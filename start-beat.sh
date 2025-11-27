#!/bin/bash

echo "⏰ Preparando Celery Beat..."

# Aguarda um pouco para garantir que o django-web já iniciou
echo "🔄 Aguardando django-web executar migrações..."
sleep 30

# Tenta conectar ao banco e verifica se a tabela existe
echo "🔍 Verificando se as migrações foram aplicadas..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(\"SELECT 1 FROM django_celery_beat_periodictask LIMIT 1\")
    print('Tabela encontrada!')
" 2>/dev/null; then
        echo "✅ Migrações aplicadas! Iniciando Celery Beat..."
        break
    else
        echo "⏳ Aguardando migrações... (tentativa $((attempt + 1))/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Timeout aguardando migrações. Tentando iniciar mesmo assim..."
fi

# Inicia o Celery Beat
exec celery -A setup beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
