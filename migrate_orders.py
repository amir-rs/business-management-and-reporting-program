#!/usr/bin/env python3
"""
Database migration script to add Order and OrderItem tables
"""

import sqlite3
import os

def migrate_orders():
    """Add Order and OrderItem tables to the database"""
    
    # Check if database exists
    if not os.path.exists('cafe.db'):
        print("Database not found. Please run the application first to create the database.")
        return
    
    conn = sqlite3.connect('cafe.db')
    cursor = conn.cursor()
    
    try:
        # Check if Order table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order'")
        if cursor.fetchone():
            print("Order table already exists. Skipping migration.")
            return
        
        # Create Order table
        cursor.execute('''
            CREATE TABLE "order" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number VARCHAR(20) UNIQUE NOT NULL,
                customer_name VARCHAR(100),
                customer_phone VARCHAR(20),
                total_amount FLOAT NOT NULL DEFAULT 0,
                status VARCHAR(20) DEFAULT 'preparing',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create OrderItem table
        cursor.execute('''
            CREATE TABLE order_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price FLOAT NOT NULL,
                total_price FLOAT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES "order" (id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES product (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX idx_order_invoice_number ON "order" (invoice_number)')
        cursor.execute('CREATE INDEX idx_order_status ON "order" (status)')
        cursor.execute('CREATE INDEX idx_order_created_at ON "order" (created_at)')
        cursor.execute('CREATE INDEX idx_order_item_order_id ON order_item (order_id)')
        cursor.execute('CREATE INDEX idx_order_item_product_id ON order_item (product_id)')
        
        conn.commit()
        print("✅ Order and OrderItem tables created successfully!")
        print("✅ Indexes created for better performance!")
        
    except sqlite3.Error as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔄 Starting Order system migration...")
    migrate_orders()
    print("✅ Migration completed!")
