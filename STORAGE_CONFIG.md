# 🗄️ Storage Configuration Guide

## 🚨 **Current Storage Issues (Fixed)**

### **❌ Problems with Project-Folder Storage:**
- **Project Pollution**: `.data/` and `.tmp_uploads/` in project root
- **Version Control Risk**: Risk of accidentally committing user data
- **Scaling Issues**: Local filesystem doesn't scale across multiple servers
- **Backup Complexity**: User data mixed with application code
- **Deployment Issues**: Data lost when redeploying containers
- **Security Concerns**: File permissions and access control
- **Maintenance Nightmare**: Hard to clean up old sessions

## 🎯 **Recommended Storage Solutions**

### **Option 1: External Data Directory (Quick Improvement)**
```bash
# Set in environment or .env file
export AGENTIC_DATA_DIR="/var/lib/agentic-service"
export AGENTIC_TEMP_DIR="/tmp/agentic-uploads"

# Or in .env file
AGENTIC_DATA_DIR=/var/lib/agentic-service
AGENTIC_TEMP_DIR=/tmp/agentic-uploads
```

**Benefits:**
- ✅ **Separation**: Data separate from application code
- ✅ **Permissions**: Proper file permissions for production
- ✅ **Backup**: Easy to backup data independently
- ✅ **Deployment**: Data persists across deployments
- ✅ **Security**: Restricted access to data directories

**Setup:**
```bash
# Create production data directories
sudo mkdir -p /var/lib/agentic-service
sudo mkdir -p /tmp/agentic-uploads

# Set ownership to your application user
sudo chown -R $USER:$USER /var/lib/agentic-service
sudo chown -R $USER:$USER /tmp/agentic-uploads

# Set restrictive permissions
sudo chmod 750 /var/lib/agentic-service
sudo chmod 750 /tmp/agentic-uploads
```

### **Option 2: Database + Object Storage (Production Ready)**
```bash
# PostgreSQL for metadata
DATABASE_URL=postgresql://user:pass@localhost/agentic_db

# MinIO/S3 for file storage
STORAGE_BACKEND=s3
S3_ENDPOINT=your-s3-endpoint
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET=agentic-files

# Redis for caching
CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379
```

**Benefits:**
- ✅ **Scalability**: Handle thousands of concurrent users
- ✅ **Reliability**: ACID compliance for metadata
- ✅ **Performance**: Fast caching with Redis
- ✅ **Backup**: Automated backup and recovery
- ✅ **Security**: Database-level access control

### **Option 3: Hybrid Approach (Enterprise Grade)**
```bash
# Metadata in PostgreSQL
METADATA_DB=postgresql://user:pass@localhost/agentic_db

# Files in S3-compatible storage
FILE_STORAGE=s3://your-bucket
FILE_STORAGE_ENDPOINT=your-s3-endpoint

# RAG indices in Redis
CACHE_STORAGE=redis://localhost:6379

# Session data in PostgreSQL
SESSION_STORAGE=postgresql://user:pass@localhost/agentic_db
```

## 🛠 **Implementation Steps**

### **Step 1: Quick Fix (External Directories)**
```bash
# 1. Set environment variables
export AGENTIC_DATA_DIR="/var/lib/agentic-service"
export AGENTIC_TEMP_DIR="/tmp/agentic-uploads"

# 2. Create directories
sudo mkdir -p /var/lib/agentic-service
sudo mkdir -p /tmp/agentic-uploads

# 3. Set permissions
sudo chown -R $USER:$USER /var/lib/agentic-service
sudo chown -R $USER:$USER /tmp/agentic-uploads
sudo chmod 750 /var/lib/agentic-service
sudo chmod 750 /tmp/agentic-uploads

# 4. Restart your service
python start_server.py
```

### **Step 2: Database Migration (When Ready)**
```sql
-- Create database
CREATE DATABASE agentic_service;

-- Create tables
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, session_id)
);

CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE document_cache (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    doc_hash VARCHAR(255) NOT NULL,
    mode VARCHAR(100) NOT NULL,
    chunks JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, doc_hash, mode)
);
```

## 📊 **Storage Comparison**

| Aspect | Project Folder | External Dir | Database + S3 | Hybrid |
|--------|----------------|--------------|---------------|---------|
| **Setup Complexity** | 🟢 Easy | 🟡 Medium | 🔴 Complex | 🔴 Complex |
| **Scalability** | 🔴 Poor | 🟡 Limited | 🟢 Good | 🟢 Excellent |
| **Security** | 🔴 Poor | 🟡 Medium | 🟢 Good | 🟢 Excellent |
| **Backup** | 🔴 Hard | 🟡 Medium | 🟢 Easy | 🟢 Easy |
| **Deployment** | 🔴 Problematic | 🟡 Good | 🟢 Excellent | 🟢 Excellent |
| **Cost** | 🟢 Free | 🟢 Free | 🟡 Medium | 🟡 Medium |
| **Maintenance** | 🔴 Hard | 🟡 Medium | 🟢 Easy | 🟢 Easy |

## 🔧 **Configuration Examples**

### **Development (.env)**
```bash
# Use project folders for development
AGENTIC_DATA_DIR=.data
AGENTIC_TEMP_DIR=.tmp_uploads
```

### **Staging (.env)**
```bash
# Use external directories for staging
AGENTIC_DATA_DIR=/var/lib/agentic-service-staging
AGENTIC_TEMP_DIR=/tmp/agentic-uploads-staging
```

### **Production (.env)**
```bash
# Use external directories for production
AGENTIC_DATA_DIR=/var/lib/agentic-service
AGENTIC_TEMP_DIR=/tmp/agentic-uploads

# Or database + S3 for high-scale
DATABASE_URL=postgresql://user:pass@localhost/agentic_db
STORAGE_BACKEND=s3
S3_ENDPOINT=your-s3-endpoint
```

## 🚀 **Migration Path**

1. **Immediate**: Set `AGENTIC_DATA_DIR` to external directory
2. **Short-term**: Implement database for metadata
3. **Medium-term**: Move files to S3-compatible storage
4. **Long-term**: Full hybrid architecture with Redis caching

## 📝 **Best Practices**

### **For Development:**
- Keep using `.data/` and `.tmp_uploads/` in project
- Add these directories to `.gitignore`
- Use environment variables for configuration

### **For Production:**
- **Never** store user data in project directories
- Use external, dedicated data directories
- Implement proper backup strategies
- Set restrictive file permissions
- Monitor disk usage and cleanup old sessions

### **For Enterprise:**
- Use database for metadata and session management
- Use object storage for file storage
- Implement Redis for caching and performance
- Set up automated backup and recovery
- Monitor and alert on storage usage

---

## 🎯 **Recommendation**

**Start with Option 1 (External Directories)** - it's a quick fix that solves most immediate problems and provides a clear path to more advanced solutions.

**Move to Option 2 (Database + S3)** when you need better scalability and reliability.

**Consider Option 3 (Hybrid)** for enterprise deployments with thousands of users.
