# 🐳 Docker Container Setup for Agentic Service

This guide explains how to containerize and run your Agentic Service using Docker.

## 📋 Prerequisites

- **Docker**: Version 20.10+ with Docker Compose
- **Docker Compose**: Version 2.0+
- **vLLM Server**: Running and accessible

## 🚀 Quick Start

### **1. Build and Run (Development)**

```bash
# Build the Docker image
./docker-build.sh build

# Start the service
./docker-build.sh start

# Check status
./docker-build.sh status
```

### **2. Access the Service**

- **API**: http://localhost:9510
- **Documentation**: http://localhost:9510/docs
- **Health Check**: http://localhost:9510/docs

## 🔧 Docker Management Commands

### **Using the Management Script**

```bash
# Build image
./docker-build.sh build

# Start service
./docker-build.sh start

# Stop service
./docker-build.sh stop

# Restart service
./docker-build.sh restart

# View logs
./docker-build.sh logs

# Check status
./docker-build.sh status

# Clean up
./docker-build.sh clean

# Open shell in container
./docker-build.sh shell
```

### **Using Docker Compose Directly**

```bash
# Start service (works with both v1 and v2)
docker-compose up -d    # Docker Compose v1
docker compose up -d    # Docker Compose v2

# Stop service
docker-compose down     # Docker Compose v1
docker compose down     # Docker Compose v2

# View logs
docker-compose logs -f  # Docker Compose v1
docker compose logs -f  # Docker Compose v2

# Restart service
docker-compose restart  # Docker Compose v1
docker compose restart  # Docker Compose v2
```

**Note**: The management script automatically detects your Docker Compose version and uses the appropriate command.

## 🏗️ Dockerfile Options

### **Development Dockerfile**
- **File**: `Dockerfile`
- **Features**: 
  - Full development environment
  - Hot reload capability
  - Debug tools included
  - All required system dependencies (tesseract, OpenCV libraries)
  - **uv-based dependency management** (same as local development)
  - **Proxy support for apt-get and pip** during build
  - Consistent with local development environment

### **Production Dockerfile**
- **File**: `Dockerfile.prod`
- **Features**:
  - Multi-stage build
  - Security hardening
  - Non-root user
  - **uv-based dependency management** (same as local development)
  - **Proxy support for apt-get and pip** during build

### **Production Dockerfile**
- **File**: `Dockerfile.prod`
- **Features**:
  - Multi-stage build
  - Security hardening
  - Non-root user
  - Optimized layers
  - All required system dependencies
  - Proxy support for network issues

## 📁 Docker Compose Configurations

### **Development (`docker-compose.yml`)**
- Auto-reload enabled
- Development environment variables
- Resource limits: 2GB RAM, 1 CPU

### **Production (`docker-compose.prod.yml`)**
- Production-optimized settings
- Security hardening
- Resource limits: 4GB RAM, 2 CPU
- Nginx reverse proxy (optional)

## 🚀 **uv-based Dependency Management**

### **Consistent with Local Development**
The Docker images now use **uv** for dependency management, ensuring:
- **Identical dependency resolution** between local and container environments
- **Faster builds** with uv's optimized package installation
- **Lock file consistency** using `uv.lock` for reproducible builds
- **Same Python packages** as your local development environment

### **Build Commands**
```bash
# Standard build (uses docker-build.sh)
./docker-build.sh build

# Build with proxy support (recommended for network issues)
./docker-build-with-proxy.sh -p build

# Build production image with proxy
./docker-build-with-proxy.sh -p build-prod

# Build with custom tag
./docker-build-with-proxy.sh -t v1.0.0 -p build
```

## 🌐 **Network and Proxy Configuration**

### **Automatic Proxy Detection**
The build scripts automatically detect and use proxy settings:
```bash
# Set proxy environment variables
export HTTP_PROXY=http://your-proxy-server:port
export HTTPS_PROXY=http://your-proxy-server:port
export NO_PROXY=localhost,127.0.0.1,192.168.0.0/16

# Build with proxy support
./docker-build-with-proxy.sh -p build
```

### **Proxy Configuration File**
Use the included proxy configuration:
```bash
# Copy and customize proxy settings
cp proxy.env proxy.env.local
nano proxy.env.local

# Source the configuration
source proxy.env.local

# Build with proxy
./docker-build-with-proxy.sh -p build
```

### **Manual Build with Proxy**
```bash
docker build \
  --build-arg HTTP_PROXY="$HTTP_PROXY" \
  --build-arg HTTPS_PROXY="$HTTPS_PROXY" \
  --build-arg NO_PROXY="$NO_PROXY" \
  -f Dockerfile \
  -t agentic-service:latest ..
```

### **Common Network Issues and Solutions:**

- **Slow downloads**: Set appropriate proxy variables
- **Package installation failures**: Check proxy settings and firewall rules
- **Docker registry access**: Ensure Docker daemon can access external registries

## 🔍 Troubleshooting

### **Build Issues**

1. **Dependencies not found:**
   ```bash
   # Check if all system packages are available
   docker run --rm python:3.12-slim apt-get update && apt-get install -y tesseract-ocr
   ```

2. **Network timeouts:**
   ```bash
   # Set longer timeout for Docker build
   export DOCKER_BUILDKIT=1
   export BUILDKIT_PROGRESS=plain
   ```

3. **Memory issues:**
   ```bash
   # Increase Docker memory limit in Docker Desktop settings
   # Or use --memory flag
   docker build --memory=4g -t agentic-service:latest .
   ```

### **Runtime Issues**

1. **Service not starting:**
   ```bash
   # Check logs
   ./docker-build.sh logs
   
   # Check container status
   ./docker-build.sh status
   ```

2. **Port conflicts:**
   ```bash
   # Check if port 9510 is already in use
   netstat -tulpn | grep 9510
   
   # Change port in docker-compose.yml if needed
   ```

3. **Permission issues:**
   ```bash
   # Ensure proper file permissions
   chmod +x docker-build.sh
   chmod 644 docker-compose.yml
   ```

## 📊 Resource Requirements

### **Development Environment**
- **Memory**: 2GB minimum, 4GB recommended
- **CPU**: 1 core minimum, 2 cores recommended
- **Storage**: 5GB minimum for image and dependencies

### **Production Environment**
- **Memory**: 4GB minimum, 8GB recommended
- **CPU**: 2 cores minimum, 4 cores recommended
- **Storage**: 10GB minimum for image, data, and logs

## 🔒 Security Considerations

### **Development**
- CORS enabled for all origins
- Debug mode enabled
- Reload enabled for development

### **Production**
- CORS restricted to specific origins
- Debug mode disabled
- Non-root user execution
- Read-only filesystem where possible
- Security options enabled

## 📝 Environment Configuration

### **Required Environment Variables**
- `VLLM_ENDPOINT`: URL of your vLLM server
- `VLLM_MODEL`: Model name to use
- `API_HOST`: Host to bind to (default: 0.0.0.0)
- `API_PORT`: Port to bind to (default: 9510)

### **Optional Environment Variables**
- `API_KEY`: API key for authentication
- `DEFAULT_LANGUAGE`: Default language for responses
- `MAX_FILE_SIZE_MB`: Maximum file upload size
- `ALLOWED_ORIGINS`: CORS allowed origins

## 🚀 Advanced Usage

### **Custom Image Tags**
```bash
./docker-build.sh -t v1.0.0 build
```

### **Different Compose Files**
```bash
./docker-build.sh -f docker-compose.prod.yml start
```

### **Multi-architecture Builds**
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t agentic-service:latest .
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Python Docker Best Practices](https://docs.docker.com/language/python/)
- [Multi-stage Docker Builds](https://docs.docker.com/develop/dev-best-practices/dockerfile_best-practices/#use-multi-stage-builds)

## 🤝 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review Docker and container logs
3. Ensure all prerequisites are met
4. Check network connectivity and proxy settings
5. Verify resource availability (memory, CPU, storage)
