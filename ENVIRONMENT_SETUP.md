# Environment Configuration Guide

This document explains how to configure the environment for the LangChain Agentic Services project.

## 📁 Environment File Structure

The project now uses a clean, organized environment configuration system:

```
├── .env                    # Active environment configuration (DO NOT COMMIT)
├── .env.example           # Comprehensive template with all options
├── .env.old               # Backup of previous configuration
├── switch_env.sh          # Script to switch between configurations
└── ENVIRONMENT_SETUP.md   # This documentation file
```

## 🚀 Quick Start

### 1. Initial Setup
```bash
# Copy the example configuration
cp .env.example .env

# Edit with your actual values
nano .env
```

### 2. Using the Environment Switcher
```bash
# Switch to development mode (file-based storage)
./switch_env.sh -d

# Switch to production mode (database storage)
./switch_env.sh -p

# Switch to S3 storage
./switch_env.sh -s

# Reset to example configuration
./switch_env.sh -r

# Create backup of current .env
./switch_env.sh -b
```

## ⚙️ Configuration Sections

### vLLM Configuration
```bash
VLLM_ENDPOINT=http://192.168.6.10:8002
VLLM_MODEL=Qwen/Qwen3-32B-FP8
```

### API Configuration
```bash
API_HOST=0.0.0.0
API_PORT=9510
API_KEY=your_secure_api_key_here
ALLOWED_ORIGINS=*
MAX_FILE_SIZE_MB=50
```

### Language Configuration
```bash
DEFAULT_LANGUAGE=Chinese
SUPPORTED_LANGUAGES=Chinese,English
AUTO_DETECT_LANGUAGE=true
```

### Storage Configuration

#### Option 1: File-based Storage (Development)
```bash
STORAGE_BACKEND=file
AGENTIC_DATA_DIR=.data
AGENTIC_TEMP_DIR=.tmp_uploads
```

#### Option 2: PostgreSQL Database (Production)
```bash
STORAGE_BACKEND=database
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

#### Option 3: S3-Compatible Storage (Enterprise)
```bash
STORAGE_BACKEND=s3
S3_ENDPOINT=localhost:9000
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET=agentic-files
S3_REGION=us-east-1
S3_SECURE=false
```

### Database Configuration
```bash
DB_ECHO=false
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

### Streaming Configuration
```bash
STREAM_CHAR_BY_CHAR=true
FORCE_SMALL_CHUNKS=true
NETWORK_STREAMING_OPTIMIZED=true
DEBUG_STREAMING=false
AGENTIC_REQUEST_TIMEOUT=30
```

### Security Configuration
```bash
SECRET_KEY=your_secret_key_here_change_this_in_production
ENCRYPTION_KEY=your_encryption_key_here_change_this_in_production
```

### Network Proxy Configuration
```bash
# Uncomment and configure if behind corporate firewall
# HTTP_PROXY=http://proxy.company.com:8080
# HTTPS_PROXY=http://proxy.company.com:8080
# NO_PROXY=127.0.0.1,localhost,*.local
```

## 🔄 Switching Between Configurations

### Development Mode
- File-based storage for quick setup
- Local data directories (`.data`, `.tmp_uploads`)
- No database required
- Perfect for development and testing

### Production Mode
- PostgreSQL database storage
- Production-grade data persistence
- Scalable and reliable
- Requires database setup

### S3 Storage Mode
- Cloud-native storage
- Scalable and cost-effective
- Requires S3-compatible service (MinIO, AWS S3, etc.)

## 📋 Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VLLM_ENDPOINT` | vLLM server endpoint | `http://192.168.6.10:8002` | Yes |
| `VLLM_MODEL` | Model name to use | `Qwen/Qwen3-32B-FP8` | Yes |
| `API_HOST` | API server host | `0.0.0.0` | Yes |
| `API_PORT` | API server port | `9510` | Yes |
| `STORAGE_BACKEND` | Storage backend type | `file` | Yes |
| `AGENTIC_DATA_DIR` | Data directory path | `.data` | If file storage |
| `AGENTIC_TEMP_DIR` | Temp directory path | `.tmp_uploads` | If file storage |
| `DATABASE_URL` | Database connection string | - | If database storage |
| `S3_ENDPOINT` | S3 endpoint URL | - | If S3 storage |
| `S3_ACCESS_KEY` | S3 access key | - | If S3 storage |
| `S3_SECRET_KEY` | S3 secret key | - | If S3 storage |
| `S3_BUCKET` | S3 bucket name | - | If S3 storage |

## 🛠️ Troubleshooting

### Common Issues

1. **Configuration not loaded**
   - Ensure `.env` file exists in project root
   - Check file permissions
   - Verify variable names match exactly

2. **Storage backend errors**
   - Verify `STORAGE_BACKEND` is set correctly
   - Check directory permissions for file storage
   - Verify database connection for database storage
   - Check S3 credentials for S3 storage

3. **Proxy issues**
   - Uncomment proxy variables in `.env`
   - Verify proxy server is accessible
   - Check `NO_PROXY` settings

### Validation Commands
```bash
# Check if .env is loaded
echo $VLLM_ENDPOINT

# Validate configuration
python -c "from dotenv import load_dotenv; load_dotenv(); print('Config loaded')"

# Test database connection (if using database)
python -c "from langchain_agent.database import test_connection; test_connection()"
```

## 🔒 Security Best Practices

1. **Never commit `.env` files** - They're already in `.gitignore`
2. **Use strong secrets** - Generate random keys for production
3. **Limit file permissions** - Set appropriate file permissions
4. **Rotate credentials** - Regularly update API keys and passwords
5. **Use environment-specific configs** - Different settings for dev/staging/prod

## 📚 Additional Resources

- [Docker Setup Guide](DOCKER_SETUP_SUMMARY.md)
- [Storage Configuration](STORAGE_CONFIG.md)
- [PostgreSQL Deployment](POSTGRES_DEPLOYMENT.md)
- [GitHub Setup](GITHUB_SETUP.md)

## 🤝 Contributing

When adding new environment variables:

1. Add them to `env.example` with clear documentation
2. Update this document
3. Provide sensible defaults
4. Include validation rules if applicable
5. Test with the environment switcher script
