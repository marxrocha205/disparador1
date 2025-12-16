# formularios/admin.py
from django.contrib import admin
from .models import EvolutionAPISettings, Instancia, Mensagem, Midia, UserMessageLimit, Enviadas

@admin.register(EvolutionAPISettings)
class EvolutionAPISettingsAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'api_host', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('usuario__username', 'api_host')

@admin.register(Instancia)
class InstanciaAdmin(admin.ModelAdmin):
    list_display = ('nome_instancia', 'usuario', 'conectado', 'ultimo_status_check')
    list_filter = ('conectado',)
    search_fields = ('nome_instancia', 'usuario__username')
    readonly_fields = ('conectado', 'ultimo_status_check', 'dados_qr_code')

@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'horario_disparo', 'id_campanha')
    list_filter = ('usuario',)
    search_fields = ('id_campanha', 'usuario__username')

@admin.register(Midia)
class MidiaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'usuario')
    list_filter = ('tipo', 'usuario')
    search_fields = ('nome', 'descricao')

admin.site.register(UserMessageLimit)
admin.site.register(Enviadas)