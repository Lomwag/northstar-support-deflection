import os
import sqlite3

def initialize_database():
    """
    Initializes a local SQLite database named 'database.db' in the project directory.
    Creates tables for 'orders', 'inventory', and 'tickets', and seeds them with mock data.
    """
    # Locate the database file path relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "database.db")
    
    print(f"Connecting to database at: {db_path}")
    
    # Establish a connection to SQLite (creates the file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ==========================================================================
    # 1. CREATE SCHEMA TABLES
    # ==========================================================================
    
    # Drop existing tables to allow clean re-runs of this script
    print("Setting up database tables...")
    cursor.execute("DROP TABLE IF EXISTS orders;")
    cursor.execute("DROP TABLE IF EXISTS inventory;")
    cursor.execute("DROP TABLE IF EXISTS tickets;")
    
    # Create the 'orders' table
    cursor.execute("""
        CREATE TABLE orders (
            id TEXT PRIMARY KEY,
            product TEXT NOT NULL,
            status TEXT NOT NULL,
            ship_date TEXT,
            eta TEXT
        );
    """)
    
    # Create the 'inventory' table
    cursor.execute("""
        CREATE TABLE inventory (
            product_name TEXT PRIMARY KEY,
            sizes TEXT NOT NULL,
            stock_status TEXT NOT NULL,
            restock_date TEXT
        );
    """)
    
    # Create the 'tickets' table for support escalations
    # id: automatically incremented primary key for tickets
    # order_id: optional linked order number
    # customer_name: name of customer submitting support request
    # customer_email: email address for agent correspondence
    # issue_description: details of user query/problem
    # status: current ticket status (default: 'open')
    # created_at: SQL timestamp of ticket creation
    cursor.execute("""
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            issue_description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # ==========================================================================
    # 2. SEED MOCK DATA
    # ==========================================================================
    
    print("Seeding database tables...")
    
    # Seed data for orders
    orders_seed = [
        ("1001", "Blue Sneakers", "shipped", "2026-08-08", "2026-08-13"),
        ("1002", "Red Boots", "processing", None, None),
        ("1003", "White Run Shoes", "delivered", "2026-08-05", "2026-08-10")
    ]
    
    cursor.executemany("""
        INSERT INTO orders (id, product, status, ship_date, eta)
        VALUES (?, ?, ?, ?, ?);
    """, orders_seed)
    
    # Seed data for inventory (catalog keys must be lowercase)
    inventory_seed = [
        ("blue sneakers", "8, 9, 10", "in_stock", None),
        ("red boots", "7, 8, 9, 10", "out_of_stock", "2026-09-01"),
        ("white run shoes", "6, 7, 8, 9, 10, 11", "in_stock", None)
    ]
    
    cursor.executemany("""
        INSERT INTO inventory (product_name, sizes, stock_status, restock_date)
        VALUES (?, ?, ?, ?);
    """, inventory_seed)
    
    # Seed data for tickets
    cursor.execute("""
        INSERT INTO tickets (order_id, customer_name, customer_email, issue_description, status)
        VALUES (?, ?, ?, ?, ?);
    """, ("1002", "Jane Doe", "jane@example.com", "My order status has been processing for 4 days.", "open"))
    
    # Commit transaction changes and close connection
    conn.commit()
    conn.close()
    print("Database successfully initialized and seeded with support tickets table!")

if __name__ == "__main__":
    initialize_database()
