#!/bin/sh
# wait-for-db.sh

set -e

host="$1"
shift
cmd="$@"

# Loop até que o pg_isready retorne 0 (sucesso)
# Você pode precisar instalar postgresql-client no seu Dockerfile para ter pg_isready
# RUN apt-get update && apt-get install -y postgresql-client ...
# Ou usar netcat (nc) se preferir e se estiver disponível:
# until nc -z "$host" 5432; do
# >&2 echo "Postgres is unavailable - sleeping"
# sleep 1
# done

# Usando um loop simples com timeout para evitar espera infinita
# e sem dependências extras, apenas netcat (que muitas imagens base têm, ou pode ser adicionado)
# Se não tiver nc, uma alternativa é tentar conectar com psql periodicamente,
# mas isso requer postgresql-client.

# Alternativa mais simples com um timeout (ex: 60 segundos)
timeout_seconds=60
interval_seconds=2
elapsed_seconds=0

echo "Waiting for $host:5432..."
while ! nc -z "$host" 5432 && [ $elapsed_seconds -lt $timeout_seconds ]; do
  echo "PostgreSQL is unavailable at $host:5432 - sleeping for $interval_seconds seconds..."
  sleep $interval_seconds
  elapsed_seconds=$((elapsed_seconds + interval_seconds))
done

if [ $elapsed_seconds -ge $timeout_seconds ]; then
  echo "Timeout: PostgreSQL at $host:5432 is still unavailable after $timeout_seconds seconds."
  exit 1
fi

>&2 echo "PostgreSQL is up - executing command: $cmd"
exec $cmd