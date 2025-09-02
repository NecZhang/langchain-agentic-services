# 🗄️ PostgreSQL Deployment Guide for Agentic Service

This guide provides step-by-step instructions for deploying PostgreSQL as the primary data storage backend for your Agentic Service.

## 🎯 **What This Setup Provides**

### **Data Storage Capabilities:**
- ✅ **User Management**: Store user profiles and authentication data
- ✅ **Session Management**: Track user sessions and activity
- ✅ **Chat History**: Persistent conversation storage with full-text search
- ✅ **Document Metadata**: File information, processing status, and metadata
- ✅ **Document Chunks**: Text chunks for RAG processing
- ✅ **Processing Caches**: Store RAG results and processing outputs
- ✅ **Vector Embeddings**: Semantic search vectors for chunks
- ✅ **File Storage References**: Track where files are stored (local/S3)

### **Performance Features:**
- 🚀 **Indexed Queries**: Fast lookups on all major fields
- 🔍 **Full-Text Search**: PostgreSQL-powered search on chat content
- 📊 **JSONB Support**: Flexible metadata storage with query capabilities
- 🗂️ **Connection Pooling**: Efficient database connection management
- 💾 **Automatic Cleanup**: Expired cache and session cleanup

## 🚀 **Quick Start Deployment**

### **Prerequisites:**
- Docker and Docker Compose installed
- Python 3.12+ with uv package manager
- At least 2GB RAM available for PostgreSQL

### **Step 1: Deploy PostgreSQL**
```bash
# Run the deployment script
./docker/deploy_postgres.sh
```

The script will:
1. Check Docker availability
2. Create `.env` file from template
3. Start PostgreSQL container
4. Initialize database schema
5. Test database connection
6. Optionally migrate existing data

### **Step 2: Configure Environment**
Edit your `.env` file with your actual configuration:
```bash
# Database configuration
DATABASE_URL=postgresql://agentic_user:your_password@localhost:5432/agentic_service

# vLLM configuration
VLLM_ENDPOINT=http://your_vllm_server:8002
VLLM_MODEL=Qwen/Qwen3-32B-FP8

# Other settings...
```

### **Step 3: Test the Setup**
```bash
# Check service status
./docker/deploy_postgres.sh --status

# Test database connection
python3 -c "from simple_agent.database import check_db_connection; print(check_db_connection())"
```

## 🗄️ **Database Schema Overview**

### **Core Tables:**

#### **Users & Sessions**
```sql
users          -- User profiles and authentication
sessions       -- User session tracking
```

#### **Content Storage**
```sql
chat_history   -- Conversation messages with full-text search
documents      -- File metadata and processing status
document_chunks -- Text chunks for RAG processing
```

#### **Processing & Caching**
```sql
processing_caches -- RAG results and processing outputs
vector_embeddings -- Semantic search vectors
file_storage     -- File location tracking
```

### **Key Relationships:**
```
User (1) → (N) Sessions
Session (1) → (N) ChatHistory
Session (1) → (N) Documents
Document (1) → (N) DocumentChunks
DocumentChunk (1) → (N) VectorEmbeddings
```

## 🔧 **Configuration Options**

### **Environment Variables:**

#### **Database Configuration**
```bash
# PostgreSQL connection
DATABASE_URL=postgresql://user:pass@host:port/db
POSTGRES_PASSWORD=secure_password
POSTGRES_USER=agentic_user
POSTGRES_DB=agentic_service

# Connection pool settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

#### **Storage Backend Selection**
```bash
# Option 1: PostgreSQL only (current setup)
DATABASE_URL=postgresql://...

# Option 2: Hybrid with S3
STORAGE_BACKEND=s3
S3_ENDPOINT=localhost:9000
S3_ACCESS_KEY=your_key
S3_SECRET_KEY=your_secret

# Option 3: With Redis caching
CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379
```

## 📊 **Data Migration**

### **From File Storage to Database**

The migration script automatically handles:
- ✅ User and session creation
- ✅ Chat history import from JSONL files
- ✅ Document metadata extraction
- ✅ Processing cache preservation
- ✅ File storage reference creation

### **Running Migration:**
```bash
# Full migration
python3 migrate_to_database.py

# Dry run (see what would be migrated)
python3 migrate_to_database.py --dry-run

# Backup only
python3 migrate_to_database.py --backup-only
```

### **Migration Process:**
1. **Backup**: Creates `.data_backup/` directory
2. **Users/Sessions**: Creates database records
3. **Chat History**: Imports from `chat_history.jsonl` files
4. **Documents**: Extracts metadata from uploads
5. **Caches**: Preserves processing results
6. **Verification**: Ensures data integrity

## 🚀 **Production Deployment**

### **Security Considerations:**
```bash
# Change default passwords
POSTGRES_PASSWORD=your_very_secure_password
API_KEY=your_secure_api_key

# Restrict network access
# Edit docker-compose.yml to bind to specific IPs
```

### **Performance Tuning:**
```bash
# PostgreSQL configuration
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
POSTGRES_WORK_MEM=4MB
POSTGRES_MAINTENANCE_WORK_MEM=64MB
```

### **Backup Strategy:**
```bash
# Enable automated backups
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
```

## 🔍 **Monitoring & Maintenance**

### **Health Checks:**
```bash
# Check service status
./docker/deploy_postgres.sh --status

# View logs
docker logs -f agentic_postgres

# Database connection test
docker exec agentic_postgres pg_isready -U agentic_user -d agentic_service
```

### **Database Maintenance:**
```sql
-- Connect to database
docker exec -it agentic_postgres psql -U agentic_user -d agentic_service

-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes ORDER BY idx_scan DESC;
```

### **Cleanup Operations:**
```python
# Python cleanup script
from simple_agent.db_service import DatabaseService

with DatabaseService() as db:
    # Clean old sessions (older than 30 days)
    db.cleanup_old_sessions(days_old=30)
    
    # Clean expired caches
    db.cleanup_expired_caches()
```

## 🐛 **Troubleshooting**

### **Common Issues:**

#### **Connection Refused**
```bash
# Check if PostgreSQL is running
docker ps | grep agentic_postgres

# Check container logs
docker logs agentic_postgres

# Verify port binding
docker port agentic_postgres
```

#### **Authentication Failed**
```bash
# Check password in .env file
grep POSTGRES_PASSWORD .env

# Reset password if needed
docker exec -it agentic_postgres psql -U postgres -c "ALTER USER agentic_user PASSWORD 'new_password';"
```

#### **Migration Errors**
```bash
# Check data directory permissions
ls -la .data/

# Run migration with verbose output
python3 migrate_to_database.py --dry-run

# Check database connection first
python3 -c "from simple_agent.database import check_db_connection; print(check_db_connection())"
```

### **Debug Mode:**
```bash
# Enable database query logging
DB_ECHO=true

# Enable debug streaming
DEBUG_STREAMING=true

# Check environment variables
cat .env | grep -v '^#'
```

## 📈 **Scaling Considerations**

### **Vertical Scaling:**
- Increase PostgreSQL container memory/CPU
- Optimize connection pool settings
- Tune PostgreSQL configuration parameters

### **Horizontal Scaling:**
- Use read replicas for query distribution
- Implement connection pooling (PgBouncer)
- Consider database sharding for large datasets

### **Storage Scaling:**
- Monitor disk usage and growth
- Implement automated cleanup policies
- Consider S3-compatible storage for large files

## 🔄 **Upgrade Path**

### **Version Updates:**
```bash
# Update PostgreSQL version
docker-compose pull postgres
docker-compose up -d postgres

# Run database migrations if needed
docker exec agentic_postgres psql -U agentic_user -d agentic_service -f upgrade_script.sql
```

### **Schema Evolution:**
- Use Alembic for database migrations
- Test schema changes in staging environment
- Plan backward compatibility for API changes

## 📚 **Additional Resources**

### **Documentation:**
- [STORAGE_CONFIG.md](STORAGE_CONFIG.md) - Storage architecture overview
- [README.md](README.md) - Application usage guide
- [API.md](api.py) - API endpoint documentation

### **External Resources:**
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

### **Support:**
- Check container logs for detailed error messages
- Use `--dry-run` flags to test operations safely
- Verify environment configuration matches requirements

---

## 🎉 **Next Steps**

1. **Deploy PostgreSQL**: Run `./docker/deploy_postgres.sh`
2. **Configure Environment**: Edit `.env` file with your settings
3. **Test Connection**: Verify database connectivity
4. **Migrate Data**: Run migration script if needed
5. **Start Application**: Restart your service to use the database
6. **Monitor**: Use provided tools to monitor performance

Your Agentic Service is now ready for production-scale data storage with PostgreSQL! 🚀

