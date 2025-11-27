# formulario_professores/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import CustomLoginView
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Redireciona a raiz do site para a lista de mensagens
  path('', RedirectView.as_view(url="mensagens/"), name='home'),

    # --- NOVAS URLs para Configuração da Evolution API ---
    path('evolution/config/', views.evolution_config_view, name='evolution_config'),
    path('evolution/status/', views.evolution_status_view, name='evolution_status'),
    path('evolution/instance/create/', views.evolution_create_instance, name='evolution_create_instance'),
    path('evolution/instance/disconnect/', views.evolution_disconnect_instance, name='evolution_disconnect_instance'),

    # URLs de Mensagens
    path('cadastrar/', views.cadastrar_aula, name='cadastrar_aula'),
    path('mensagens/', views.listar_aulas, name='listar_aulas'),
    path('editar/<int:mensagem_id>/', views.editar_aula, name='editar_aula'),
    path('excluir/<int:aula_id>/', views.excluir_aula, name='excluir_aula'),

    # URLs de Autenticação
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # URLs de Mídia
    path('midias/', views.listar_midias, name='listar_midias'),
    path('midias/upload/', views.upload_midia, name='upload_midia'),
    path('midias/editar/<int:midia_id>/', views.editar_midia, name='editar_midia'),
    path('midias/excluir/<int:midia_id>/', views.excluir_midia, name='excluir_midia'),
    path('midias/url/<int:midia_id>/', views.gerar_presigned_url, name='gerar_presigned_url'),
    
    # URL de Erro
    path('erro/', views.erro_view, name='erro_view'),
    
     # --- NOVAS URLS PARA EXTRAÇÃO DE CONTATOS ---
    path('exportar-contatos/', views.exportar_contatos_view, name='exportar_contatos'),
    path('api/iniciar-exportacao/', views.iniciar_exportacao_view, name='iniciar_exportacao'),
    
    path('api/status-exportacao/<str:task_id>/', views.status_exportacao_view, name='status_exportacao'),
    path('download-exportacao/<str:task_id>/', views.download_arquivo_exportado, name='download_arquivo_exportado'),
    path('api/listar-grupos/', views.listar_grupos_view, name='api_listar_grupos'),
]