# forms.py
from django import forms
from .models import Mensagem, Midia 
import re
from datetime import datetime
import pandas as pd
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User

TAMANHO_LOTE_CONTATOS_FORM = 65 # Usado para a lógica condicional

class MensagemForm(forms.ModelForm):
    contato_digitado = forms.CharField(
        label="Contatos (digite ou cole, separados por vírgula)",
        required=False, 
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': "Ex: 11999999999, +5588988888888",
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )

    contacts_file = forms.FileField(
        label="Ou importe de planilha (CSV/XLS/XLSX)",
        help_text="Os contactos da primeira coluna serão importados.",
        required=False, 
        widget=forms.ClearableFileInput(attrs={
            'class': 'w-full mt-1 text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'
        })
    )
    
    dias_disparo = forms.CharField(
        label="Dia(s) de Disparo (para < 65 contatos ou 1º lote)",
        help_text="Selecione. Obrigatório se <= 65 contatos e o submenu de lotes não estiver ativo.",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'autocomplete': 'off',
            'id': 'id_dias_disparo_principal' 
        }),
        required=False 
    )
    
    horario_disparo = forms.TimeField(
        label="Horário de Disparo (para < 65 contatos ou 1º lote)",
        help_text="Obrigatório se <= 65 contatos e o submenu de lotes não estiver ativo.",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'id': 'id_horario_disparo_principal'}),
        required=False 
    )

    contato = forms.JSONField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Mensagem
        fields = [
            'horario_disparo', 
            'intervalo_disparo', 
            'mensagem_notificacao',
            'tipo_envio',
            'modo_envio',
            'contato', # Campo do modelo (HiddenInput)
            'dias_disparo' # Campo do formulário (CharField) que mapeia para o modelo
        ]
        exclude = ['usuario', 'ordem_envio', 'id_campanha']
        widgets = {
            # Widgets para campos que não foram explicitamente definidos acima
            'intervalo_disparo': forms.NumberInput(attrs={'min': 1}),
            'mensagem_notificacao': forms.Textarea(attrs={'rows': 3}),
        }

    # MÉTODO __init__ ÚNICO E CORRIGIDO
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        tailwind_text_input_classes = 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        tailwind_select_classes = tailwind_text_input_classes
        
        # Lista de campos que já têm widgets com classes definidas na sua declaração direta,
        # ou são campos especiais que não devem receber classes genéricas.
        campos_com_widget_ja_estilizado = ['contato_digitado', 'contacts_file', 'dias_disparo', 'horario_disparo', 'contato']
        
        for field_name, field in self.fields.items():
            if field_name not in campos_com_widget_ja_estilizado:
                # Aplicar classes apenas se o widget ainda não tiver uma.
                if not field.widget.attrs.get('class'):
                    if isinstance(field.widget, (forms.TextInput, forms.TimeInput, forms.NumberInput)):
                        field.widget.attrs.update({'class': tailwind_text_input_classes})
                    elif isinstance(field.widget, forms.Textarea):
                        field.widget.attrs.update({'class': tailwind_text_input_classes, 'rows': field.widget.attrs.get('rows', 3)})
                    elif isinstance(field.widget, forms.Select):
                        field.widget.attrs.update({'class': tailwind_select_classes})

        # Preencher campos na edição
        if self.instance and self.instance.pk:
            # Popula 'contato_digitado' com os contatos da instância
            if isinstance(self.instance.contato, list): 
                self.fields['contato_digitado'].initial = ", ".join(self.instance.contato)
            
            # Popula 'dias_disparo' (que é um CharField no form)
            # A instância armazena dias_disparo como uma lista de strings de data ['YYYY-MM-DD', ...]
            if isinstance(self.instance.dias_disparo, list) and self.instance.dias_disparo:
                self.fields['dias_disparo'].initial = ", ".join(self.instance.dias_disparo) # Se for um lote, terá só uma data
            
            # Popula 'horario_disparo' (que é um TimeField no form)
            if self.instance.horario_disparo: # Verifica se não é None
                 self.fields['horario_disparo'].initial = self.instance.horario_disparo.strftime('%H:%M')

    def _formatar_numero_telefone(self, numero_str):
        if not numero_str: return None
        numero_limpo = re.sub(r'[^\d+]', '', str(numero_str).strip())
        if numero_limpo.startswith('+55') and (13 <= len(numero_limpo) <= 14): return numero_limpo
        if numero_limpo.startswith('55') and (12 <= len(numero_limpo) <= 13): return f"+{numero_limpo}"
        apenas_digitos_internos = re.sub(r'\D', '', numero_limpo)
        if 10 <= len(apenas_digitos_internos) <= 11: return f"+55{apenas_digitos_internos}"
        return None

    def clean_dias_disparo(self): 
        datas_raw = self.cleaned_data.get('dias_disparo', '').strip()
        if not datas_raw:
            # Se o campo é opcional (devido a loteamento) e está vazio, retorna lista vazia.
            # A obrigatoriedade condicional é tratada no clean() geral.
            if not self.fields['dias_disparo'].required:
                 return []
            raise forms.ValidationError("Selecione pelo menos uma data para o disparo.") # Se for obrigatório e vazio
            
        datas_str_list = [d.strip() for d in datas_raw.split(',') if d.strip()]
        datas_formatadas = []
        for data_str in datas_str_list:
            try:
                datetime.strptime(data_str, '%Y-%m-%d')
                datas_formatadas.append(data_str)
            except ValueError:
                raise forms.ValidationError(f"A data '{data_str}' no campo principal não é válida. Use o formato AAAA-MM-DD.")
        
        if datas_raw and not datas_formatadas: 
            raise forms.ValidationError("Nenhuma data válida foi fornecida para o campo principal de 'Dias de Disparo'.")
        return datas_formatadas

    def clean(self):
        cleaned_data = super().clean()
        
        contatos_digitados_str = cleaned_data.get('contato_digitado', "")
        arquivo_contatos = cleaned_data.get('contacts_file')
        
        numeros_crus_combinados = []
        numeros_invalidos_reportados = []
        erro_no_processamento_do_ficheiro = False

        if contatos_digitados_str:
            numeros_crus_combinados.extend([c.strip() for c in contatos_digitados_str.split(',') if c.strip()])

        if arquivo_contatos:
            contatos_do_arquivo_extraidos = []
            try:
                df = None; file_name = arquivo_contatos.name.lower()
                if file_name.endswith('.xlsx'): df = pd.read_excel(arquivo_contatos, header=None, dtype=str, engine='openpyxl')
                elif file_name.endswith('.xls'): df = pd.read_excel(arquivo_contatos, header=None, dtype=str, engine='xlrd')
                elif file_name.endswith('.csv'):
                    try: df = pd.read_csv(arquivo_contatos, header=None, dtype=str, encoding='utf-8-sig')
                    except UnicodeDecodeError: df = pd.read_csv(arquivo_contatos, header=None, dtype=str, encoding='latin1')
                else: self.add_error('contacts_file', "Formato de arquivo não suportado."); erro_no_processamento_do_ficheiro = True
                
                if df is not None and not df.empty:
                    numeros_potenciais_arquivo = df.iloc[:, 0].astype(str).str.strip().dropna().tolist()
                    for num_str in numeros_potenciais_arquivo:
                        if num_str and num_str.lower() not in ['nan', 'none', '']: contatos_do_arquivo_extraidos.append(num_str)
                    numeros_crus_combinados.extend(contatos_do_arquivo_extraidos)
                elif df is not None and df.empty: self.add_error('contacts_file', "Arquivo vazio ou sem dados."); erro_no_processamento_do_ficheiro = True
            
            except ImportError as ie:
                engine = 'xlrd (para .xls)' if 'xlrd' in str(ie) else 'openpyxl (para .xlsx)' if 'openpyxl' in str(ie) else None
                self.add_error('contacts_file', f"Motor {engine} não encontrado. Instale-o." if engine else f"Erro de importação: {ie}")
                erro_no_processamento_do_ficheiro = True
            except Exception as e: self.add_error('contacts_file', f"Erro no arquivo: {e}"); erro_no_processamento_do_ficheiro = True
        
        contatos_finais_formatados = []
        numeros_ja_vistos = set()
        for num_cru in numeros_crus_combinados:
            numero_formatado = self._formatar_numero_telefone(num_cru)
            if numero_formatado:
                if numero_formatado not in numeros_ja_vistos:
                    contatos_finais_formatados.append(numero_formatado)
                    numeros_ja_vistos.add(numero_formatado)
            elif num_cru: numeros_invalidos_reportados.append(num_cru)
        
        if numeros_invalidos_reportados:
            exemplos = ", ".join(list(set(numeros_invalidos_reportados))[:3])
            self.add_error(None, f"Números inválidos ignorados (ex: {exemplos}).")

        cleaned_data['todos_contatos_validados'] = contatos_finais_formatados 

        if not contatos_finais_formatados:
            if not (arquivo_contatos and erro_no_processamento_do_ficheiro and not contatos_digitados_str):
                if not contatos_digitados_str and not arquivo_contatos:
                    self.add_error(None, "É obrigatório fornecer contatos (digitados ou via arquivo).")
                else: 
                    self.add_error(None, "Nenhum contato válido processado.")
        
        num_lotes_previstos = 0
        if contatos_finais_formatados:
            num_lotes_previstos = (len(contatos_finais_formatados) + TAMANHO_LOTE_CONTATOS_FORM - 1) // TAMANHO_LOTE_CONTATOS_FORM

        # Validação condicional dos campos principais de data/hora
        # Estes campos são 'required=False' na definição. Aqui tornamo-los 'required' se num_lotes_previstos <= 1.
        if num_lotes_previstos <= 1:
            if not cleaned_data.get('dias_disparo'): 
                self.add_error('dias_disparo', "Dia de disparo é obrigatório para envio único ou primeiro lote.")
            if not cleaned_data.get('horario_disparo'):
                self.add_error('horario_disparo', "Horário de disparo é obrigatório para envio único ou primeiro lote.")
        # Se houver múltiplos lotes (num_lotes_previstos > 1), o JavaScript deve ter escondido estes campos.
        # Como são required=False, não darão erro de validação de campo se estiverem vazios.
        # A view irá obter as datas/horas dos campos de lote do POST.
        
        modo_envio = cleaned_data.get("modo_envio")
        mensagem_notificacao = cleaned_data.get("mensagem_notificacao")
        if modo_envio == "texto" and not mensagem_notificacao:
            self.add_error('mensagem_notificacao', "Se o envio for apenas texto, a mensagem não pode estar vazia.")
        
        # Preenche cleaned_data['contato'] com uma lista vazia.
        # A view 'cadastrar_aula' usará 'todos_contatos_validados' para criar os lotes
        # e preencherá o campo 'contato' de cada instância de Mensagem.
        # Para a view 'editar_aula' (que salva uma única Mensagem), precisamos garantir que
        # cleaned_data['contato'] tem os contatos corretos para a instância sendo editada.
        # Se for uma edição e não houver múltiplos lotes, podemos popular cleaned_data['contato'] aqui.
        if self.instance and self.instance.pk and num_lotes_previstos <= 1:
             cleaned_data['contato'] = contatos_finais_formatados
        else:
            cleaned_data['contato'] = [] # Para o caso de criação com múltiplos lotes, a view preenche

        return cleaned_data


class MidiaForm(forms.ModelForm):
    tipo = forms.ChoiceField(
        choices=Midia.TIPOS_MIDIA, # Irá incluir PDF após alteração no models.py
        widget=forms.Select() 
    )
    arquivo = forms.FileField(
        required=True, 
        label="Arquivo da Mídia",
        widget=forms.ClearableFileInput() 
    )
    class Meta:
        model = Midia
        fields = ['nome', 'tipo', 'descricao', 'arquivo']

   


    
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('username', 'email')













