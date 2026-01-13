#!/bin/bash

# BioDataMine Docker Commands
# ============================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# BUILD COMMANDS
# =============================================================================

build_ui() {
    log_info "Building frontend Docker image..."
    cd "$PROJECT_ROOT/frontend"
    docker build -t biodatamine-frontend .
    if [ $? -eq 0 ]; then
        log_success "Frontend image built successfully"
    else
        log_error "Frontend build failed"
        exit 1
    fi
}

build_api() {
    log_info "Building backend Docker image..."
    cd "$PROJECT_ROOT"
    docker build -t biodatamine-backend -f backend/Dockerfile .
    if [ $? -eq 0 ]; then
        log_success "Backend image built successfully"
    else
        log_error "Backend build failed"
        exit 1
    fi
}

build() {
    log_info "Building all Docker images..."
    build_api
    build_ui
    log_success "All images built successfully"
}

# =============================================================================
# RUN COMMANDS
# =============================================================================

run_ui() {
    BACKEND_URL="${1:-http://localhost:8000}"
    log_info "Starting frontend container..."
    log_info "Backend URL: $BACKEND_URL"
    
    # Stop existing container if running
    docker stop biodatamine-frontend 2>/dev/null
    docker rm biodatamine-frontend 2>/dev/null
    
    docker run -d \
        --name biodatamine-frontend \
        --network host \
        -e BACKEND_URL="$BACKEND_URL" \
        biodatamine-frontend
    
    if [ $? -eq 0 ]; then
        log_success "Frontend running at http://localhost:3000"
    else
        log_error "Failed to start frontend"
        exit 1
    fi
}

run_api() {
    MONGO_URL="${1:-mongodb://localhost:27017}"
    log_info "Starting backend container..."
    log_info "MongoDB URL: $MONGO_URL"
    
    # Stop existing container if running
    docker stop biodatamine-backend 2>/dev/null
    docker rm biodatamine-backend 2>/dev/null
    
    docker run -d \
        --name biodatamine-backend \
        --network host \
        -e DATASCAN_MONGO_URL="$MONGO_URL" \
        -e DATASCAN_MONGO_DB="datascan" \
        -e DATASCAN_DATA_ROOT="/tmp/datascan" \
        -e DATASCAN_PIPELINE_ENABLED="true" \
        -v /tmp/datascan:/tmp/datascan \
        biodatamine-backend
    
    if [ $? -eq 0 ]; then
        log_success "Backend running at http://localhost:8000"
    else
        log_error "Failed to start backend"
        exit 1
    fi
}

run() {
    log_info "Starting all containers..."
    run_api "$1"
    run_ui "$2"
    echo ""
    log_success "BioDataMine is running!"
    echo "  - Frontend: http://localhost:3000"
    echo "  - Backend:  http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
}

# =============================================================================
# STOP COMMANDS
# =============================================================================

stop_ui() {
    log_info "Stopping frontend..."
    docker stop biodatamine-frontend 2>/dev/null
    docker rm biodatamine-frontend 2>/dev/null
    log_success "Frontend stopped"
}

stop_api() {
    log_info "Stopping backend..."
    docker stop biodatamine-backend 2>/dev/null
    docker rm biodatamine-backend 2>/dev/null
    log_success "Backend stopped"
}

stop() {
    log_info "Stopping all containers..."
    stop_ui
    stop_api
    log_success "All containers stopped"
}

# =============================================================================
# UTILITY COMMANDS
# =============================================================================

logs_ui() {
    docker logs -f biodatamine-frontend
}

logs_api() {
    docker logs -f biodatamine-backend
}

status() {
    echo ""
    log_info "Container Status:"
    echo "----------------------------------------"
    docker ps -a --filter "name=biodatamine" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
}

# =============================================================================
# HELP
# =============================================================================

help() {
    echo ""
    echo -e "${CYAN}BioDataMine Docker Commands${NC}"
    echo "========================================"
    echo ""
    echo "Usage: ./docker-run.sh <command> [args]"
    echo ""
    echo -e "${GREEN}Build Commands:${NC}"
    echo "  build              Build all Docker images (frontend + backend)"
    echo "  build-ui           Build frontend Docker image only"
    echo "  build-api          Build backend Docker image only"
    echo ""
    echo -e "${GREEN}Run Commands:${NC}"
    echo "  run [MONGO] [API]  Run all containers"
    echo "  run-ui [API_URL]   Run frontend only (default API: http://localhost:8000)"
    echo "  run-api [MONGO]    Run backend only (default MongoDB: mongodb://localhost:27017)"
    echo ""
    echo -e "${GREEN}Stop Commands:${NC}"
    echo "  stop               Stop all containers"
    echo "  stop-ui            Stop frontend container"
    echo "  stop-api           Stop backend container"
    echo ""
    echo -e "${GREEN}Utility Commands:${NC}"
    echo "  logs-ui            Show frontend logs"
    echo "  logs-api           Show backend logs"
    echo "  status             Show container status"
    echo "  help               Show this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  ./docker-run.sh build                    # Build all images"
    echo "  ./docker-run.sh run                      # Run with defaults"
    echo "  ./docker-run.sh run-api                  # Run backend only"
    echo "  ./docker-run.sh run-ui                   # Run frontend only"
    echo "  ./docker-run.sh stop                     # Stop everything"
    echo "  ./docker-run.sh status                   # Check what's running"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

case "${1:-help}" in
    build)     build ;;
    build-ui)  build_ui ;;
    build-api) build_api ;;
    run)       run "$2" "$3" ;;
    run-ui)    run_ui "$2" ;;
    run-api)   run_api "$2" ;;
    stop)      stop ;;
    stop-ui)   stop_ui ;;
    stop-api)  stop_api ;;
    logs-ui)   logs_ui ;;
    logs-api)  logs_api ;;
    status)    status ;;
    *)         help ;;
esac

