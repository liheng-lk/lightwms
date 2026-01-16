#!/bin/bash
#
# LightWMS Database Backup Script
# Usage: backup.sh [daily|weekly|monthly|cleanup]
#
# Environment variables required:
#   POSTGRES_HOST - PostgreSQL host
#   POSTGRES_DB - Database name
#   POSTGRES_USER - Database user
#   PGPASSWORD - Database password (set automatically from POSTGRES_PASSWORD)
#

set -e

# Configuration
BACKUP_DIR="/backups"
DAILY_DIR="${BACKUP_DIR}/daily"
WEEKLY_DIR="${BACKUP_DIR}/weekly"
MONTHLY_DIR="${BACKUP_DIR}/monthly"

# Retention policy
DAILY_RETENTION=7      # Keep 7 daily backups
WEEKLY_RETENTION=4     # Keep 4 weekly backups
MONTHLY_RETENTION=12   # Keep 12 monthly backups

# Database connection
DB_HOST="${POSTGRES_HOST:-db}"
DB_NAME="${POSTGRES_DB:-lightwms}"
DB_USER="${POSTGRES_USER:-lightwms}"

# Timestamp
DATE=$(date +%Y-%m-%d)
DATETIME=$(date +%Y-%m-%d_%H-%M-%S)

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Create backup directories if they don't exist
create_dirs() {
    mkdir -p "${DAILY_DIR}" "${WEEKLY_DIR}" "${MONTHLY_DIR}"
}

# Perform database backup
do_backup() {
    local backup_type=$1
    local backup_dir=$2
    local backup_file="${backup_dir}/${DATE}.sql.gz"
    
    log "Starting ${backup_type} backup..."
    
    # Check if backup already exists for today
    if [ -f "${backup_file}" ]; then
        log "Backup for ${DATE} already exists, skipping..."
        return 0
    fi
    
    # Perform pg_dump and compress
    pg_dump -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" \
        --no-password \
        --format=plain \
        --no-owner \
        --no-privileges \
        | gzip > "${backup_file}"
    
    # Verify backup was created
    if [ -f "${backup_file}" ] && [ -s "${backup_file}" ]; then
        local size=$(du -h "${backup_file}" | cut -f1)
        log "${backup_type} backup completed: ${backup_file} (${size})"
    else
        log "ERROR: Backup file was not created or is empty"
        exit 1
    fi
}

# Cleanup old backups based on retention policy
cleanup_old_backups() {
    local backup_dir=$1
    local retention=$2
    local backup_type=$3
    
    log "Cleaning up old ${backup_type} backups (keeping ${retention})..."
    
    # Count existing backups
    local count=$(ls -1 "${backup_dir}"/*.sql.gz 2>/dev/null | wc -l)
    
    if [ "${count}" -gt "${retention}" ]; then
        local to_delete=$((count - retention))
        log "Removing ${to_delete} old ${backup_type} backup(s)..."
        
        # Remove oldest backups
        ls -1t "${backup_dir}"/*.sql.gz | tail -n "${to_delete}" | xargs rm -f
    else
        log "No ${backup_type} backups to clean up (${count}/${retention})"
    fi
}

# Main execution
main() {
    local action=${1:-daily}
    
    create_dirs
    
    case "${action}" in
        daily)
            do_backup "daily" "${DAILY_DIR}"
            ;;
        weekly)
            do_backup "weekly" "${WEEKLY_DIR}"
            ;;
        monthly)
            do_backup "monthly" "${MONTHLY_DIR}"
            ;;
        cleanup)
            cleanup_old_backups "${DAILY_DIR}" "${DAILY_RETENTION}" "daily"
            cleanup_old_backups "${WEEKLY_DIR}" "${WEEKLY_RETENTION}" "weekly"
            cleanup_old_backups "${MONTHLY_DIR}" "${MONTHLY_RETENTION}" "monthly"
            ;;
        all)
            # Run all backup types (useful for initial setup)
            do_backup "daily" "${DAILY_DIR}"
            do_backup "weekly" "${WEEKLY_DIR}"
            do_backup "monthly" "${MONTHLY_DIR}"
            ;;
        *)
            echo "Usage: $0 [daily|weekly|monthly|cleanup|all]"
            exit 1
            ;;
    esac
    
    log "Backup operation '${action}' completed successfully"
}

main "$@"
