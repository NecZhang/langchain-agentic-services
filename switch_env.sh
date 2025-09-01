#!/bin/bash

# Environment Configuration Switcher
# This script helps you switch between different environment configurations

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_EXAMPLE="$PROJECT_DIR/env.example"
ENV_FILE="$PROJECT_DIR/.env"

print_status() {
    echo "✅ $1"
}

print_warning() {
    echo "⚠️  $1"
}

print_error() {
    echo "❌ $1"
}

print_info() {
    echo "ℹ️  $1"
}

show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  -d, --development    Switch to development configuration (file-based storage)"
    echo "  -p, --production     Switch to production configuration (database storage)"
    echo "  -s, --s3            Switch to S3 storage configuration"
    echo "  -r, --reset         Reset to example configuration"
    echo "  -b, --backup        Create backup of current .env"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -d               # Switch to development mode"
    echo "  $0 -p               # Switch to production mode"
    echo "  $0 -r               # Reset to example configuration"
}

backup_env() {
    if [[ -f "$ENV_FILE" ]]; then
        local backup_file="$PROJECT_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$ENV_FILE" "$backup_file"
        print_status "Current .env backed up to $backup_file"
    else
        print_warning "No .env file to backup"
    fi
}

switch_to_development() {
    print_info "Switching to development configuration..."
    
    # Create backup
    backup_env
    
    # Copy example and customize for development
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    
    # Update storage backend to file-based
    sed -i 's/^# STORAGE_BACKEND=file/STORAGE_BACKEND=file/' "$ENV_FILE"
    sed -i 's/^STORAGE_BACKEND=database/# STORAGE_BACKEND=database/' "$ENV_FILE"
    sed -i 's/^STORAGE_BACKEND=s3/# STORAGE_BACKEND=s3/' "$ENV_FILE"
    
    # Uncomment development paths
    sed -i 's/^# AGENTIC_DATA_DIR=.data/AGENTIC_DATA_DIR=.data/' "$ENV_FILE"
    sed -i 's/^# AGENTIC_TEMP_DIR=.tmp_uploads/AGENTIC_TEMP_DIR=.tmp_uploads/' "$ENV_FILE"
    
    # Comment out production paths
    sed -i 's/^AGENTIC_DATA_DIR=\/var\/lib\/agentic-service/# AGENTIC_DATA_DIR=\/var\/lib\/agentic-service/' "$ENV_FILE"
    sed -i 's/^AGENTIC_TEMP_DIR=\/tmp\/agentic-uploads/# AGENTIC_TEMP_DIR=\/tmp\/agentic-uploads/' "$ENV_FILE"
    
    print_status "Switched to development configuration (file-based storage)"
    print_warning "Please review and customize $ENV_FILE if needed"
}

switch_to_production() {
    print_info "Switching to production configuration..."
    
    # Create backup
    backup_env
    
    # Copy example and customize for production
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    
    # Update storage backend to database
    sed -i 's/^# STORAGE_BACKEND=database/STORAGE_BACKEND=database/' "$ENV_FILE"
    sed -i 's/^STORAGE_BACKEND=file/# STORAGE_BACKEND=file/' "$ENV_FILE"
    sed -i 's/^STORAGE_BACKEND=s3/# STORAGE_BACKEND=s3/' "$ENV_FILE"
    
    # Uncomment production paths
    sed -i 's/^# AGENTIC_DATA_DIR=\/var\/lib\/agentic-service/AGENTIC_DATA_DIR=\/var\/lib\/agentic-service/' "$ENV_FILE"
    sed -i 's/^# AGENTIC_TEMP_DIR=\/tmp\/agentic-uploads/AGENTIC_TEMP_DIR=\/tmp\/agentic-uploads/' "$ENV_FILE"
    
    # Comment out development paths
    sed -i 's/^AGENTIC_DATA_DIR=.data/# AGENTIC_DATA_DIR=.data/' "$ENV_FILE"
    sed -i 's/^AGENTIC_TEMP_DIR=.tmp_uploads/# AGENTIC_TEMP_DIR=.tmp_uploads/' "$ENV_FILE"
    
    print_status "Switched to production configuration (database storage)"
    print_warning "Please review and customize $ENV_FILE if needed"
    print_warning "Make sure to set DATABASE_URL and other production values"
}

switch_to_s3() {
    print_info "Switching to S3 storage configuration..."
    
    # Create backup
    backup_env
    
    # Copy example and customize for S3
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    
    # Update storage backend to S3
    sed -i 's/^# STORAGE_BACKEND=s3/STORAGE_BACKEND=s3/' "$ENV_FILE"
    sed -i 's/^STORAGE_BACKEND=file/# STORAGE_BACKEND=file/' "$ENV_FILE"
    sed -i 's/^STORAGE_BACKEND=database/# STORAGE_BACKEND=database/' "$ENV_FILE"
    
    # Uncomment S3 configuration
    sed -i 's/^# S3_ENDPOINT=/S3_ENDPOINT=/' "$ENV_FILE"
    sed -i 's/^# S3_ACCESS_KEY=/S3_ACCESS_KEY=/' "$ENV_FILE"
    sed -i 's/^# S3_SECRET_KEY=/S3_SECRET_KEY=/' "$ENV_FILE"
    sed -i 's/^# S3_BUCKET=/S3_BUCKET=/' "$ENV_FILE"
    sed -i 's/^# S3_REGION=/S3_REGION=/' "$ENV_FILE"
    sed -i 's/^# S3_SECURE=/S3_SECURE=/' "$ENV_FILE"
    
    print_status "Switched to S3 storage configuration"
    print_warning "Please review and customize S3 settings in $ENV_FILE"
}

reset_to_example() {
    print_info "Resetting to example configuration..."
    
    # Create backup
    backup_env
    
    # Copy example
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    
    print_status "Reset to example configuration"
    print_warning "Please customize $ENV_FILE with your actual values"
}

# Main script logic
if [[ $# -eq 0 ]]; then
    show_usage
    exit 1
fi

case "$1" in
    -d|--development)
        switch_to_development
        ;;
    -p|--production)
        switch_to_production
        ;;
    -s|--s3)
        switch_to_s3
        ;;
    -r|--reset)
        reset_to_example
        ;;
    -b|--backup)
        backup_env
        ;;
    -h|--help)
        show_usage
        ;;
    *)
        print_error "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac
