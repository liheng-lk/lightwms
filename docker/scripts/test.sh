#!/bin/bash
#
# LightWMS Test Runner Script
#
# This script ensures PostgreSQL is running and runs the test suite.
#
# Usage:
#   ./scripts/test.sh              # Run all tests
#   ./scripts/test.sh -v           # Run with verbose output
#   ./scripts/test.sh tests/test_auth.py  # Run specific test file
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-lightwms}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-lightwms_secret}"
POSTGRES_DB="${POSTGRES_DB:-lightwms_test}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if PostgreSQL is running
check_postgres() {
    log_info "Checking PostgreSQL connection..."
    
    if command -v pg_isready &> /dev/null; then
        if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" &> /dev/null; then
            log_info "PostgreSQL is ready"
            return 0
        fi
    fi
    
    # Try connecting with psql
    if command -v psql &> /dev/null; then
        if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "SELECT 1" &> /dev/null; then
            log_info "PostgreSQL is ready"
            return 0
        fi
    fi
    
    return 1
}

# Start PostgreSQL via docker-compose if not running
start_postgres() {
    log_warn "PostgreSQL is not running. Attempting to start via docker-compose..."
    
    if [ -f "docker-compose.yml" ]; then
        docker-compose up -d db
        
        # Wait for PostgreSQL to be ready
        log_info "Waiting for PostgreSQL to be ready..."
        for i in {1..30}; do
            if check_postgres; then
                return 0
            fi
            sleep 1
        done
        
        log_error "PostgreSQL failed to start within 30 seconds"
        return 1
    else
        log_error "docker-compose.yml not found. Please start PostgreSQL manually."
        return 1
    fi
}

# Create test database if it doesn't exist
create_test_db() {
    log_info "Ensuring test database exists..."
    
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DB'" | grep -q 1 || \
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB"
    
    log_info "Test database '$POSTGRES_DB' is ready"
}

# Main execution
main() {
    # Change to project root
    cd "$(dirname "$0")/.."
    
    # Check/start PostgreSQL
    if ! check_postgres; then
        if ! start_postgres; then
            log_error "Cannot connect to PostgreSQL. Please ensure it's running."
            echo ""
            echo "To start PostgreSQL:"
            echo "  docker-compose up -d db"
            echo ""
            echo "Or set DATABASE_URL to an existing PostgreSQL instance:"
            echo "  export DATABASE_URL=postgres://user:pass@host:5432/dbname"
            exit 1
        fi
    fi
    
    # Create test database
    create_test_db
    
    # Set DATABASE_URL for tests
    export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
    
    log_info "Running tests with DATABASE_URL=$DATABASE_URL"
    echo ""
    
    # Run pytest
    cd backend
    python -m pytest "$@"
}

main "$@"
