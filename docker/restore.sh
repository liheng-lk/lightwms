#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${LIGHTWMS_COMPOSE_FILE:-$ROOT/docker/compose/docker-compose.dockerhub.yml}"
BACKUP_DIR="${1:-}"
CONFIRM="${2:-}"

if [[ -z "$BACKUP_DIR" || "$CONFIRM" != "--yes" ]]; then
  echo "Usage: bash docker/restore.sh <backup-directory> --yes" >&2
  echo "Restore is destructive and will replace the current database and media files." >&2
  exit 2
fi

BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd)"
for file in database.dump media.tar.gz SHA256SUMS; do
  [[ -f "$BACKUP_DIR/$file" ]] || { echo "Missing backup file: $file" >&2; exit 1; }
done

compose=(docker compose -f "$COMPOSE_FILE")
if [[ -f "$ROOT/.env" ]]; then
  compose=(docker compose --env-file "$ROOT/.env" -f "$COMPOSE_FILE")
fi

(
  cd "$BACKUP_DIR"
  sha256sum -c SHA256SUMS
)

echo "Creating a pre-restore safety backup..."
bash "$ROOT/docker/backup.sh" "$ROOT/backups"

echo "Stopping application traffic..."
"${compose[@]}" stop frontend backend || true
"${compose[@]}" up -d db redis

echo "Restoring PostgreSQL..."
cat "$BACKUP_DIR/database.dump" | "${compose[@]}" exec -T db sh -ec \
  'pg_restore --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

echo "Starting backend without frontend traffic..."
"${compose[@]}" up -d backend

for attempt in $(seq 1 60); do
  if "${compose[@]}" exec -T backend python -c \
      "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/', timeout=2)" \
      >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 60 ]]; then
    echo "Backend did not become healthy after database restore; frontend remains stopped." >&2
    exit 1
  fi
  sleep 2
done

echo "Replacing media files..."
"${compose[@]}" exec -T backend sh -ec \
  'find /app/media -mindepth 1 -maxdepth 1 -exec rm -rf {} +'
cat "$BACKUP_DIR/media.tar.gz" | "${compose[@]}" exec -T backend tar -xzf - -C /app/media

echo "Restarting application..."
"${compose[@]}" restart backend
"${compose[@]}" up -d frontend

echo "Restore completed from: $BACKUP_DIR"
