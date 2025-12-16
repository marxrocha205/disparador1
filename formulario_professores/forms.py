# forms.py
from django import forms
from .models import Mensagem, Midia, Instancia 
import re
from datetime import datetime
import pandas as pd
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django import forms
from .models import Mensagem, Midia, Instancia, EvolutionAPISettings # Adicione EvolutionAPISettings aqui

TAMANHO_LOTE_CONTATOS_FORM = 65


# CORREÇÃO: InstanciaForm movido para fora e com a Meta class correta
class InstanciaForm(forms.ModelForm):
    id_instancia = forms.CharField(
        label="ID da Instância Z-API",
        widget=forms.TextInput(attrs={
            'placeholder': "Cole o ID da sua instância aqui",
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )
    token_instancia = forms.CharField(
        label="Token da Instância Z-API",
        widget=forms.TextInput(attrs={
            'placeholder': "Cole o Token da sua instância aqui",
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )

    class Meta:
        model = Instancia # CORRIGIDO: Aponta para o modelo Instancia
        fields = ['id_instancia', 'token_instancia']


class MensagemForm(forms.ModelForm):
    contato_digitado = forms.CharField(
        label="Contatos (digite ou cole, separados por vírgula)",
        required=False, 
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': "Ex: +5511988887777 ou 11988887777",
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        })
    )

    contacts_file = forms.FileField(
        label="Ou importe de planilha (CSV/XLS/XLSX)",
        help_text="A primeira coluna será lida. Números brasileiros válidos serão formatados para o padrão +55.",
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

    incluir_botao = forms.BooleanField(
        label="Incluir Botão com Link",
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500',
            'id': 'id_incluir_botao'
        })
    )
    
    botao_texto = forms.CharField(
        label="Texto do Botão",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: Acesse nossa página',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'id': 'id_botao_texto'
        })
    )
    
    botao_url = forms.URLField(
        label="URL do Botão",
        max_length=500,
        required=False,
        widget=forms.URLInput(attrs={
            'placeholder': 'Ex: https://seusite.com',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'id': 'id_botao_url'
        })
    )

    class Meta:
        model = Mensagem
        fields = [
            'horario_disparo', 
            'intervalo_disparo', 
            'mensagem_notificacao',
            'tipo_envio',
            'modo_envio',
            'contato',
            'dias_disparo',
            'incluir_botao',
            'botao_texto',
            'botao_url'
        ]
        exclude = ['usuario', 'ordem_envio', 'id_campanha']
        widgets = {
            'intervalo_disparo': forms.NumberInput(attrs={'min': 1}),
            'mensagem_notificacao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        tailwind_text_input_classes = 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        tailwind_select_classes = tailwind_text_input_classes
        
        campos_com_widget_ja_estilizado = ['contato_digitado', 'contacts_file', 'dias_disparo', 'horario_disparo', 'contato', 'incluir_botao', 'botao_texto', 'botao_url']
        
        for field_name, field in self.fields.items():
            if field_name not in campos_com_widget_ja_estilizado and not field.widget.attrs.get('class'):
                if isinstance(field.widget, (forms.TextInput, forms.TimeInput, forms.NumberInput)):
                    field.widget.attrs.update({'class': tailwind_text_input_classes})
                elif isinstance(field.widget, forms.Textarea):
                    field.widget.attrs.update({'class': tailwind_text_input_classes, 'rows': field.widget.attrs.get('rows', 3)})
                elif isinstance(field.widget, forms.Select):
                    field.widget.attrs.update({'class': tailwind_select_classes})

        if self.instance and self.instance.pk:
            if isinstance(self.instance.contato, list): 
                self.fields['contato_digitado'].initial = ", ".join(self.instance.contato)
            if isinstance(self.instance.dias_disparo, list):
                self.fields['dias_disparo'].initial = ", ".join(self.instance.dias_disparo)
            if self.instance.horario_disparo:
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
            if not self.fields['dias_disparo'].required:
                 return []
            raise forms.ValidationError("Selecione pelo menos uma data para o disparo.")
            
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
            try:
                df = None; file_name = arquivo_contatos.name.lower()
                if file_name.endswith(('.xls', '.xlsx')):
                    engine = 'xlrd' if file_name.endswith('.xls') else 'openpyxl'
                    df = pd.read_excel(arquivo_contatos, header=None, dtype=str, engine=engine)
                elif file_name.endswith('.csv'):
                    df = pd.read_csv(arquivo_contatos, header=None, dtype=str, encoding='utf-8-sig', on_bad_lines='skip')
                else: self.add_error('contacts_file', "Formato de arquivo não suportado."); erro_no_processamento_do_ficheiro = True
                
                if df is not None and not df.empty:
                    numeros_potenciais_arquivo = df.iloc[:, 0].astype(str).str.strip().dropna().tolist()
                    for num_str in numeros_potenciais_arquivo:
                        if num_str and num_str.lower() not in ['nan', 'none', '']:
                            numeros_crus_combinados.append(num_str)
                elif df is not None and df.empty: self.add_error('contacts_file', "Arquivo vazio ou sem dados."); erro_no_processamento_do_ficheiro = True
            except Exception as e: self.add_error('contacts_file', f"Erro ao processar o arquivo: {e}"); erro_no_processamento_do_ficheiro = True
        
        contatos_finais_formatados = []
        numeros_ja_vistos = set()
        for num_cru in numeros_crus_combinados:
            numero_formatado = self._formatar_numero_telefone(num_cru)
            if numero_formatado:
                if numero_formatado not in numeros_ja_vistos:
                    contatos_finais_formatados.append(numero_formatado)
                    numeros_ja_vistos.add(numero_formatado)
            elif num_cru: 
                numeros_invalidos_reportados.append(num_cru)
        
        if numeros_invalidos_reportados:
            exemplos = ", ".join(list(set(numeros_invalidos_reportados))[:3])
            self.add_error(None, f"Aviso: Alguns números foram descartados por não serem um formato brasileiro válido (ex: {exemplos}).")

        # CORREÇÃO CRÍTICA PARA EDIÇÃO E CRIAÇÃO:
        # 1. Popula 'todos_contatos_validados' para a view de criação de lotes usar.
        cleaned_data['todos_contatos_validados'] = contatos_finais_formatados
        # 2. Popula 'contato' (o campo do modelo) com a lista final para que form.save() funcione na edição.
        cleaned_data['contato'] = contatos_finais_formatados

        if not contatos_finais_formatados:
            if not (arquivo_contatos and erro_no_processamento_do_ficheiro and not contatos_digitados_str):
                if not contatos_digitados_str and not arquivo_contatos:
                    self.add_error(None, "É obrigatório fornecer contatos (digitados ou via arquivo).")
                else: 
                    self.add_error(None, "Nenhum contato válido foi processado.")
        
        num_lotes_previstos = 0
        if contatos_finais_formatados:
            num_lotes_previstos = (len(contatos_finais_formatados) + TAMANHO_LOTE_CONTATOS_FORM - 1) // TAMANHO_LOTE_CONTATOS_FORM

        if num_lotes_previstos <= 1:
            if not cleaned_data.get('dias_disparo'): 
                self.add_error('dias_disparo', "Dia de disparo é obrigatório para envio único ou primeiro lote.")
            if not cleaned_data.get('horario_disparo'):
                self.add_error('horario_disparo', "Horário de disparo é obrigatório para envio único ou primeiro lote.")
        else: 
            if 'dias_disparo' in self._errors: del self._errors['dias_disparo']
            if 'horario_disparo' in self._errors: del self._errors['horario_disparo']
        
        modo_envio = cleaned_data.get("modo_envio")
        mensagem_notificacao = cleaned_data.get("mensagem_notificacao")
        if modo_envio == "texto" and not mensagem_notificacao:
            self.add_error('mensagem_notificacao', "A mensagem é obrigatória quando o modo de envio é 'Somente Texto'.")
        
        # Validação dos campos de botão
        incluir_botao = cleaned_data.get('incluir_botao')
        botao_texto = cleaned_data.get('botao_texto', '').strip()
        botao_url = cleaned_data.get('botao_url', '').strip()
        
        if incluir_botao:
            if not botao_texto:
                self.add_error('botao_texto', 'O texto do botão é obrigatório quando "Incluir Botão" está marcado.')
            if not botao_url:
                self.add_error('botao_url', 'A URL do botão é obrigatória quando "Incluir Botão" está marcado.')
        
        return cleaned_data

class MidiaForm(forms.ModelForm):
    tipo = forms.ChoiceField(
        choices=Midia.TIPOS_MIDIA,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tailwind_input_classes = 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
        self.fields['nome'].widget.attrs.update({'class': tailwind_input_classes})
        self.fields['tipo'].widget.attrs.update({'class': tailwind_input_classes}) 
        self.fields['descricao'].widget.attrs.update({'class': tailwind_input_classes, 'rows': 3}) 
        self.fields['arquivo'].widget.attrs.update({'class': 'w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'})


    def save(self, commit=True):
        instance = super().save(commit=False)
        if 'arquivo' in self.cleaned_data and self.cleaned_data['arquivo']:
            instance.link = instance.arquivo.url 
        if commit:
            instance.save()
        return instance
    
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')
class EvolutionAPISettingsForm(forms.ModelForm):
    # CORREÇÃO: Definimos o campo explicitamente como CharField para remover a validação de URL
    api_host = forms.CharField(
        label='URL da API Evolution',
        help_text="URL base da sua instância Evolution API. Ex: http://evolution_api:8080",
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md'})
    )

    class Meta:
        model = EvolutionAPISettings
        fields = ['api_host', 'api_key', 'is_active']
        widgets = {
            'api_key': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 border-gray-300 rounded'}),
        }
        labels = {
            'api_key': 'Chave da API (API Key)',
            'is_active': 'Ativar esta configuração'
        }
