#!/bin/bash

echo "👷 Preparando Celery Worker..."

# Aguarda um pouco para garantir que o django-web já iniciou
echo "🔄 Aguardando django-web executar migrações..."
sleep 20

echo "✅ Iniciando Celery Worker..."
exec celery -A setup worker --loglevel=info --concurrency=2
