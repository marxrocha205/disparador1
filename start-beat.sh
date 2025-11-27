#!/bin/bash

echo "⏰ Preparando Celery Beat..."

# Aguarda um pouco para garantir que o django-web já iniciou
echo "🔄 Aguardando django-web executar migrações..."
sleep 30

# Tenta conectar ao banco e verifica se a tabela existe
echo "🔍 Verificando se as migrações foram aplicadas..."
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    # Tenta executar um comando Python para verificar a tabela
    if python -c "
import django
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM django_celery_beat_periodictask LIMIT 1')
        count = cursor.fetchone()[0]
        print(f'✅ Tabela encontrada com {count} registros!')
        sys.exit(0)
except Exception as e:
    print(f'❌ Erro: {e}')
    sys.exit(1)
" 2>&1; then
        echo "✅ Migrações aplicadas! Iniciando Celery Beat..."
        break
    else
        echo "⏳ Aguardando migrações... (tentativa $((attempt + 1))/$max_attempts)"
        sleep 10
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Timeout aguardando migrações."
    echo "🔍 Tentando executar migrações manualmente..."
    python manage.py migrate --no-input
    echo "✅ Migrações executadas! Iniciando Celery Beat..."
fi

# Inicia o Celery Beat
echo "🎯 Iniciando Celery Beat..."
exec celery -A setup beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
