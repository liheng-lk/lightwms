#!/bin/bash
#
# LightWMS Deployment Script
# Usage: deploy.sh [start|stop|restart|update|status|logs|init]
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"; exit 1
    fi
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"; exit 1
    fi
    if [ ! -f "${PROJECT_DIR}/.env" ]; then
        log_warn ".env file not found. Creating from .env.example..."
        if [ -f "${PROJECT_DIR}/.env.example" ]; then
            cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
            log_warn "Please edit .env file with your configuration before deploying"; exit 1
        else
            log_error ".env.example not found"; exit 1
        fi
    fi
    log_info "Prerequisites check passed"
}

# Get docker compose command
get_compose_cmd() {
    if docker compose version &> /dev/null; then echo "docker compose"; else echo "docker-compose"; fi
}

# Start services
start_services() {
    log_info "Starting LightWMS services..."
    cd "${PROJECT_DIR}"
    $(get_compose_cmd) -f "${COMPOSE_FILE}" up -d
    log_info "Services started successfully"
    show_status
}

# Stop services
stop_services() {
    log_info "Stopping LightWMS services..."
    cd "${PROJECT_DIR}"
    $(get_compose_cmd) -f "${COMPOSE_FILE}" down
    log_info "Services stopped"
}

# Restart services
restart_services() {
    log_info "Restarting LightWMS services..."
    stop_services
    start_services
}

# Update and rebuild
update_services() {
    log_info "Updating LightWMS..."
    cd "${PROJECT_DIR}"
    if [ -d "${PROJECT_DIR}/.git" ]; then
        log_info "Pulling latest code..."; git pull
    fi
    log_info "Rebuilding Docker images..."
    $(get_compose_cmd) -f "${COMPOSE_FILE}" build --no-cache
    log_info "Restarting services with new images..."
    $(get_compose_cmd) -f "${COMPOSE_FILE}" up -d
    log_info "Running database migrations..."
    $(get_compose_cmd) -f "${COMPOSE_FILE}" exec -T web python manage.py migrate --noinput
    log_info "Collecting static files..."
    $(get_compose_cmd) -f "${COMPOSE_FILE}" exec -T web python manage.py collectstatic --noinput
    log_info "Update completed successfully"
    show_status
}

# Show service status
show_status() {
    log_info "Service status:"
    cd "${PROJECT_DIR}"
    $(get_compose_cmd) -f "${COMPOSE_FILE}" ps
}

# Show logs
show_logs() {
    local service=${1:-}
    cd "${PROJECT_DIR}"
    if [ -n "${service}" ]; then
        $(get_compose_cmd) -f "${COMPOSE_FILE}" logs -f "${service}"
    else
        $(get_compose_cmd) -f "${COMPOSE_FILE}" logs -f
    fi
}


# Initialize deployment (first time setup)
init_deployment() {
    log_info "Initializing LightWMS deployment..."
    check_prerequisites
    log_info "Creating directories..."
    mkdir -p "${PROJECT_DIR}/nginx/ssl" "${PROJECT_DIR}/backup"
    log_info "Building Docker images..."
    cd "${PROJECT_DIR}"
    $(get_compose_cmd) -f "${COMPOSE_FILE}" build
    log_info "Starting services..."
    $(get_compose_cmd) -f "${COMPOSE_FILE}" up -d
    log_info "Waiting for database to be ready..."
    sleep 10
    log_info "Running database migrations..."
    $(get_compose_cmd) -f "${COMPOSE_FILE}" exec -T web python manage.py migrate --noinput
    log_info "Collecting static files..."
    $(get_compose_cmd) -f "${COMPOSE_FILE}" exec -T web python manage.py collectstatic --noinput
    log_info "Creating initial superuser..."
    $(get_compose_cmd) -f "${COMPOSE_FILE}" exec -T web python manage.py shell -c "
from apps.users.models import User
if not User.objects.filter(role='super_admin').exists():
    import os
    User.objects.create_superuser(
        username=os.environ.get('ADMIN_USERNAME', 'admin'),
        password=os.environ.get('ADMIN_PASSWORD', 'admin123'),
        email=os.environ.get('ADMIN_EMAIL', 'admin@example.com'),
        role='super_admin'
    )
    print('Superuser created')
else:
    print('Superuser already exists')
" || log_warn "Could not create superuser automatically"
    log_info "Initialization completed!"
    show_status
    echo ""
    log_info "LightWMS is now running at http://localhost"
    log_info "API documentation: http://localhost/api/docs/"
}

# Show usage
usage() {
    echo "LightWMS Deployment Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  init      Initialize deployment (first time setup)"
    echo "  start     Start all services"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  update    Update and rebuild services"
    echo "  status    Show service status"
    echo "  logs      Show logs (optionally specify service: logs web)"
    echo "  help      Show this help message"
}

# Main
main() {
    local command=${1:-help}
    case "${command}" in
        init) init_deployment ;;
        start) check_prerequisites; start_services ;;
        stop) stop_services ;;
        restart) check_prerequisites; restart_services ;;
        update) check_prerequisites; update_services ;;
        status) show_status ;;
        logs) shift; show_logs "$@" ;;
        help|--help|-h) usage ;;
        *) log_error "Unknown command: ${command}"; usage; exit 1 ;;
    esac
}

main "$@"
