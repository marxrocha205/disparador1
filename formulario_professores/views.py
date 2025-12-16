# formularios/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.core.cache import cache
from django.utils import timezone
from .forms import MensagemForm, MidiaForm, EvolutionAPISettingsForm
from .models import Mensagem, EvolutionAPISettings, Instancia, Enviadas, UserMessageLimit, Midia
from .repositories.evolutionRepository import EvolutionRepository
import uuid
from datetime import datetime as dt
from django.http import JsonResponse, HttpResponse
from celery.result import AsyncResult
from .tasks import exportar_contatos_task # <-- NOVO IMPORT
import json


# --- Constantes ---
TAMANHO_LOTE_CONTATOS = 65
CACHE_STATUS_TTL = 30  # 30 segundos de cache para o status da conexão

# --- Funções Auxiliares (Estão corretas!) ---
def get_user_api_config(user):
    """Obtém a configuração da API e a instância para o usuário."""
    try:
        api_settings = EvolutionAPISettings.objects.get(usuario=user, is_active=True)
        # Garante que uma instância exista para o usuário
        instancia, _ = Instancia.objects.get_or_create(usuario=user, defaults={'nome_instancia': f'instancia_{user.username}'})
        return api_settings, instancia
    except EvolutionAPISettings.DoesNotExist:
        return None, None

def check_connection_status(request, api_settings, instancia):
    """Verifica e atualiza o status da conexão, buscando o QR Code se necessário."""
    cache_key = f'evolution_status_{instancia.id}'
    
    # Não vamos usar o cache aqui por enquanto para facilitar o debug
    # cached_status = cache.get(cache_key)
    # if cached_status:
    #     return cached_status

    # 1. Primeiro, apenas checa o estado da conexão
    status_data = EvolutionRepository.get_status(
        api_settings.api_host, api_settings.api_key, instancia.nome_instancia
    )
    
    is_connected = status_data.get('instance', {}).get('state') == 'open'
    qr_code_base64 = None

    # 2. Se não estiver conectado, pede ativamente o QR Code
    if not is_connected:
        qr_data = EvolutionRepository.get_qrcode(
            api_settings.api_host, api_settings.api_key, instancia.nome_instancia
        )
        # A API retorna o QR Code dentro da chave 'base64'
        qr_code_base64 = qr_data.get('base64')

    status_info = {
        'connected': is_connected,
        'qrcode': qr_code_base64,
        'raw_data': status_data,
        'timestamp': timezone.now()
    }
    
    # Armazena em cache apenas se estiver conectado (para não guardar o QR Code)
    if is_connected:
        cache.set(cache_key, status_info, CACHE_STATUS_TTL)
    
    # Atualiza o banco de dados
    if instancia.conectado != is_connected:
        instancia.conectado = is_connected
        instancia.save(update_fields=['conectado'])
        
    return status_info

# --- Views de Autenticação ---
class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    def form_invalid(self, form):
        messages.error(self.request, 'Credenciais inválidas. Por favor, tente novamente.')
        return super().form_invalid(form)

# --- Views de Configuração da Evolution API (Estão corretas!) ---
@login_required
def evolution_config_view(request):
    api_settings = EvolutionAPISettings.objects.filter(usuario=request.user).first()
    
    if request.method == 'POST':
        form = EvolutionAPISettingsForm(request.POST, instance=api_settings)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.usuario = request.user
            instance.save()
            messages.success(request, "Configurações da Evolution API salvas com sucesso.")
            return redirect('evolution_status')
    else:
        form = EvolutionAPISettingsForm(instance=api_settings)

    return render(request, 'evolution/config.html', {'form': form})

@login_required
def evolution_status_view(request):
    api_settings, instancia = get_user_api_config(request.user)

    if not api_settings:
        messages.warning(request, "Por favor, configure suas credenciais da Evolution API primeiro.")
        return redirect('evolution_config')
    
    status_info = check_connection_status(request, api_settings, instancia)

    context = {
        'instancia': instancia,
        'status_info': status_info,
    }
    return render(request, 'evolution/status.html', context)

@login_required
def evolution_create_instance(request):
    if request.method == 'POST':
        api_settings, instancia = get_user_api_config(request.user)
        if not api_settings:
            messages.error(request, "Credenciais da API não configuradas.")
            return redirect('evolution_config')

        # O nome da instância já existe no objeto 'instancia'
        instance_name = instancia.nome_instancia

        result = EvolutionRepository.criar_instancia(
            api_settings.api_host, 
            api_settings.api_key, 
            instance_name
        )

        if result.get('instance'):
            # --- CORREÇÃO AQUI ---
            # Limpa o cache de status para forçar a busca do novo status com o QR Code
            cache_key = f'evolution_status_{instancia.id}'
            cache.delete(cache_key)
            # --- FIM DA CORREÇÃO ---

            messages.success(request, f"Instância '{instance_name}' criada/iniciada. Escaneie o QR Code se necessário.")
        else:
            error_msg = result.get('error', 'Erro desconhecido.')
            messages.error(request, f"Erro ao criar instância: {error_msg}")

    return redirect('evolution_status')

@login_required
def evolution_disconnect_instance(request):
    if request.method == 'POST':
        api_settings, instancia = get_user_api_config(request.user)
        if api_settings and instancia:
            result = EvolutionRepository.desconectar(api_settings.api_host, api_settings.api_key, instancia.nome_instancia)
            if result.get('status') != 'error':
                instancia.conectado = False
                instancia.save()
                cache.delete(f'evolution_status_{instancia.id}')
                messages.success(request, "Instância desconectada com sucesso.")
            else:
                messages.error(request, f"Erro ao desconectar: {result.get('message')}")
    return redirect('evolution_status')


# --- Views Principais da Aplicação (Adaptadas) ---

@login_required
def listar_aulas(request):
    api_settings, instancia = get_user_api_config(request.user)
    if not api_settings:
        messages.warning(request, "Você precisa configurar a sua instância do WhatsApp antes de agendar mensagens.")
        return redirect('evolution_config')

    status_conexao = instancia.get_cached_status()
    
    mensagens_qs = Mensagem.objects.filter(usuario=request.user).order_by('-id_campanha', '-id')
    
    hoje = timezone.now().date()
    mensagens_enviadas_hoje = Enviadas.objects.filter(user=request.user, data_envio__date=hoje).count()
    limite = UserMessageLimit.objects.filter(user=request.user).first()
    limite_diario = limite.limite_diario if limite else 65

    return render(request, 'listar.html', {
        'mensagens': mensagens_qs,
        'status_conexao': status_conexao,
        'mensagens_enviadas_hoje': mensagens_enviadas_hoje,
        'limite_diario': limite_diario
    })

@login_required
def cadastrar_aula(request):
    api_settings, instancia = get_user_api_config(request.user)
    if not (api_settings and instancia and instancia.get_cached_status()):
         messages.warning(request, "Conecte sua instância do WhatsApp para poder agendar mensagens.")
         return redirect('evolution_status')

    midias_disponiveis = Midia.objects.filter(usuario=request.user)

    if request.method == 'POST':
        form = MensagemForm(request.POST, request.FILES)
        if form.is_valid():
            nova_mensagem = form.save(commit=False)
            nova_mensagem.usuario = request.user
            nova_mensagem.id_campanha = uuid.uuid4()
            
            id_midia = request.POST.get('midia')
            if id_midia:
                nova_mensagem.midia = get_object_or_404(Midia, id=id_midia, usuario=request.user)
            
            nova_mensagem.save()
            messages.success(request, "Agendamento criado com sucesso!")
            return redirect('listar_aulas')
    else:
        form = MensagemForm()

    return render(request, 'formulario.html', {
        'form': form, 'titulo': 'Cadastrar Mensagem', 'mensagem_botao': 'Agendar',
        'midias': midias_disponiveis,
        'TAMANHO_LOTE_CONTATOS_FORM': TAMANHO_LOTE_CONTATOS
    })
    
@login_required
def editar_aula(request, mensagem_id):
    mensagem_obj = get_object_or_404(Mensagem, id=mensagem_id, usuario=request.user)
    midias_disponiveis = Midia.objects.filter(usuario=request.user)
    
    # CORREÇÃO: Usando a nova forma de verificar o status da conexão
    api_settings, instancia = get_user_api_config(request.user)
    status_conexao_instancia = instancia.get_cached_status() if instancia else False
    
    midia_selecionada_atual = mensagem_obj.midia
        
    if request.method == 'POST':
        form = MensagemForm(request.POST, request.FILES, instance=mensagem_obj)
        if form.is_valid():
            mensagem_editada = form.save(commit=False)
            
            # CORREÇÃO: Lógica para atualizar a mídia associada
            id_midia_post = request.POST.get('midia')
            if id_midia_post:
                mensagem_editada.midia = get_object_or_404(Midia, id=id_midia_post, usuario=request.user)
            else:
                mensagem_editada.midia = None # Remove a associação se nenhuma mídia for selecionada
            
            mensagem_editada.save()
            messages.success(request, "Mensagem atualizada com sucesso!")
            return redirect('listar_aulas')
        else:
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = MensagemForm(instance=mensagem_obj)
    
    return render(request, 'formulario.html', {
        'form': form, 
        'titulo': 'Editar Mensagem', 
        'mensagem_botao': 'Salvar', 
        'midia_select': midia_selecionada_atual,
        'midias': midias_disponiveis,
        'status': status_conexao_instancia, 
        'TAMANHO_LOTE_CONTATOS_FORM': TAMANHO_LOTE_CONTATOS
    })

@login_required
def excluir_aula(request, aula_id):
    aula_obj = get_object_or_404(Mensagem, id=aula_id, usuario=request.user)
    if request.method == 'POST': 
        aula_obj.delete()
        messages.success(request, "Agendamento de mensagem excluído com sucesso.")
        return redirect('listar_aulas')
    return render(request, 'excluir.html', {'aula': aula_obj})



@login_required
def listar_midias(request):
    _, instancia = get_user_api_config(request.user)
    status_conexao = instancia.get_cached_status() if instancia else False
    midias = Midia.objects.filter(usuario=request.user).order_by('-id')
    return render(request, 'listar_midias.html', {'midias': midias, 'status_conexao': status_conexao})

@login_required
def upload_midia(request):
    if request.method == "POST":
        form = MidiaForm(request.POST, request.FILES)
        if form.is_valid():
            midia_obj = form.save(commit=False)
            midia_obj.usuario = request.user
            midia_obj.save()
            messages.success(request, "Mídia enviada com sucesso!")
            return redirect('listar_midias')
    else:
        form = MidiaForm()
    return render(request, 'upload.html', {'form': form})

@login_required
def editar_midia(request, midia_id):
    midia_obj = get_object_or_404(Midia, id=midia_id, usuario=request.user)
    
    api_settings, instancia = get_user_api_config(request.user)
    status_conexao_instancia = instancia.get_cached_status() if instancia else False

    if request.method == "POST":
        form = MidiaForm(request.POST, request.FILES, instance=midia_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Mídia '{midia_obj.nome}' atualizada com sucesso!")
            return redirect('listar_midias')
        else:
            messages.error(request, "Erro ao atualizar mídia. Verifique o formulário.")
    else:
        form = MidiaForm(instance=midia_obj)

    return render(request, 'editar_midia.html', {'form': form, 'midia': midia_obj, 'status': status_conexao_instancia})

@login_required
def excluir_midia(request, midia_id):
    midia_obj = get_object_or_404(Midia, id=midia_id, usuario=request.user)
    midia_obj.delete()
    messages.success(request, f"Mídia '{midia_obj.nome}' excluída com sucesso.")
    return redirect('listar_midias')

def erro_view(request):
    return render(request, 'erro.html', {"mensagem_erro": "Ocorreu um erro ou o recurso não foi encontrado."})

def gerar_presigned_url(request, midia_id):
    midia_obj = get_object_or_404(Midia, id=midia_id)
    if midia_obj.usuario != request.user and not request.user.is_staff:
        messages.error(request, "Você não tem permissão para acessar esta mídia.")
        return redirect('listar_midias')
    
    url = midia_obj.get_presigned_url()
    
    if url:
        return redirect(url)
    else:
        messages.error(request, "Não foi possível gerar o link para a mídia.")
        return redirect('erro_view')

@login_required
def exportar_contatos_view(request):
    """Renderiza a página para iniciar a extração de contatos."""
    api_settings, instancia = get_user_api_config(request.user)
    status_conexao = instancia.get_cached_status() if instancia else False
    return render(request, 'evolution/exportar_contatos.html', {'status_conexao': status_conexao})

@login_required
def iniciar_exportacao_view(request):
    """
    Inicia a tarefa Celery, agora recebendo uma lista de IDs de grupos
    do corpo da requisição.
    """
    if request.method == 'POST':
        try:
            # Pega a lista de IDs do corpo da requisição JSON
            data = json.loads(request.body)
            group_ids = data.get('group_ids')

            if not group_ids or not isinstance(group_ids, list):
                return JsonResponse({'error': 'Nenhum grupo foi selecionado.'}, status=400)
            
            # Passa a lista de IDs para a tarefa Celery
            task = exportar_contatos_task.delay(request.user.id, group_ids)
            return JsonResponse({'task_id': task.id})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Requisição JSON inválida.'}, status=400)
            
    return JsonResponse({'error': 'Método não permitido'}, status=405)

@login_required
def status_exportacao_view(request, task_id):
    """
    VERSÃO CORRIGIDA E ROBUSTA
    Retorna o status de uma tarefa Celery em formato JSON,
    de uma maneira que o nosso JavaScript entende perfeitamente.
    """
    result = AsyncResult(task_id)
    
    response_data = {
        'task_id': task_id,
        'state': result.state,
        'meta': {},      # Detalhes para progresso ou falha
        'result': None   # URL final apenas em caso de sucesso
    }

    # Lida com cada estado da tarefa e monta a resposta correta
    if result.state == 'PENDING':
        response_data['meta'] = {'status': 'Tarefa na fila, aguardando para iniciar...'}

    elif result.state == 'PROGRESS':
        # result.info contém o dicionário de progresso da tarefa
        # Colocamos ele inteiro dentro da chave 'meta'
        response_data['meta'] = result.info 

    elif result.state == 'SUCCESS':
        # result.result contém o valor de retorno da tarefa (a URL)
        # Colocamos na chave 'result'
        response_data['result'] = result.result
        response_data['meta'] = {'status': 'Concluído!'}
        
    elif result.state == 'FAILURE':
        # Em caso de falha, guardamos a mensagem de erro em 'meta'
        response_data['meta'] = {
            'status': str(result.info),  # Pega a exceção como string
        }

    return JsonResponse(response_data)

@login_required
def download_arquivo_exportado(request, task_id):
    """
    Busca o arquivo gerado pela tarefa Celery no cache e o serve para download.
    """
    cache_key = f"export_task_{task_id}"
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        messages.error(request, "O arquivo para download não foi encontrado ou expirou. Por favor, tente gerar novamente.")
        return redirect('exportar_contatos')

    # Pega o conteúdo e o nome do arquivo do cache
    file_content = cached_data['file_content']
    filename = cached_data['filename']
    
    # Cria uma resposta HTTP com o arquivo
    response = HttpResponse(
        file_content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # (Opcional) Deleta a chave do cache após o primeiro download
    cache.delete(cache_key)
    
    return response

@login_required
def listar_grupos_view(request):
    """
    Uma view de API que retorna uma lista simplificada de todos os grupos
    para o usuário logado (apenas ID e nome).
    """
    api_settings, instancia = get_user_api_config(request.user)
    if not api_settings:
        return JsonResponse({'error': 'Configuração da API não encontrada'}, status=404)

    # Buscamos os grupos SEM os participantes para uma resposta rápida
    grupos_data = EvolutionRepository.get_todos_grupos(
        api_settings.api_host, 
        api_settings.api_key, 
        instancia.nome_instancia,
        get_participants=False # Importante para a velocidade
    )
    
    if "error" in grupos_data or not isinstance(grupos_data, list):
        return JsonResponse({'error': 'Falha ao buscar grupos na API do WhatsApp', 'details': grupos_data}, status=500)

    # Filtramos para enviar apenas os dados que o frontend precisa (ID e Nome)
    grupos_simplificados = [
        {'id': g.get('id'), 'name': g.get('subject')}
        for g in grupos_data
    ]

    return JsonResponse({'groups': grupos_simplificados})