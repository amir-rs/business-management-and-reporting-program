#!/usr/bin/env python3
"""
Migration script to add 'deleted' column to product table
Run this after running app.py to create the database
"""

import sqlite3
import os

def migrate_add_deleted_column():
    """Add deleted column to product table"""
    
    # Database path
    db_path = "instance/cafe.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        print("Please run app.py first to create the database")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking if 'deleted' column exists...")
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(product)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'deleted' in columns:
            print("✅ 'deleted' column already exists!")
            return True
        
        print("➕ Adding 'deleted' column to product table...")
        
        # Add the deleted column with default value False (0)
        cursor.execute("ALTER TABLE product ADD COLUMN deleted BOOLEAN DEFAULT 0")
        
        # Update existing products to have deleted = 0 (False)
        cursor.execute("UPDATE product SET deleted = 0 WHERE deleted IS NULL")
        
        # Commit changes
        conn.commit()
        
        print("✅ Successfully added 'deleted' column to product table!")
        print("✅ All existing products marked as not deleted")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(product)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Current columns: {', '.join(columns)}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Starting migration: Add 'deleted' column to product table")
    print("=" * 60)
    
    success = migrate_add_deleted_column()
    
    print("=" * 60)
    if success:
        print("🎉 Migration completed successfully!")
        print("You can now run the application with soft delete functionality.")
    else:
        print("💥 Migration failed!")
        print("Please check the error messages above.")
