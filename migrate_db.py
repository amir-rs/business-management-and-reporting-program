#!/usr/bin/env python3
"""
Database migration script to handle unit conversion changes.
This script will update existing materials to use the new unit conversion system.
"""

import sqlite3
import os

def migrate_database():
    """Migrate the existing database to support unit conversions"""
    
    # Check if database exists
    if not os.path.exists('instance/cafe.db'):
        print("Database not found. Please run the application first to create the database.")
        return
    
    print("Starting database migration...")
    
    # Connect to database
    conn = sqlite3.connect('instance/cafe.db')
    cursor = conn.cursor()
    
    try:
        # Check if migration is needed
        cursor.execute("PRAGMA table_info(raw_material)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'display_unit' not in columns:
            print("Adding display_unit column...")
            cursor.execute("ALTER TABLE raw_material ADD COLUMN display_unit TEXT DEFAULT 'gram'")
            
            # Update existing records to use 'gram' as display_unit
            cursor.execute("UPDATE raw_material SET display_unit = 'gram' WHERE display_unit IS NULL")
            
            print("Migration completed successfully!")
        else:
            print("Migration already completed. No changes needed.")
            
        conn.commit()
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
