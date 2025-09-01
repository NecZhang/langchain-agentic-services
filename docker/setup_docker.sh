#!/bin/bash

# Docker setup script for Agentic Service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check Docker installation
check_docker() {
    print_status "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check for Docker Compose (both v1 and v2)
    DOCKER_COMPOSE_CMD=""
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
        print_status "Found Docker Compose v1: docker-compose"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
        print_status "Found Docker Compose v2: docker compose"
    else
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed!"
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker daemon is running!"
    
    # Export the command for use in other functions
    export DOCKER_COMPOSE_CMD
}

# Function to setup environment file
setup_env() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env file from .env.example"
            print_warning "Please edit .env file with your configuration before starting the service."
        else
            print_warning ".env.example not found. Creating basic .env file..."
            cat > .env << EOF
# Server configuration
API_HOST=0.0.0.0
API_PORT=9510

# vLLM connection (update these for your setup)
VLLM_ENDPOINT=http://192.168.6.10:8002
VLLM_MODEL=Qwen/Qwen3-32B-FP8
AGENTIC_REQUEST_TIMEOUT=30

# Language configuration
DEFAULT_LANGUAGE=Chinese
SUPPORTED_LANGUAGES=Chinese,English
AUTO_DETECT_LANGUAGE=true

# Streaming configuration
STREAM_CHAR_BY_CHAR=true
FORCE_SMALL_CHUNKS=true
NETWORK_STREAMING_OPTIMIZED=true
DEBUG_STREAMING=false

# Development mode (disable in production)
ENABLE_RELOAD=false

# Storage configuration
AGENTIC_DATA_DIR=/app/data
AGENTIC_TEMP_DIR=/app/tmp_uploads

# Security (optional)
# API_KEY=your_secret_key
MAX_FILE_SIZE_MB=50

# CORS
ALLOWED_ORIGINS=*
EOF
            print_success "Created basic .env file"
            print_warning "Please edit .env file with your configuration before starting the service."
        fi
    else
        print_status ".env file already exists"
    fi
}

# Function to setup proxy configuration
setup_proxy() {
    print_status "Setting up proxy configuration..."
    
    echo "Do you need to configure proxy settings for network connectivity? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Enter HTTP proxy (e.g., http://proxy.example.com:8080):"
        read -r http_proxy
        
        echo "Enter HTTPS proxy (e.g., http://proxy.example.com:8080):"
        read -r https_proxy
        
        echo "Enter no-proxy list (e.g., localhost,127.0.0.1,192.168.0.0/16):"
        read -r no_proxy
        
        # Create proxy configuration file
        cat > .proxy.env << EOF
# Proxy configuration for Docker builds
export HTTP_PROXY="$http_proxy"
export HTTPS_PROXY="$https_proxy"
export NO_PROXY="$no_proxy"
EOF
        
        print_success "Proxy configuration saved to .proxy.env"
        print_status "To use proxy settings, run: source .proxy.env"
        print_status "Or set them manually before building:"
        echo "  export HTTP_PROXY=$http_proxy"
        echo "  export HTTPS_PROXY=$https_proxy"
        echo "  export NO_PROXY=$no_proxy"
    else
        print_status "No proxy configuration needed"
    fi
}

# Function to setup directories
setup_directories() {
    print_status "Setting up required directories..."
    
    mkdir -p .data .tmp_uploads
    print_success "Created .data and .tmp_uploads directories"
}

# Function to test network connectivity
test_network() {
    print_status "Testing network connectivity..."
    
    # Test Docker Hub access
    if docker pull hello-world:latest &> /dev/null; then
        print_success "Docker Hub access: OK"
        docker rmi hello-world:latest &> /dev/null
    else
        print_warning "Docker Hub access: Failed"
        print_warning "This may indicate network connectivity issues"
        print_warning "Consider setting up proxy configuration"
    fi
    
    # Test Python package index
    if curl -s --connect-timeout 10 https://pypi.org/ &> /dev/null; then
        print_success "PyPI access: OK"
    else
        print_warning "PyPI access: Failed"
        print_warning "This may indicate network connectivity issues"
        print_warning "Consider setting up proxy configuration"
    fi
}

# Function to show next steps
show_next_steps() {
    print_success "Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your configuration"
    echo "2. Build the Docker image:"
    echo "   cd docker && ./docker-build.sh build"
    echo "3. Start the service:"
    echo "   ./docker-build.sh start"
    echo "4. Access the service at: http://localhost:9510"
    echo "5. View API documentation at: http://localhost:9510/docs"
    echo ""
    echo "If you encounter network issues during build:"
    echo "1. Set proxy variables: source .proxy.env (if created)"
    echo "2. Or set manually: export HTTP_PROXY=http://your-proxy:port"
    echo "3. Then run: ./docker-build.sh build"
}

# Main execution
main() {
    echo "🐳 Agentic Service Docker Setup"
    echo "================================"
    echo ""
    
    check_docker
    setup_env
    setup_proxy
    setup_directories
    test_network
    show_next_steps
}

# Run main function
main "$@"
