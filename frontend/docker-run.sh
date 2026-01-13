#!/bin/bash

# BioDataMine Frontend Docker Commands
# =====================================

# Build the frontend image
build() {
    echo "Building BioDataMine frontend..."
    docker build -t biodatamine-frontend .
}

# Run the frontend container
# Usage: ./docker-run.sh run [BACKEND_URL]
# Example: ./docker-run.sh run http://192.168.1.100:8000
run() {
    BACKEND_URL="${1:-http://host.docker.internal:8000}"
    echo "Starting BioDataMine frontend..."
    echo "Backend URL: $BACKEND_URL"
    
    # Stop existing container if running
    docker stop biodatamine-frontend 2>/dev/null
    docker rm biodatamine-frontend 2>/dev/null
    
    docker run -d \
        --name biodatamine-frontend \
        -p 3000:80 \
        -e BACKEND_URL="$BACKEND_URL" \
        --add-host=host.docker.internal:host-gateway \
        biodatamine-frontend
    
    echo ""
    echo "Frontend running at http://localhost:3000"
    echo "(Backend expected at $BACKEND_URL)"
}

# Run with host networking (for when backend is on localhost)
run-host() {
    BACKEND_URL="${1:-http://localhost:8000}"
    echo "Starting BioDataMine frontend (host network mode)..."
    echo "Backend URL: $BACKEND_URL"
    
    # Stop existing container if running
    docker stop biodatamine-frontend 2>/dev/null
    docker rm biodatamine-frontend 2>/dev/null
    
    docker run -d \
        --name biodatamine-frontend \
        --network host \
        -e BACKEND_URL="$BACKEND_URL" \
        biodatamine-frontend
    
    echo ""
    echo "Frontend running at http://localhost:80"
    echo "(Backend expected at $BACKEND_URL)"
}

# Stop and remove the container
stop() {
    echo "Stopping BioDataMine frontend..."
    docker stop biodatamine-frontend 2>/dev/null
    docker rm biodatamine-frontend 2>/dev/null
    echo "Stopped."
}

# Show logs
logs() {
    docker logs -f biodatamine-frontend
}

# Show help
help() {
    echo "BioDataMine Frontend Docker Commands"
    echo "====================================="
    echo ""
    echo "Usage: ./docker-run.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  build                Build the Docker image"
    echo "  run [BACKEND_URL]    Run container on port 3000 (default backend: host.docker.internal:8000)"
    echo "  run-host [BACKEND]   Run with host networking on port 80 (for localhost backend)"
    echo "  stop                 Stop and remove the container"
    echo "  logs                 Show container logs"
    echo "  help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./docker-run.sh build"
    echo "  ./docker-run.sh run                              # Frontend at :3000, backend at host.docker.internal:8000"
    echo "  ./docker-run.sh run-host                         # Frontend at :80, backend at localhost:8000"
    echo "  ./docker-run.sh run http://192.168.1.100:8000    # Custom backend URL"
    echo "  ./docker-run.sh stop"
}

# Main
case "${1:-help}" in
    build) build ;;
    run) run "$2" ;;
    run-host) run-host "$2" ;;
    stop) stop ;;
    logs) logs ;;
    *) help ;;
esac
