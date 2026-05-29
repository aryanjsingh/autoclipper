#!/usr/bin/env python3
"""
Script to add thumbnail column to projects table
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.core.database import engine, SessionLocal
from sqlalchemy import text

def add_thumbnail_column():
    """Add thumbnail column to projects table"""
    try:
        # Check if column already exists
        with engine.connect() as conn:
            # For SQLite, check table structure
            result = conn.execute(text("PRAGMA table_info(projects)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'thumbnail' in columns:
                print("thumbnail column already exists, no need to add")
                return True
            
            # Add thumbnail column
            conn.execute(text("ALTER TABLE projects ADD COLUMN thumbnail TEXT"))
            conn.commit()
            print("Successfully added thumbnail column to projects table")
            return True
            
    except Exception as e:
        print(f"Failed to add thumbnail column: {e}")
        return False

def main():
    """Main function"""
    print("Starting to add thumbnail column...")
    
    if add_thumbnail_column():
        print("Thumbnail column addition complete!")
    else:
        print("Thumbnail column addition failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
