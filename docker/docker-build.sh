#!/bin/bash

# Docker management script for Agentic Service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="agentic-service"
TAG="latest"
COMPOSE_FILE="docker-compose.yml"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to detect Docker Compose command
detect_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null; then
        echo "docker compose"
    else
        print_error "Docker Compose not found. Please install Docker Compose first."
        exit 1
    fi
}

# Get Docker Compose command
DOCKER_COMPOSE_CMD=$(detect_docker_compose)
print_status "Using Docker Compose command: $DOCKER_COMPOSE_CMD"

# Function to check proxy settings
check_proxy_settings() {
    if [ -n "$HTTP_PROXY" ] || [ -n "$HTTPS_PROXY" ]; then
        print_status "Proxy settings detected:"
        [ -n "$HTTP_PROXY" ] && echo "  HTTP_PROXY: $HTTP_PROXY"
        [ -n "$HTTPS_PROXY" ] && echo "  HTTPS_PROXY: $HTTPS_PROXY"
        [ -n "$NO_PROXY" ] && echo "  NO_PROXY: $NO_PROXY"
    else
        print_warning "No proxy settings detected. If you experience network issues during build, set:"
        echo "  export HTTP_PROXY=http://your-proxy:port"
        echo "  export HTTPS_PROXY=http://your-proxy:port"
        echo "  export NO_PROXY=localhost,127.0.0.1"
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build       Build the Docker image"
    echo "  start       Start the service using docker-compose"
    echo "  stop        Stop the service"
    echo "  restart     Restart the service"
    echo "  logs        Show service logs"
    echo "  status      Show service status"
    echo "  clean       Clean up containers and images"
    echo "  shell       Open shell in running container"
    echo ""
    echo "Options:"
    echo "  -t, --tag TAG     Docker image tag (default: latest)"
    echo "  -f, --file FILE   Docker compose file (default: docker-compose.yml)"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  HTTP_PROXY         HTTP proxy for Docker build (if needed)"
    echo "  HTTPS_PROXY        HTTPS proxy for Docker build (if needed)"
    echo "  NO_PROXY           No proxy list for Docker build (if needed)"
}

# Function to build image
build_image() {
    print_status "Building Docker image: ${IMAGE_NAME}:${TAG}"
    print_status "Checking proxy settings..."
    check_proxy_settings
    
    # Build from parent directory to access pyproject.toml and uv.lock
    print_status "Building from project root directory..."
    
    # Build with proxy support if available
    if [ -n "$HTTP_PROXY" ] || [ -n "$HTTPS_PROXY" ]; then
        print_status "Building with proxy support..."
        docker build \
            --build-arg HTTP_PROXY="$HTTP_PROXY" \
            --build-arg HTTPS_PROXY="$HTTPS_PROXY" \
            --build-arg NO_PROXY="$NO_PROXY" \
            -f Dockerfile \
            -t "${IMAGE_NAME}:${TAG}" ..
    else
        print_status "Building without proxy settings..."
        docker build \
            -f Dockerfile \
            -t "${IMAGE_NAME}:${TAG}" ..
    fi
    
    print_success "Image built successfully!"
}

# Function to start service
start_service() {
    print_status "Starting Agentic Service..."
    
    # Check if .env file exists
    if [ ! -f "../.env" ]; then
        print_warning ".env file not found. Creating from example..."
        if [ -f "../.env.example" ]; then
            cp ../.env.example ../.env
            print_status "Please edit ../.env file with your configuration before starting the service."
            print_status "Then run: $0 start"
            exit 1
        else
            print_error ".env.example file not found. Please create a .env file manually."
            exit 1
        fi
    fi
    
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d
    print_success "Service started! Access at http://localhost:9510"
    print_status "API docs: http://localhost:9510/docs"
}

# Function to stop service
stop_service() {
    print_status "Stopping Agentic Service..."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" down
    print_success "Service stopped!"
}

# Function to restart service
restart_service() {
    print_status "Restarting Agentic Service..."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" restart
    print_success "Service restarted!"
}

# Function to show logs
show_logs() {
    print_status "Showing service logs..."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" logs -f
}

# Function to show status
show_status() {
    print_status "Service status:"
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps
    echo ""
    print_status "Container health:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# Function to clean up
clean_up() {
    print_warning "This will remove all containers and images. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up..."
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" down -v --rmi all
        docker system prune -f
        print_success "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Function to open shell
open_shell() {
    print_status "Opening shell in running container..."
    CONTAINER_ID=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps -q agentic-service)
    if [ -z "$CONTAINER_ID" ]; then
        print_error "Service is not running. Start it first with: $0 start"
        exit 1
    fi
    docker exec -it "$CONTAINER_ID" /bin/bash
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        build|start|stop|restart|logs|status|clean|shell)
            COMMAND="$1"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if command is provided
if [ -z "$COMMAND" ]; then
    print_error "No command specified"
    show_usage
    exit 1
fi

# Execute command
case $COMMAND in
    build)
        build_image
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    clean)
        clean_up
        ;;
    shell)
        open_shell
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac
