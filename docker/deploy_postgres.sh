#!/bin/bash

# PostgreSQL Deployment Script for Agentic Service
# This script sets up PostgreSQL and migrates data from file storage

set -e

echo "🚀 Deploying PostgreSQL for Agentic Service..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    echo -e "${RED}❌ Error: This script must be run from the project root directory${NC}"
    exit 1
fi

echo -e "${BLUE}📁 Project directory: $PROJECT_DIR${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_status "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available. Please install Docker Compose and try again."
        exit 1
    fi
    print_status "Docker Compose is available"
}

# Create environment file
setup_environment() {
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f "$ENV_EXAMPLE" ]]; then
            print_info "Creating .env file from env.example..."
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            print_warning "Please edit .env file with your actual configuration before continuing"
            print_info "You can now edit .env file and run this script again"
            exit 0
        else
            print_error "env.example file not found. Cannot create .env file."
            exit 1
        fi
    fi
    
    # Load environment variables
    if [[ -f "$ENV_FILE" ]]; then
        print_info "Loading environment variables from .env file..."
        export $(grep -v '^#' "$ENV_FILE" | xargs)
    fi
}

# Start PostgreSQL
start_postgres() {
    print_info "Starting PostgreSQL with Docker Compose..."
    
    cd "$PROJECT_DIR"
    
    # Set PostgreSQL password if not set
    if [[ -z "$POSTGRES_PASSWORD" ]]; then
        export POSTGRES_PASSWORD="secure_password_change_me"
        print_warning "Using default PostgreSQL password. Please change it in production."
    fi
    
    # Start services
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d postgres
    else
        docker compose up -d postgres
    fi
    
    # Wait for PostgreSQL to be ready
    print_info "Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker exec agentic_postgres pg_isready -U agentic_user -d agentic_service > /dev/null 2>&1; then
            print_status "PostgreSQL is ready!"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            print_error "PostgreSQL failed to start within expected time"
            exit 1
        fi
        
        print_info "Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
}

# Initialize database
init_database() {
    print_info "Initializing database..."
    
    cd "$PROJECT_DIR"
    
    # Check if database tables exist
    if docker exec agentic_postgres psql -U agentic_user -d agentic_service -c "\dt" > /dev/null 2>&1; then
        print_warning "Database tables already exist. Skipping initialization."
        return
    fi
    
    # Run initialization script
    print_info "Running database initialization script..."
    docker exec agentic_postgres psql -U agentic_user -d agentic_service -f /docker-entrypoint-initdb.d/01-init.sql
    
    print_status "Database initialized successfully"
}

# Test database connection
test_database() {
    print_info "Testing database connection..."
    
    cd "$PROJECT_DIR"
    
    # Test with Python
    if python3 -c "
import sys
sys.path.insert(0, '.')
from simple_agent.database import check_db_connection
if check_db_connection():
    print('Database connection successful')
    exit(0)
else:
    print('Database connection failed')
    exit(1)
" 2>/dev/null; then
        print_status "Database connection test successful"
    else
        print_error "Database connection test failed"
        print_info "Please check your DATABASE_URL configuration in .env file"
        exit 1
    fi
}

# Run migration
run_migration() {
    print_info "Running data migration from file storage to database..."
    
    cd "$PROJECT_DIR"
    
    # Check if migration script exists
    if [[ ! -f "migrate_to_database.py" ]]; then
        print_error "Migration script not found"
        exit 1
    fi
    
    # Run migration
    print_info "Starting migration (this may take a while)..."
    if python3 migrate_to_database.py; then
        print_status "Migration completed successfully"
    else
        print_error "Migration failed"
        print_info "You can run the migration manually with: python3 migrate_to_database.py"
        exit 1
    fi
}

# Show status
show_status() {
    print_info "Checking service status..."
    
    cd "$PROJECT_DIR"
    
    # Check PostgreSQL container
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "agentic_postgres"; then
        print_status "PostgreSQL container is running"
    else
        print_error "PostgreSQL container is not running"
    fi
    
    # Check database connection
    if docker exec agentic_postgres pg_isready -U agentic_user -d agentic_service > /dev/null 2>&1; then
        print_status "PostgreSQL database is accessible"
    else
        print_error "PostgreSQL database is not accessible"
    fi
    
    # Show container logs
    print_info "Recent PostgreSQL logs:"
    docker logs --tail 10 agentic_postgres
}

# Main deployment function
main() {
    echo -e "${BLUE}🚀 Starting PostgreSQL deployment...${NC}"
    
    # Pre-flight checks
    check_docker
    check_docker_compose
    setup_environment
    
    # Deploy PostgreSQL
    start_postgres
    init_database
    test_database
    
    # Ask about migration
    echo
    read -p "Do you want to migrate existing data from file storage to the database? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_migration
    else
        print_info "Skipping data migration. You can run it later with: python3 migrate_to_database.py"
    fi
    
    # Show final status
    echo
    show_status
    
    echo
    print_status "PostgreSQL deployment completed!"
    echo
    echo -e "${BLUE}📋 Next steps:${NC}"
    echo "1. Update your .env file with the correct DATABASE_URL"
    echo "2. Restart your application to use the database"
    echo "3. Test the connection with: python3 -c 'from simple_agent.database import check_db_connection; print(check_db_connection())'"
    echo
    echo -e "${BLUE}🔧 Useful commands:${NC}"
    echo "  View logs: docker logs -f agentic_postgres"
    echo "  Stop service: docker-compose down"
    echo "  Start service: docker-compose up -d"
    echo "  Access database: docker exec -it agentic_postgres psql -U agentic_user -d agentic_service"
    echo
    echo -e "${BLUE}📚 Documentation:${NC}"
    echo "  See STORAGE_CONFIG.md for detailed configuration options"
    echo "  See README.md for application usage"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--help|--status|--migrate]"
        echo
        echo "Options:"
        echo "  --help     Show this help message"
        echo "  --status   Show service status"
        echo "  --migrate  Run data migration only"
        echo
        echo "Examples:"
        echo "  $0                    # Full deployment"
        echo "  $0 --status           # Show status"
        echo "  $0 --migrate          # Run migration only"
        exit 0
        ;;
    --status)
        show_status
        exit 0
        ;;
    --migrate)
        setup_environment
        run_migration
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

