#!/usr/bin/env bash
set -euo pipefail

umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${LIGHTWMS_COMPOSE_FILE:-$ROOT/docker/compose/docker-compose.dockerhub.yml}"
BACKUP_ROOT="${1:-$ROOT/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
DEST="$BACKUP_ROOT/$STAMP"

compose=(docker compose -f "$COMPOSE_FILE")
if [[ -f "$ROOT/.env" ]]; then
  compose=(docker compose --env-file "$ROOT/.env" -f "$COMPOSE_FILE")
fi

mkdir -p "$DEST"
chmod 700 "$DEST"

if [[ -z "$("${compose[@]}" ps -q db)" ]]; then
  echo "Database container is not running." >&2
  exit 1
fi
if [[ -z "$("${compose[@]}" ps -q backend)" ]]; then
  echo "Backend container is not running." >&2
  exit 1
fi

echo "[1/3] Backing up PostgreSQL..."
"${compose[@]}" exec -T db sh -ec 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DEST/database.dump"

echo "[2/3] Backing up uploaded media (including private invoices)..."
"${compose[@]}" exec -T backend tar -czf - -C /app/media . > "$DEST/media.tar.gz"

echo "[3/3] Writing integrity manifest..."
(
  cd "$DEST"
  sha256sum database.dump media.tar.gz > SHA256SUMS
  printf 'created_at=%s\n' "$(date -Iseconds)" > metadata.txt
  if [[ -f "$ROOT/VERSION" ]]; then
    printf 'lightwms_version=%s\n' "$(tr -d '[:space:]' < "$ROOT/VERSION")" >> metadata.txt
  fi
)

cat <<EOF
Backup completed: $DEST
Files are mode 600/700 by default because the archive may contain invoices and personal data.
Copy this directory to a second physical device or encrypted backup destination.
EOF
