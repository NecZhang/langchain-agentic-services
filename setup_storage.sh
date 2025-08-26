#!/bin/bash

# Storage Setup Script for Enterprise Agentic Service
# This script sets up external storage directories for production use

set -e

echo "🚀 Setting up external storage for Enterprise Agentic Service..."

# Configuration
DATA_DIR="${AGENTIC_DATA_DIR:-/var/lib/agentic-service}"
TEMP_DIR="${AGENTIC_TEMP_DIR:-/tmp/agentic-uploads}"
CURRENT_USER=$(whoami)

echo "📁 Data directory: $DATA_DIR"
echo "📁 Temp directory: $TEMP_DIR"
echo "👤 Current user: $CURRENT_USER"

# Check if running as root (needed for /var/lib)
if [[ "$DATA_DIR" == /var/lib* ]] && [[ "$EUID" -ne 0 ]]; then
    echo "⚠️  Warning: Creating /var/lib directories requires sudo privileges"
    echo "   The script will attempt to create directories with sudo"
fi

# Create data directory
echo "📂 Creating data directory: $DATA_DIR"
if [[ "$DATA_DIR" == /var/lib* ]]; then
    sudo mkdir -p "$DATA_DIR"
    sudo chown "$CURRENT_USER:$CURRENT_USER" "$DATA_DIR"
    sudo chmod 750 "$DATA_DIR"
else
    mkdir -p "$DATA_DIR"
    chmod 750 "$DATA_DIR"
fi

# Create temp directory
echo "📂 Creating temp directory: $TEMP_DIR"
if [[ "$TEMP_DIR" == /tmp* ]]; then
    sudo mkdir -p "$TEMP_DIR"
    sudo chown "$CURRENT_USER:$CURRENT_USER" "$TEMP_DIR"
    sudo chmod 750 "$TEMP_DIR"
else
    mkdir -p "$TEMP_DIR"
    chmod 750 "$TEMP_DIR"
fi

# Create subdirectories
echo "📂 Creating subdirectories..."
mkdir -p "$DATA_DIR/users"
mkdir -p "$DATA_DIR/logs"
mkdir -p "$TEMP_DIR/sessions"

# Set permissions
echo "🔒 Setting permissions..."
chmod 750 "$DATA_DIR/users"
chmod 750 "$DATA_DIR/logs"
chmod 750 "$TEMP_DIR/sessions"

# Create .env file if it doesn't exist
if [[ ! -f .env ]]; then
    echo "📝 Creating .env file from .env.example..."
    if [[ -f .env.example ]]; then
        cp .env.example .env
        echo "✅ .env file created from .env.example"
        echo "⚠️  Please edit .env file with your actual configuration"
    else
        echo "⚠️  .env.example not found, creating basic .env file..."
        cat > .env << EOF
# Enterprise Agentic Service Configuration
VLLM_ENDPOINT=http://192.168.6.10:8002
VLLM_MODEL=Qwen/Qwen3-32B-FP8
API_HOST=0.0.0.0
API_PORT=9510
DEFAULT_LANGUAGE=Chinese
AUTO_DETECT_LANGUAGE=true
AGENTIC_DATA_DIR=$DATA_DIR
AGENTIC_TEMP_DIR=$TEMP_DIR
EOF
        echo "✅ Basic .env file created"
    fi
else
    echo "✅ .env file already exists"
fi

# Update .env with storage paths
echo "🔧 Updating .env with storage paths..."
if grep -q "AGENTIC_DATA_DIR" .env; then
    sed -i "s|AGENTIC_DATA_DIR=.*|AGENTIC_DATA_DIR=$DATA_DIR|" .env
else
    echo "AGENTIC_DATA_DIR=$DATA_DIR" >> .env
fi

if grep -q "AGENTIC_TEMP_DIR" .env; then
    sed -i "s|AGENTIC_TEMP_DIR=.*|AGENTIC_TEMP_DIR=$TEMP_DIR|" .env
else
    echo "AGENTIC_TEMP_DIR=$TEMP_DIR" >> .env
fi

# Display final configuration
echo ""
echo "🎉 Storage setup completed successfully!"
echo ""
echo "📊 Configuration Summary:"
echo "   Data Directory: $DATA_DIR"
echo "   Temp Directory: $TEMP_DIR"
echo "   Permissions: 750 (owner: rwx, group: rx, others: none)"
echo ""
echo "📝 Next steps:"
echo "   1. Edit .env file with your vLLM server settings"
echo "   2. Start the service: python start_server.py"
echo "   3. Test with: curl http://localhost:9510/health"
echo ""
echo "🔒 Security Note:"
echo "   - Data directories have restrictive permissions (750)"
echo "   - Only owner and group can access"
echo "   - Consider setting up regular backups"
echo ""
echo "📚 For more information, see STORAGE_CONFIG.md"
