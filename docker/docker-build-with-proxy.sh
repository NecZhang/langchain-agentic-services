#!/bin/bash

# Docker build script with proxy support for Ubuntu systems
# This script ensures consistent dependency management with local development using uv

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
DOCKERFILE="Dockerfile"
BUILD_CONTEXT=".."
MAX_RETRIES=3
RETRY_DELAY=10

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

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build       Build the Docker image (default)"
    echo "  build-prod  Build production Docker image"
    echo "  clean       Clean up Docker resources"
    echo ""
    echo "Options:"
    echo "  -t, --tag TAG         Docker image tag (default: latest)"
    echo "  -n, --name NAME       Docker image name (default: agentic-service)"
    echo "  -p, --proxy           Enable proxy for apt-get and pip"
    echo "  -f, --file FILE       Dockerfile to use (default: Dockerfile)"
    echo "  -r, --retries N       Maximum retry attempts (default: 3)"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  HTTP_PROXY            HTTP proxy for Docker build"
    echo "  HTTPS_PROXY           HTTPS proxy for Docker build"
    echo "  NO_PROXY              No proxy list for Docker build"
    echo ""
    echo "Examples:"
    echo "  $0 build                    # Build with default settings"
    echo "  $0 build-prod               # Build production image"
    echo "  $0 -p build                 # Build with proxy support"
    echo "  $0 -t v1.0.0 build         # Build with specific tag"
    echo "  $0 -r 5 -p build           # Build with proxy and 5 retries"
    echo "  export HTTP_PROXY=http://proxy:port && $0 -p build  # Build with proxy"
}

# Function to check proxy settings
check_proxy_settings() {
    if [ -n "$HTTP_PROXY" ] || [ -n "$HTTPS_PROXY" ]; then
        print_status "Proxy settings detected:"
        [ -n "$HTTP_PROXY" ] && echo "  HTTP_PROXY: $HTTP_PROXY"
        [ -n "$HTTPS_PROXY" ] && echo "  HTTPS_PROXY: $HTTPS_PROXY"
        [ -n "$NO_PROXY" ] && echo "  NO_PROXY: $NO_PROXY"
        return 0
    else
        print_warning "No proxy settings detected."
        return 1
    fi
}

# Function to build image with retry logic
build_image() {
    local dockerfile_path="$1"
    local build_args=""
    local attempt=1
    
    print_status "Building Docker image: ${IMAGE_NAME}:${TAG}"
    print_status "Using Dockerfile: $dockerfile_path"
    print_status "Build context: $BUILD_CONTEXT"
    print_status "Maximum retries: $MAX_RETRIES"
    
    # Check proxy settings
    if check_proxy_settings; then
        print_status "Building with proxy support..."
        build_args="--build-arg HTTP_PROXY=$HTTP_PROXY --build-arg HTTPS_PROXY=$HTTPS_PROXY --build-arg NO_PROXY=$NO_PROXY"
    else
        print_warning "Building without proxy settings. If you experience network issues, set proxy environment variables."
        print_warning "Example: export HTTP_PROXY=http://your-proxy:port"
    fi
    
    # Build with retry logic
    while [ $attempt -le $MAX_RETRIES ]; do
        print_status "Build attempt $attempt of $MAX_RETRIES..."
        
        if docker build \
            $build_args \
            -f "$dockerfile_path" \
            -t "${IMAGE_NAME}:${TAG}" \
            "$BUILD_CONTEXT"; then
            
            print_success "Image built successfully: ${IMAGE_NAME}:${TAG}"
            print_status "You can now run: docker run -p 9211:9211 ${IMAGE_NAME}:${TAG}"
            return 0
        else
            print_warning "Build attempt $attempt failed!"
            
            if [ $attempt -lt $MAX_RETRIES ]; then
                print_status "Waiting $RETRY_DELAY seconds before retry..."
                sleep $RETRY_DELAY
                
                # Clean up failed build cache
                print_status "Cleaning up failed build cache..."
                docker builder prune -f
            else
                print_error "All build attempts failed after $MAX_RETRIES retries!"
                print_error "This might be due to:"
                print_error "  - Network connectivity issues"
                print_error "  - Proxy configuration problems"
                print_error "  - Docker daemon issues"
                print_error "  - Insufficient disk space"
                print_error ""
                print_error "Try:"
                print_error "  - Check your proxy settings"
                print_error "  - Verify network connectivity"
                print_error "  - Increase retry attempts: $0 -r 5 -p build"
                exit 1
            fi
        fi
        
        ((attempt++))
    done
}

# Function to clean up
clean_up() {
    print_warning "This will remove all containers and images. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up..."
        docker system prune -f
        docker image prune -f
        print_success "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Parse command line arguments
COMMAND="build"
ENABLE_PROXY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -p|--proxy)
            ENABLE_PROXY=true
            shift
            ;;
        -f|--file)
            DOCKERFILE="$2"
            shift 2
            ;;
        -r|--retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        build|build-prod|clean)
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

# Validate Dockerfile exists
if [ ! -f "$DOCKERFILE" ]; then
    print_error "Dockerfile not found: $DOCKERFILE"
    exit 1
fi

# Validate retry count
if ! [[ "$MAX_RETRIES" =~ ^[0-9]+$ ]] || [ "$MAX_RETRIES" -lt 1 ]; then
    print_error "Invalid retry count: $MAX_RETRIES. Must be a positive integer."
    exit 1
fi

# Execute command
case $COMMAND in
    build)
        build_image "$DOCKERFILE"
        ;;
    build-prod)
        if [ -f "Dockerfile.prod" ]; then
            build_image "Dockerfile.prod"
        else
            print_error "Production Dockerfile not found: Dockerfile.prod"
            exit 1
        fi
        ;;
    clean)
        clean_up
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac
