#!/bin/bash

# Script de inicialização para o Railway
echo "🚀 Iniciando aplicação Django..."

# Executa as migrações do banco de dados
echo "📦 Executando migrações..."
python manage.py migrate --no-input

# Cria superusuário automaticamente se não existir
echo "👤 Verificando superusuário..."
python manage.py create_superuser

# Coleta arquivos estáticos (já feito no build, mas garante)
echo "📁 Verificando arquivos estáticos..."
python manage.py collectstatic --no-input --clear

# Inicia o Gunicorn
echo "🌐 Iniciando servidor Gunicorn na porta $PORT..."
exec gunicorn setup.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120 --access-logfile - --error-logfile -
