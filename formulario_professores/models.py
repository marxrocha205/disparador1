# formularios/models.py
import uuid
from django.db import models
from django.contrib.auth.models import User
from storages.backends.s3boto3 import S3Boto3Storage
import boto3
from django.conf import settings
from django.core.cache import cache
import mimetypes
class EvolutionAPISettings(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # CORREÇÃO DEFINITIVA: Trocado de URLField para CharField
    api_host = models.CharField(
        max_length=255,
        verbose_name="URL da API Evolution",
        help_text="URL base da sua instância Evolution API. Ex: http://evolution_api:8080"
    )
    
    api_key = models.CharField(
        max_length=255,
        verbose_name="Chave da API (API Key)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    def __str__(self):
        return f"Configuração da API para {self.usuario.username}"

    class Meta:
        verbose_name = "Configuração da Evolution API"
        verbose_name_plural = "Configurações da Evolution API"

class Instancia(models.Model):
    """Gerencia as instâncias (sessões) da Evolution API para um usuário."""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instancia')
    nome_instancia = models.CharField(max_length=100, unique=True, help_text="Nome único para a instância/sessão. Ex: instancia_padrao")
    conectado = models.BooleanField(default=False)
    ultimo_status_check = models.DateTimeField(null=True, blank=True)
    dados_qr_code = models.TextField(blank=True, null=True)

    def __str__(self):
        status = "Conectado" if self.conectado else "Desconectado"
        return f"Instância '{self.nome_instancia}' de {self.usuario.username} ({status})"

    def get_cached_status(self):
        """Busca o status da conexão do cache para evitar chamadas excessivas."""
        cache_key = f'evolution_status_{self.id}'
        status = cache.get(cache_key)
        if status is None:
            # Se não estiver no cache, a view irá chamar a API e atualizar o cache.
            return self.conectado # Retorna o último estado conhecido do banco
        return status.get('connected', False)

# --- Modelos existentes (mantidos como estão) ---

class Mensagem(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    dias_disparo = models.JSONField(blank=False)
    horario_disparo = models.TimeField(blank=False)
    contato = models.JSONField(blank=False)
    intervalo_disparo = models.IntegerField()
    mensagem_notificacao = models.TextField(blank=True)
    
    tipo_envio = models.CharField(
        max_length=15,
        choices=[
            ("texto_primeiro", "Texto Primeiro"),
            ("midia_primeiro", "Mídia Primeiro")
        ],
        default="texto_primeiro"
    )
    
    modo_envio = models.CharField(
        max_length=10,
        choices=[
            ("texto", "Somente Texto"),
            ("midia", "Somente Mídia"),
            ("ambos", "Ambos")
        ],
        default="texto"
    )
    
    # Campos para botões URL
    incluir_botao = models.BooleanField(default=False, verbose_name="Incluir Botão com Link")
    botao_texto = models.CharField(max_length=100, blank=True, null=True, verbose_name="Texto do Botão")
    botao_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="URL do Botão")

    ordem_envio = models.IntegerField(default=0)
    id_campanha = models.UUIDField(default=uuid.uuid4, editable=False, help_text="Loteamento")
    midia = models.ForeignKey('Midia', on_delete=models.SET_NULL, null=True, blank=True, related_name="mensagens")


class Enviadas(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField()
    data_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mensagem enviada por {self.user.username} em {self.data_envio}"

class UserMessageLimit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    limite_diario = models.IntegerField(default=65)

    def __str__(self):
        return f"{self.user.username} - Limite: {self.limite_diario} mensagens/dia"
    
    class Meta:
        verbose_name = "Limite de Mensagens do Usuário"
        verbose_name_plural = "Limites de Mensagens dos Usuários"


class Midia(models.Model):
    TIPOS_MIDIA = [
        ('image', 'Imagem'),
        ('video', 'Vídeo'),
        ('audio', 'Áudio'),
        ('document', 'Documento'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPOS_MIDIA)
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, null=True)
    link = models.URLField(blank=True, null=True, max_length=500)
    arquivo = models.FileField(upload_to='midia/', storage=S3Boto3Storage())
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='midias')
    mimetype = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nome
    
    def get_presigned_url(self):
        if not self.arquivo:
            return None
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        try:
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': self.arquivo.name
                },
                ExpiresIn=3600
            )
            return url
        except Exception as e:
            return None
            
    def delete(self, *args, **kwargs):
        if self.arquivo:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            try:
                s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=self.arquivo.name)
            except Exception as e:
                print(f"Erro ao excluir do S3: {e}")

        super().delete(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        if self.arquivo and not self.mimetype:
            mime, _ = mimetypes.guess_type(self.arquivo.name)
        if mime:
            self.mimetype = mime
        else:
            # Define um valor padrão genérico para evitar None
            self.mimetype = 'application/octet-stream'
        super().save(*args, **kwargs)


class MidiaMensagem(models.Model):
    mensagem = models.ForeignKey('Mensagem', on_delete=models.CASCADE, related_name="mensagem_midias")
    midia = models.ForeignKey(Midia, on_delete=models.CASCADE, related_name="midia_mensagens")