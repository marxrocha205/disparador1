from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# Define o módulo de configurações padrão para o Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')

app = Celery('formulario_professores', broker=settings.CELERY_BROKER_URL)

# Carrega as configurações do Django no Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobre tarefas automaticamente nos aplicativos do Django
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
    print(f'Tasks Registered: {app.tasks.keys()}') 
