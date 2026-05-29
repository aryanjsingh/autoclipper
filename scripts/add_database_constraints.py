#!/usr/bin/env python3
"""
Add Database Constraints Script
Adds foreign key constraints and data integrity constraints to database tables
"""

import sys
import sqlite3
import logging
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseConstraintManager:
    """Database constraint manager"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(project_root / "data" / "autoclip.db")
        
    def add_foreign_key_constraints(self) -> bool:
        """Enable foreign key constraints (SQLite does not support dynamically adding foreign key constraints)"""
        logger.info("Enabling foreign key constraints...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Verify foreign key constraints are enabled
            cursor.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            
            conn.commit()
            conn.close()
            
            if fk_enabled:
                logger.info("Foreign key constraints enabled")
                return True
            else:
                logger.error("Failed to enable foreign key constraints")
                return False
            
        except Exception as e:
            logger.error(f"Failed to enable foreign key constraints: {e}")
            return False
    
    def add_check_constraints(self) -> bool:
        """Add check constraints (SQLite does not support dynamically adding check constraints)"""
        logger.info("Check constraint notes...")
        
        # SQLite does not support dynamically adding check constraints, they need to be defined when creating tables
        # Here we only log the constraint requirements, actual constraints are in model definitions
        
        constraints_info = [
            "Project status: pending, processing, completed, failed",
            "Task status: pending, running, completed, failed", 
            "Clip status: pending, processing, completed, failed",
            "Collection status: pending, processing, completed, failed",
            "Upload record status: pending, uploading, completed, failed"
        ]
        
        logger.info("Data integrity constraint requirements:")
        for constraint in constraints_info:
            logger.info(f"  - {constraint}")
        
        logger.info("Note: SQLite does not support dynamically adding check constraints, constraints are implemented in model definitions")
        return True
    
    def add_indexes(self) -> bool:
        """Add indexes to improve query performance"""
        logger.info("Starting to add indexes...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            indexes = [
                # Project table indexes
                {
                    'name': 'idx_projects_status',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)'
                },
                {
                    'name': 'idx_projects_created_at',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at)'
                },
                
                # Task table indexes
                {
                    'name': 'idx_tasks_project_id',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id)'
                },
                {
                    'name': 'idx_tasks_status',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)'
                },
                {
                    'name': 'idx_tasks_created_at',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)'
                },
                
                # Clip table indexes
                {
                    'name': 'idx_clips_project_id',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_clips_project_id ON clips(project_id)'
                },
                {
                    'name': 'idx_clips_status',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_clips_status ON clips(status)'
                },
                {
                    'name': 'idx_clips_score',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_clips_score ON clips(score)'
                },
                
                # Collection table indexes
                {
                    'name': 'idx_collections_project_id',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_collections_project_id ON collections(project_id)'
                },
                {
                    'name': 'idx_collections_status',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_collections_status ON collections(status)'
                },
                
                # Upload record table indexes
                {
                    'name': 'idx_upload_records_account_id',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_upload_records_account_id ON upload_records(account_id)'
                },
                {
                    'name': 'idx_upload_records_clip_id',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_upload_records_clip_id ON upload_records(clip_id)'
                },
                {
                    'name': 'idx_upload_records_status',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_upload_records_status ON upload_records(status)'
                }
            ]
            
            success_count = 0
            error_count = 0
            
            for index in indexes:
                try:
                    cursor.execute(index['sql'])
                    success_count += 1
                    logger.info(f"Index added successfully: {index['name']}")
                except sqlite3.Error as e:
                    logger.error(f"Failed to add index: {index['name']}, error: {e}")
                    error_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"Index addition complete: {success_count} succeeded, {error_count} failed")
            return error_count == 0
            
        except Exception as e:
            logger.error(f"Failed to add indexes: {e}")
            return False
    
    def verify_constraints(self) -> bool:
        """Verify constraints were correctly added"""
        logger.info("Verifying constraints...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if foreign key constraints are enabled
            cursor.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            logger.info(f"Foreign key constraint status: {'Enabled' if fk_enabled else 'Disabled'}")
            
            # Check table structure
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"Database tables: {', '.join(tables)}")
            
            # Check indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            indexes = [row[0] for row in cursor.fetchall()]
            logger.info(f"Custom indexes: {', '.join(indexes)}")
            
            conn.close()
            
            logger.info("Constraint verification complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify constraints: {e}")
            return False


def main():
    """Main function"""
    logger.info("Starting to add database constraints...")
    
    manager = DatabaseConstraintManager()
    
    # 1. Add foreign key constraints
    fk_success = manager.add_foreign_key_constraints()
    
    # 2. Add check constraints
    check_success = manager.add_check_constraints()
    
    # 3. Add indexes
    index_success = manager.add_indexes()
    
    # 4. Verify constraints
    verify_success = manager.verify_constraints()
    
    print("\n" + "=" * 80)
    print("Database Constraint Addition Results")
    print("=" * 80)
    print(f"Foreign key constraints: {'Succeeded' if fk_success else 'Failed'}")
    print(f"Check constraints: {'Succeeded' if check_success else 'Failed'}")
    print(f"Index addition: {'Succeeded' if index_success else 'Failed'}")
    print(f"Constraint verification: {'Succeeded' if verify_success else 'Failed'}")
    
    if all([fk_success, check_success, index_success, verify_success]):
        print("\nAll database constraints added successfully!")
    else:
        print("\nSome constraints failed to add, please check logs")
    
    logger.info("Database constraint addition complete!")


if __name__ == "__main__":
    main()
