import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def init_database():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    # -----------------------------------------------------
    # ORDERS
    # -----------------------------------------------------

    cursor.execute("""
        DROP TABLE IF EXISTS orders
    """)

    cursor.execute("""
        CREATE TABLE orders (
            id TEXT PRIMARY KEY,
            product TEXT NOT NULL,
            status TEXT NOT NULL,
            ship_date TEXT,
            eta TEXT,
            tracking_number TEXT,
            carrier TEXT
        )
    """)

    # -----------------------------------------------------
    # INVENTORY
    # -----------------------------------------------------

    cursor.execute("""
        DROP TABLE IF EXISTS inventory
    """)

    cursor.execute("""
        CREATE TABLE inventory (
            product_name TEXT PRIMARY KEY,
            sizes TEXT NOT NULL,
            stock_status TEXT NOT NULL,
            restock_date TEXT
        )
    """)

    # -----------------------------------------------------
    # CONVERSATIONS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE conversations (
            conversation_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # MESSAGES
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            intent TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # FEEDBACK
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            rating TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # SEED ORDERS
    # -----------------------------------------------------

    orders = [

        (
            "1001",
            "Blue Sneakers",
            "shipped",
            "2026-08-08",
            "2026-08-13",
            "NS1001",
            "Northstar Express"
        ),

        (
            "1002",
            "White Run Shoes",
            "processing",
            None,
            "2026-08-16",
            None,
            None
        ),

        (
            "1003",
            "Black Hoodie",
            "delivered",
            "2026-08-05",
            "2026-08-09",
            "NS1003",
            "Northstar Express"
        )

    ]

    cursor.executemany(
        """
        INSERT INTO orders
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        orders
    )

    # -----------------------------------------------------
    # SEED INVENTORY
    # -----------------------------------------------------

    inventory = [

        (
            "blue sneakers",
            "8, 9, 10",
            "in_stock",
            None
        ),

        (
            "white run shoes",
            "7, 8, 9, 10, 11",
            "in_stock",
            None
        ),

        (
            "black hoodie",
            "S, M, L, XL",
            "out_of_stock",
            "2026-08-20"
        )

    ]

    cursor.executemany(
        """
        INSERT INTO inventory
        VALUES (?, ?, ?, ?)
        """,
        inventory
    )

    conn.commit()

    conn.close()

    print("Northstar database initialized successfully.")


if __name__ == "__main__":
    init_database()
