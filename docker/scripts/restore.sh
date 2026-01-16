#!/bin/bash
#
# LightWMS Database Restore Script
# Usage: restore.sh <backup_file> [--verify]
#
# Environment variables required:
#   POSTGRES_HOST - PostgreSQL host
#   POSTGRES_DB - Database name
#   POSTGRES_USER - Database user
#   PGPASSWORD - Database password
#

set -e

# Configuration
DB_HOST="${POSTGRES_HOST:-db}"
DB_NAME="${POSTGRES_DB:-lightwms}"
DB_USER="${POSTGRES_USER:-lightwms}"
VERIFY_DB="${DB_NAME}_verify"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Show usage
usage() {
    echo "Usage: $0 <backup_file> [--verify]"
    echo ""
    echo "Arguments:"
    echo "  backup_file    Path to the backup file (.sql.gz)"
    echo "  --verify       Restore to a test database for verification"
    echo ""
    echo "Examples:"
    echo "  $0 /backups/daily/2024-01-15.sql.gz"
    echo "  $0 /backups/daily/2024-01-15.sql.gz --verify"
    exit 1
}

# Check if backup file exists
check_backup_file() {
    local backup_file=$1
    
    if [ ! -f "${backup_file}" ]; then
        log "ERROR: Backup file not found: ${backup_file}"
        exit 1
    fi
    
    if [ ! -s "${backup_file}" ]; then
        log "ERROR: Backup file is empty: ${backup_file}"
        exit 1
    fi
    
    log "Backup file found: ${backup_file}"
}

# Restore to main database
restore_main() {
    local backup_file=$1
    
    log "WARNING: This will overwrite the current database!"
    log "Database: ${DB_NAME} on ${DB_HOST}"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [ "${confirm}" != "yes" ]; then
        log "Restore cancelled by user"
        exit 0
    fi
    
    log "Starting restore to main database..."
    
    # Drop and recreate database
    log "Dropping existing database..."
    psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
    
    log "Creating new database..."
    psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};"
    
    # Restore from backup
    log "Restoring from backup..."
    gunzip -c "${backup_file}" | psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}"
    
    log "Restore completed successfully!"
}

# Restore to verification database
restore_verify() {
    local backup_file=$1
    
    log "Starting verification restore..."
    log "Verification database: ${VERIFY_DB}"
    
    # Drop verification database if exists
    log "Dropping existing verification database..."
    psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${VERIFY_DB};" || true
    
    # Create verification database
    log "Creating verification database..."
    psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${VERIFY_DB};"
    
    # Restore from backup
    log "Restoring from backup to verification database..."
    gunzip -c "${backup_file}" | psql -h "${DB_HOST}" -U "${DB_USER}" -d "${VERIFY_DB}"
    
    # Run basic verification queries
    log "Running verification queries..."
    
    # Count tables
    local table_count=$(psql -h "${DB_HOST}" -U "${DB_USER}" -d "${VERIFY_DB}" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    log "Tables found: ${table_count}"
    
    # Count users
    local user_count=$(psql -h "${DB_HOST}" -U "${DB_USER}" -d "${VERIFY_DB}" -t -c \
        "SELECT COUNT(*) FROM users_user;" 2>/dev/null || echo "0")
    log "Users found: ${user_count}"
    
    # Count items
    local item_count=$(psql -h "${DB_HOST}" -U "${DB_USER}" -d "${VERIFY_DB}" -t -c \
        "SELECT COUNT(*) FROM inventory_item;" 2>/dev/null || echo "0")
    log "Items found: ${item_count}"
    
    # Cleanup verification database
    log "Cleaning up verification database..."
    psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${VERIFY_DB};"
    
    log "Verification completed successfully!"
    log "Backup file is valid and can be restored."
}

# List available backups
list_backups() {
    local backup_dir="/backups"
    
    echo "Available backups:"
    echo ""
    echo "Daily backups:"
    ls -lh "${backup_dir}/daily/"*.sql.gz 2>/dev/null || echo "  No daily backups found"
    echo ""
    echo "Weekly backups:"
    ls -lh "${backup_dir}/weekly/"*.sql.gz 2>/dev/null || echo "  No weekly backups found"
    echo ""
    echo "Monthly backups:"
    ls -lh "${backup_dir}/monthly/"*.sql.gz 2>/dev/null || echo "  No monthly backups found"
}

# Main execution
main() {
    if [ $# -lt 1 ]; then
        usage
    fi
    
    local backup_file=$1
    local verify_mode=false
    
    # Check for --verify flag
    if [ "$2" = "--verify" ]; then
        verify_mode=true
    fi
    
    # Handle special commands
    if [ "${backup_file}" = "--list" ] || [ "${backup_file}" = "-l" ]; then
        list_backups
        exit 0
    fi
    
    check_backup_file "${backup_file}"
    
    if [ "${verify_mode}" = true ]; then
        restore_verify "${backup_file}"
    else
        restore_main "${backup_file}"
    fi
}

main "$@"
