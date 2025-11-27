# /app/formulario_professores/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.models import User
import os
import boto3
import tempfile
import base64
from botocore.exceptions import ClientError
import ffmpeg
from django.conf import settings as django_settings
from .models import Mensagem, EvolutionAPISettings, UserMessageLimit, Enviadas, Midia, Instancia
from .repositories.evolutionRepository import EvolutionRepository
import pandas as pd 
from django.core.files.base import ContentFile 
import time
import random

logger = logging.getLogger(__name__)
VERIFICAR_DISPAROS_LOCK_EXPIRE = 50

def get_api_credentials(usuario_id: int):
    """Busca as credenciais da API e a instância para um dado usuário a partir da base de dados."""
    try:
        settings = EvolutionAPISettings.objects.select_related('usuario__instancia').get(usuario_id=usuario_id, is_active=True)
        instancia = settings.usuario.instancia
        return settings, instancia
    except (EvolutionAPISettings.DoesNotExist, User.instancia.RelatedObjectDoesNotExist):
        logger.error(f"Credenciais ou instância da Evolution API não encontradas para o usuário ID {usuario_id}.")
        return None, None


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_notificacao_whatsapp_texto(self, contato, mensagem_texto, usuario_id, envio_log_id):
    """Tarefa Celery para enviar uma mensagem de texto."""
    logger.info(f"[EnvioTexto ID: {envio_log_id}] Iniciando para {contato}, Usuário ID: {usuario_id}")
    api_settings, instancia = get_api_credentials(usuario_id)
    if not api_settings:
        return

    resultado_api = EvolutionRepository.enviar_mensagem_texto(
        api_settings.api_host,
        api_settings.api_key,
        instancia.nome_instancia,
        contato,
        mensagem_texto
    )

    if "error" in resultado_api or resultado_api.get("status") == "error":
        error_details = resultado_api.get('message', 'Erro desconhecido')
        logger.error(f"[EnvioTexto ID: {envio_log_id}] Falha ao enviar para {contato}. Erro: {error_details}")
    else:
        logger.info(f"[EnvioTexto ID: {envio_log_id}] Sucesso para {contato}.")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_notificacao_whatsapp_botao(self, contato, mensagem_texto, botao_texto, botao_url, usuario_id, envio_log_id):
    """Tarefa Celery para enviar uma mensagem de texto com botão URL."""
    logger.info(f"[EnvioBotao ID: {envio_log_id}] Iniciando para {contato}, Usuário ID: {usuario_id}")
    api_settings, instancia = get_api_credentials(usuario_id)
    if not api_settings:
        return

    resultado_api = EvolutionRepository.enviar_mensagem_com_botao(
        api_settings.api_host,
        api_settings.api_key,
        instancia.nome_instancia,
        contato,
        mensagem_texto,
        botao_texto,
        botao_url
    )

    if "error" in resultado_api or resultado_api.get("status") == "error":
        error_details = resultado_api.get('message', 'Erro desconhecido')
        logger.error(f"[EnvioBotao ID: {envio_log_id}] Falha ao enviar para {contato}. Erro: {error_details}")
    else:
        logger.info(f"[EnvioBotao ID: {envio_log_id}] Sucesso para {contato}.")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_notificacao_whatsapp_midia(self, contato, midia_id, mensagem_id, usuario_id, envio_log_id):
    """Tarefa Celery para enviar uma mensagem com mídia, com conversão de áudio."""
    logger.info(f"[EnvioMidia ID: {envio_log_id}] Iniciando para {contato}, Usuário ID: {usuario_id}")
    api_settings, instancia = get_api_credentials(usuario_id)
    if not api_settings:
        return

    try:
        midia = Midia.objects.get(id=midia_id)
        mensagem = Mensagem.objects.get(id=mensagem_id)
    except (Midia.DoesNotExist, Mensagem.DoesNotExist):
        logger.error(f"[EnvioMidia ID: {envio_log_id}] Mídia ou Mensagem não encontrada.")
        return

    resultado_api = {}
    try:
        if midia.tipo in ['image', 'video', 'document', 'audio']:
            s3_client = boto3.client('s3')
            
            # Usamos um diretório temporário para lidar com os arquivos de entrada e saída
            with tempfile.TemporaryDirectory() as temp_dir:
                original_file_path = os.path.join(temp_dir, midia.nome)
                
                # Baixa o arquivo original do S3
                s3_client.download_file(
                    os.getenv('AWS_STORAGE_BUCKET_NAME'), midia.arquivo.name, original_file_path
                )

                file_to_encode_path = original_file_path
                mimetype = midia.mimetype or 'application/octet-stream'

                # <<< LÓGICA DE CONVERSÃO DE ÁUDIO >>>
                if midia.tipo == 'audio':
                    logger.info(f"[EnvioMidia ID: {envio_log_id}] Arquivo de áudio detectado. Iniciando conversão para OGG/Opus.")
                    converted_file_path = os.path.join(temp_dir, "audio.ogg")
                    try:
                        # Roda o comando do ffmpeg para converter o áudio
                        ffmpeg.input(original_file_path).output(
                            converted_file_path, 
                            acodec='libopus',       # Codec do WhatsApp
                            format='ogg',           # Formato do WhatsApp
                            audio_bitrate='16k'     # Taxa de bits comum para áudio de voz
                        ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
                        
                        file_to_encode_path = converted_file_path # O arquivo a ser enviado é o convertido
                        mimetype = 'audio/ogg' # O mimetype agora é OGG
                        logger.info(f"[EnvioMidia ID: {envio_log_id}] Conversão de áudio concluída com sucesso.")
                    except ffmpeg.Error as e:
                        logger.error(f"[EnvioMidia ID: {envio_log_id}] Erro do FFmpeg ao converter áudio: {e.stderr.decode()}")
                        # Continua tentando enviar o arquivo original se a conversão falhar
                        pass
                
                # <<< CODIFICAÇÃO PARA BASE64 >>>
                with open(file_to_encode_path, 'rb') as f:
                    file_bytes = f.read()
                base64_data = base64.b64encode(file_bytes).decode('utf-8')
                
                # <<< CHAMADA PARA A API >>>
                if midia.tipo == 'audio':
                    resultado_api = EvolutionRepository.enviar_audio(
                        host=api_settings.api_host, api_key=api_settings.api_key,
                        instance_name=instancia.nome_instancia, number=contato,
                        audio_data=base64_data # Envia o áudio (convertido ou original)
                    )
                else:
                    resultado_api = EvolutionRepository.enviar_midia(
                        host=api_settings.api_host, api_key=api_settings.api_key,
                        instance_name=instancia.nome_instancia, number=contato,
                        mediatype=midia.tipo,
                        mimetype=mimetype,
                        media_data=base64_data,
                        caption=mensagem.mensagem_notificacao,
                        file_name=midia.nome
                    )
        else:
            logger.error(f"[EnvioMidia ID: {envio_log_id}] Tipo de mídia '{midia.tipo}' não suportado.")
            return

        if "error" in resultado_api or resultado_api.get("status") == "error":
            error_details = resultado_api.get('message', 'Erro desconhecido')
            logger.error(f"[EnvioMidia ID: {envio_log_id}] Falha ao enviar {midia.tipo}. Erro: {error_details}")
        else:
            logger.info(f"[EnviaMidia ID: {envio_log_id}] Sucesso ao enviar {midia.tipo} para {contato}.")

    except ClientError as s3_err:
        logger.error(f"[EnvioMidia ID: {envio_log_id}] Erro no S3: {s3_err}")
    except Exception as e:
        logger.error(f"[EnvioMidia ID: {envio_log_id}] Erro inesperado: {e}", exc_info=True)






@shared_task(bind=True)
def verificar_disparos(self):
    """Verifica e enfileira os disparos de mensagens agendados para o minuto atual."""
    agora_para_lock = timezone.localtime(timezone.now())
    lock_key = f"verificar_disparos_lock_{agora_para_lock.strftime('%Y%m%d%H%M')}"
    lock_adquirido = cache.add(lock_key, self.request.id, VERIFICAR_DISPAROS_LOCK_EXPIRE)

    if not lock_adquirido:
        logger.warning(f"VERIFICAR_DISPAROS: Lock '{lock_key}' já existe. Task {self.request.id} saindo.")
        return

    logger.info(f"VERIFICAR_DISPAROS: Task {self.request.id} adquiriu lock '{lock_key}'.")
    try:
        agora = timezone.localtime(timezone.now())
        hora_minuto_atual = agora.time()
        data_atual_str = agora.strftime("%Y-%m-%d")

        mensagens_para_hoje = Mensagem.objects.filter(
            horario_disparo__hour=hora_minuto_atual.hour,
            horario_disparo__minute=hora_minuto_atual.minute,
            dias_disparo__contains=data_atual_str
        ).select_related('usuario', 'midia')

        logger.info(f"VERIFICAR_DISPAROS ({self.request.id}): {mensagens_para_hoje.count()} agendamentos encontrados.")

        for msg in mensagens_para_hoje:
            usuario = msg.usuario
            limite_obj = UserMessageLimit.objects.filter(user=usuario).first()
            limite_diario = limite_obj.limite_diario if limite_obj else 65

            enviadas_hoje = Enviadas.objects.filter(user=usuario, data_envio__date=agora.date()).count()
            if enviadas_hoje >= limite_diario:
                logger.warning(f"VERIFICAR_DISPAROS: Limite diário atingido para {usuario.username}. Agendamento {msg.id} ignorado.")
                continue

            delay = 0
            for contato_idx, contato in enumerate(msg.contato):
                if Enviadas.objects.filter(user=usuario, data_envio__date=agora.date()).count() >= limite_diario:
                    logger.warning(f"VERIFICAR_DISPAROS: Limite diário atingido durante o envio do lote para {usuario.username}.")
                    break

                envio_log_id = f"msg{msg.id}-camp{msg.id_campanha}-cont{contato_idx}"
                enviou_algo = False

                def agendar_envio_texto():
                    # Verifica se deve enviar com botão ou texto simples
                    if msg.incluir_botao and msg.botao_texto and msg.botao_url:
                        enviar_notificacao_whatsapp_botao.apply_async(
                            args=[contato, msg.mensagem_notificacao, msg.botao_texto, msg.botao_url, usuario.id, f"{envio_log_id}-btn"],
                            countdown=delay
                        )
                    else:
                        enviar_notificacao_whatsapp_texto.apply_async(
                            args=[contato, msg.mensagem_notificacao, usuario.id, f"{envio_log_id}-txt"],
                            countdown=delay
                        )
                    return True

                def agendar_envio_midia():
                    if msg.midia and msg.midia.arquivo:
                        enviar_notificacao_whatsapp_midia.apply_async(
                            args=[contato, msg.midia.id, msg.id, usuario.id, f"{envio_log_id}-mid"],
                            countdown=delay + (2 if msg.modo_envio == 'ambos' and msg.tipo_envio == 'texto_primeiro' else 0)
                        )
                        return True
                    logger.warning(f"VERIFICAR_DISPAROS: Mídia não encontrada para msg {msg.id}")
                    return False

                if msg.modo_envio == 'texto':
                    enviou_algo = agendar_envio_texto()
                elif msg.modo_envio == 'midia':
                    enviou_algo = agendar_envio_midia()
                elif msg.modo_envio == 'ambos':
                    if msg.tipo_envio == 'texto_primeiro':
                        enviou_algo = agendar_envio_texto()
                        enviou_algo = agendar_envio_midia() or enviou_algo
                    else:  # midia_primeiro
                        enviou_algo = agendar_envio_midia()
                        enviou_algo = agendar_envio_texto() or enviou_algo

                if enviou_algo:
                    Enviadas.objects.create(user=usuario, texto=f"Agend.: {msg.id} - Contato: {contato}")
                    delay += msg.intervalo_disparo

    finally:
        if lock_adquirido:
            cache.delete(lock_key)
            logger.info(f"VERIFICAR_DISPAROS: Task {self.request.id} libertou lock '{lock_key}'.")
            
            

@shared_task(bind=True)
def exportar_contatos_task(self, usuario_id, selected_group_ids):
    """
    VERSÃO FINAL E OTIMIZADA (15/08/2025)
    - Usa UMA ÚNICA chamada de API para buscar grupos e participantes, eliminando o 'rate-overlimit'.
    - Salva o arquivo Excel gerado diretamente no cache para download imediato.
    """
    self.update_state(state='PENDING', meta={'status': 'Iniciando...'})
    
    # 1. Busca as credenciais da API
    try:
        settings = EvolutionAPISettings.objects.select_related('usuario__instancia').get(usuario_id=usuario_id, is_active=True)
        instancia = settings.usuario.instancia
    except Exception as e:
        self.update_state(state='FAILURE', meta={'status': f'Configuração da API não encontrada: {e}'})
        return "Erro de configuração"

    host = settings.api_host
    api_key = settings.api_key
    instance_name = instancia.nome_instancia

    self.update_state(state='PROGRESS', meta={'status': 'Buscando todos os grupos e participantes... (Isso pode levar um momento)'})
    
    # 2. FAZ A CHAMADA ÚNICA E EFICIENTE À API
    grupos_com_participantes = EvolutionRepository.get_todos_grupos(host, api_key, instance_name, get_participants=True)

    if "error" in grupos_com_participantes or not isinstance(grupos_com_participantes, list):
        error_msg = f"Erro ao buscar grupos na API: {grupos_com_participantes}"
        self.update_state(state='FAILURE', meta={'status': error_msg})
        return error_msg

    # 3. PROCESSA OS DADOS (JÁ EM MEMÓRIA, SEM NOVAS CHAMADAS DE API)
    todos_os_contatos = []
    total_grupos = len(grupos_com_participantes)
    for i, grupo in enumerate(grupos_com_participantes):
        group_name = grupo.get('subject', 'Nome Desconhecido')
        self.update_state(state='PROGRESS', meta={'status': f'Processando dados do grupo {i+1}/{total_grupos}: {group_name}', 'current': i + 1, 'total': total_grupos})
        
        for participante in grupo.get('participants', []):
            numero = participante.get('id', '').split('@')[0]
            if numero:
                todos_os_contatos.append({'Numero': numero, 'Nome do Grupo': group_name})

    if not todos_os_contatos:
        self.update_state(state='SUCCESS', meta={'status': 'Nenhum contato encontrado nos grupos.'})
        return "EMPTY" # Sinaliza ao frontend que não há arquivo

    self.update_state(state='PROGRESS', meta={'status': 'Finalizando e gerando arquivo Excel...'})
    
    # 4. GERA O ARQUIVO EXCEL EM MEMÓRIA
    df = pd.DataFrame(todos_os_contatos).drop_duplicates(subset=['Numero'])
    output = ContentFile(b'')
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Contatos')
    output.seek(0)
    
    nome_arquivo = f"contatos_whatsapp_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    # 5. SALVA O ARQUIVO NO CACHE UNIFICADO
    cache_data = {
        'file_content': output.read(),
        'filename': nome_arquivo
    }
    cache.set(f"export_task_{self.request.id}", cache_data, timeout=600) # 10 minutos para baixar
    
    return True