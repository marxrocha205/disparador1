# --- Estágio 1: Build ---
# Usamos uma imagem Python completa que já vem com as ferramentas de compilação.
FROM python:3.10-slim as builder

# Define o diretório de trabalho
WORKDIR /app

# Instala as dependências do sistema necessárias APENAS para construir as bibliotecas Python.
# libpq-dev é necessário para compilar o psycopg2.
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos primeiro para aproveitar o cache do Docker.
COPY requirements.txt .

# Em vez de 'pip install', usamos 'pip wheel'. Isso compila todas as suas dependências
# em arquivos .whl, que são como "instaladores" pré-prontos.
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# --- Estágio 2: Final ---
# Começamos com uma imagem "slim" e limpa para a nossa aplicação final.
FROM python:3.10-slim

# Define o diretório de trabalho
WORKDIR /app

# Instala APENAS as dependências de sistema necessárias para RODAR a aplicação.
# libpq5 é a biblioteca do PostgreSQL (muito menor que libpq-dev).
# ffmpeg continua aqui, pois sua aplicação precisa dele em tempo de execução.
RUN apt-get update && apt-get install -y libpq5 ffmpeg && rm -rf /var/lib/apt/lists/*

# Copia as dependências pré-compiladas (wheels) do estágio 'builder'.
COPY --from=builder /app/wheels /wheels

# Instala as dependências a partir dos wheels. Este passo é muito mais rápido
# e não precisa de ferramentas de compilação.
RUN pip install --no-cache /wheels/*

# Agora, copia todo o código da sua aplicação para a imagem final.
COPY . .

# Executa o collectstatic. Essencial para que o WhiteNoise sirva seus arquivos CSS/JS.
RUN python manage.py collectstatic --no-input

# Torna o script de inicialização executável
RUN chmod +x start.sh

# Expõe a porta que o Gunicorn/Django vai usar.
# O Railway vai fornecer a porta correta através da variável de ambiente $PORT.
EXPOSE 8000

# Comando que usa a variável $PORT fornecida pelo Railway
CMD ["./start.sh"]
# Ex: gunicorn setup.wsgi:application --bind 0.0.0.0:$PORT