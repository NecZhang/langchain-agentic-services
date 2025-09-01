#!/usr/bin/env python3
"""
Migration script to move data from file-based storage to PostgreSQL database.

This script will:
1. Read existing data from .data/ directory
2. Migrate users, sessions, and chat history to PostgreSQL
3. Preserve file uploads and processing caches
4. Create a backup of the original data

Usage:
    python migrate_to_database.py [--backup-only] [--dry-run]
"""

import argparse
import json
import os
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_agent.database import init_db, SessionLocal
from langchain_agent.db_service import DatabaseService


class FileStorageMigrator:
    """Migrate data from file storage to PostgreSQL database."""
    
    def __init__(self, data_dir: str = ".data", backup_dir: str = ".data_backup"):
        self.data_dir = Path(data_dir)
        self.backup_dir = Path(backup_dir)
        self.db_service = DatabaseService()
        
    def backup_existing_data(self) -> bool:
        """Create a backup of existing data directory."""
        try:
            if self.data_dir.exists():
                if self.backup_dir.exists():
                    shutil.rmtree(self.backup_dir)
                
                print(f"📦 Creating backup at {self.backup_dir}")
                shutil.copytree(self.data_dir, self.backup_dir)
                print(f"✅ Backup created successfully")
                return True
            else:
                print(f"⚠️  Data directory {self.data_dir} does not exist")
                return False
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return False
    
    def migrate_users_and_sessions(self) -> Dict[str, int]:
        """Migrate users and sessions from file structure."""
        print("👥 Migrating users and sessions...")
        
        migrated_users = 0
        migrated_sessions = 0
        
        if not self.data_dir.exists():
            print("⚠️  No data directory found, skipping migration")
            return {"users": 0, "sessions": 0}
        
        users_dir = self.data_dir / "users"
        if not users_dir.exists():
            print("⚠️  No users directory found")
            return {"users": 0, "sessions": 0}
        
        for user_dir in users_dir.iterdir():
            if not user_dir.is_dir():
                continue
                
            user_id = user_dir.name
            print(f"  📁 Processing user: {user_id}")
            
            # Create user in database
            try:
                user = self.db_service.get_or_create_user(user_id)
                migrated_users += 1
                
                # Process sessions for this user
                sessions_dir = user_dir / "sessions"
                if sessions_dir.exists():
                    for session_dir in sessions_dir.iterdir():
                        if not session_dir.is_dir():
                            continue
                            
                        session_id = session_dir.name
                        print(f"    📂 Processing session: {session_id}")
                        
                        # Create session in database
                        session = self.db_service.get_or_create_session(user_id, session_id)
                        migrated_sessions += 1
                        
            except Exception as e:
                print(f"    ❌ Error processing user {user_id}: {e}")
                continue
        
        print(f"✅ Migrated {migrated_users} users and {migrated_sessions} sessions")
        return {"users": migrated_users, "sessions": migrated_sessions}
    
    def migrate_chat_history(self) -> int:
        """Migrate chat history from JSONL files."""
        print("💬 Migrating chat history...")
        
        migrated_messages = 0
        
        if not self.data_dir.exists():
            print("⚠️  No data directory found, skipping migration")
            return 0
        
        users_dir = self.data_dir / "users"
        if not users_dir.exists():
            print("⚠️  No users directory found")
            return 0
        
        for user_dir in users_dir.iterdir():
            if not user_dir.is_dir():
                continue
                
            user_id = user_dir.name
            sessions_dir = user_dir / "sessions"
            
            if not sessions_dir.exists():
                continue
                
            for session_dir in sessions_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                    
                session_id = session_dir.name
                chat_file = session_dir / "chat_history.jsonl"
                
                if not chat_file.exists():
                    continue
                
                print(f"  📝 Migrating chat history for {user_id}/{session_id}")
                
                try:
                    # Read and parse chat history
                    with open(chat_file, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue
                                
                            try:
                                chat_data = json.loads(line)
                                
                                # Extract data from old format
                                role = chat_data.get('role', 'user')
                                content = chat_data.get('content', '')
                                timestamp = chat_data.get('ts')
                                
                                # Convert timestamp if needed
                                if timestamp:
                                    try:
                                        # Assume timestamp is Unix timestamp
                                        dt = datetime.fromtimestamp(timestamp)
                                    except (ValueError, TypeError):
                                        dt = datetime.utcnow()
                                else:
                                    dt = datetime.utcnow()
                                
                                # Add to database
                                metadata = {
                                    "migrated_from_file": True,
                                    "original_timestamp": timestamp,
                                    "migration_date": datetime.utcnow().isoformat()
                                }
                                
                                self.db_service.add_chat_message(
                                    user_id, session_id, role, content, metadata
                                )
                                migrated_messages += 1
                                
                            except json.JSONDecodeError as e:
                                print(f"    ⚠️  Invalid JSON on line {line_num}: {e}")
                                continue
                            except Exception as e:
                                print(f"    ❌ Error processing line {line_num}: {e}")
                                continue
                                
                except Exception as e:
                    print(f"    ❌ Error reading chat file {chat_file}: {e}")
                    continue
        
        print(f"✅ Migrated {migrated_messages} chat messages")
        return migrated_messages
    
    def migrate_documents(self) -> int:
        """Migrate document metadata and uploads."""
        print("📄 Migrating document metadata...")
        
        migrated_documents = 0
        
        if not self.data_dir.exists():
            print("⚠️  No data directory found, skipping migration")
            return 0
        
        users_dir = self.data_dir / "users"
        if not users_dir.exists():
            print("⚠️  No users directory found")
            return 0
        
        for user_dir in users_dir.iterdir():
            if not user_dir.is_dir():
                continue
                
            user_id = user_dir.name
            sessions_dir = user_dir / "sessions"
            
            if not sessions_dir.exists():
                continue
                
            for session_dir in sessions_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                    
                session_id = session_dir.name
                uploads_dir = session_dir / "uploads"
                
                if not uploads_dir.exists():
                    continue
                
                print(f"  📁 Processing uploads for {user_id}/{session_id}")
                
                for file_path in uploads_dir.iterdir():
                    if not file_path.is_file():
                        continue
                    
                    try:
                        filename = file_path.name
                        file_size = file_path.stat().st_size
                        
                        # Compute file hash
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                            file_hash = hashlib.sha256(file_content).hexdigest()
                        
                        # Determine file type
                        file_type = file_path.suffix.lstrip('.') if file_path.suffix else 'unknown'
                        
                        # Add document to database
                        metadata = {
                            "migrated_from_file": True,
                            "original_path": str(file_path),
                            "migration_date": datetime.utcnow().isoformat()
                        }
                        
                        doc = self.db_service.add_document(
                            user_id, session_id, filename, file_hash, 
                            file_size, file_type, metadata=metadata
                        )
                        
                        # Add file storage info
                        self.db_service.add_file_storage(
                            doc.id, "local", str(file_path), metadata=metadata
                        )
                        
                        migrated_documents += 1
                        
                    except Exception as e:
                        print(f"    ❌ Error processing file {file_path}: {e}")
                        continue
        
        print(f"✅ Migrated {migrated_documents} documents")
        return migrated_documents
    
    def migrate_processing_caches(self) -> int:
        """Migrate processing caches from file storage."""
        print("🔧 Migrating processing caches...")
        
        migrated_caches = 0
        
        if not self.data_dir.exists():
            print("⚠️  No data directory found, skipping migration")
            return 0
        
        users_dir = self.data_dir / "users"
        if not users_dir.exists():
            print("⚠️  No users directory found")
            return 0
        
        for user_dir in users_dir.iterdir():
            if not user_dir.is_dir():
                continue
                
            user_id = user_dir.name
            sessions_dir = user_dir / "sessions"
            
            if not sessions_dir.exists():
                continue
                
            for session_dir in sessions_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                    
                session_id = session_dir.name
                caches_dir = session_dir / "caches"
                
                if not caches_dir.exists():
                    continue
                
                print(f"  🗂️  Processing caches for {user_id}/{session_id}")
                
                for cache_dir in caches_dir.iterdir():
                    if not cache_dir.is_dir():
                        continue
                    
                    try:
                        # Parse cache directory name (format: <doc_hash>_<mode>)
                        cache_name = cache_dir.name
                        if '_' not in cache_name:
                            continue
                            
                        doc_hash, mode = cache_name.rsplit('_', 1)
                        
                        # Look for chunks.json file
                        chunks_file = cache_dir / "chunks.json"
                        if chunks_file.exists():
                            with open(chunks_file, 'r', encoding='utf-8') as f:
                                chunks_data = json.load(f)
                                
                                # Add to database
                                metadata = {
                                    "migrated_from_file": True,
                                    "original_path": str(cache_dir),
                                    "migration_date": datetime.utcnow().isoformat()
                                }
                                
                                cache = self.db_service.set_processing_cache(
                                    user_id, session_id, doc_hash, mode, 
                                    {"chunks": chunks_data}, metadata=metadata
                                )
                                
                                migrated_caches += 1
                        
                    except Exception as e:
                        print(f"    ❌ Error processing cache {cache_dir}: {e}")
                        continue
        
        print(f"✅ Migrated {migrated_caches} processing caches")
        return migrated_caches
    
    def run_migration(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run the complete migration process."""
        print("🚀 Starting migration from file storage to PostgreSQL...")
        
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
        
        # Initialize database
        if not dry_run:
            print("🗄️  Initializing database...")
            init_db()
            print("✅ Database initialized")
        
        # Create backup
        print("💾 Creating backup of existing data...")
        if not dry_run:
            backup_success = self.backup_existing_data()
            if not backup_success:
                print("⚠️  Backup failed, but continuing with migration")
        else:
            print("  📦 Would create backup (dry run)")
        
        # Run migrations
        results = {}
        
        if not dry_run:
            results["users_sessions"] = self.migrate_users_and_sessions()
            results["chat_history"] = self.migrate_chat_history()
            results["documents"] = self.migrate_documents()
            results["processing_caches"] = self.migrate_processing_caches()
        else:
            print("  👥 Would migrate users and sessions (dry run)")
            print("  💬 Would migrate chat history (dry run)")
            print("  📄 Would migrate documents (dry run)")
            print("  🔧 Would migrate processing caches (dry run)")
        
        print("🎉 Migration completed!")
        return results
    
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'db_service'):
            self.db_service.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate from file storage to PostgreSQL")
    parser.add_argument("--backup-only", action="store_true", 
                       help="Only create backup, don't migrate")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be migrated without making changes")
    parser.add_argument("--data-dir", default=".data",
                       help="Source data directory (default: .data)")
    parser.add_argument("--backup-dir", default=".data_backup",
                       help="Backup directory (default: .data_backup)")
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = FileStorageMigrator(args.data_dir, args.backup_dir)
    
    try:
        if args.backup_only:
            print("📦 Creating backup only...")
            migrator.backup_existing_data()
        else:
            results = migrator.run_migration(dry_run=args.dry_run)
            if not args.dry_run:
                print("\n📊 Migration Summary:")
                for key, value in results.items():
                    if isinstance(value, dict):
                        print(f"  {key}: {value}")
                    else:
                        print(f"  {key}: {value}")
    
    finally:
        migrator.cleanup()


if __name__ == "__main__":
    main()

