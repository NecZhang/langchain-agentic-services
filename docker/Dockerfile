# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set proxy environment variables (can be overridden at build time)
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}

# Configure apt to use proxy if available
RUN if [ -n "$HTTP_PROXY" ]; then \
        echo "Acquire::http::Proxy \"$HTTP_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf; \
        echo "Acquire::https::Proxy \"$HTTPS_PROXY\";" >> /etc/apt/apt.conf.d/proxy.conf; \
    fi

# Install system dependencies including tesseract for pytesseract
# Add retry logic and better error handling for proxy network issues
RUN apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing \
        curl \
        build-essential \
        tesseract-ocr \
        tesseract-ocr-chi-sim \
        tesseract-ocr-chi-tra \
        tesseract-ocr-eng \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        libgcc-s1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv for dependency management (same as local development)
RUN pip install --no-cache-dir uv

# Copy project configuration files
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv (same as local development)
# Use uv run to ensure we're using the virtual environment
RUN uv sync --frozen --no-dev && \
    uv run python -c "import fastapi, uvicorn, dotenv; print('✅ All required modules imported successfully')"

# Copy only the necessary application files
COPY simple_agent/ ./simple_agent/
COPY api.py ./
COPY start_server.py ./
COPY main.py ./

# Create necessary directories
RUN mkdir -p .data .tmp_uploads

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 9211

# Health check (using the actual API endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9211/docs || exit 1

# Run the service using uv run to ensure virtual environment is activated
CMD ["uv", "run", "python", "start_server.py"]
