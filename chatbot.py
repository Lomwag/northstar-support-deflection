import os
import sqlite3
import re

def detect_intent(user_text):
    """
    Analyzes the user's input text to detect their intention.
    Checks for keywords related to support escalations, order status, or stock availability.
    
    Parameters:
        user_text (any): The input text from the user.
        
    Returns:
        str: "support", "order_status", "stock", or "unknown"
    """
    # Safe conversion to string, handling None or other types gracefully
    if user_text is None:
        return "unknown"
    
    text = str(user_text).lower()
    
    # Define keywords for human-agent support escalations
    support_keywords = ["support", "agent", "human", "ticket", "contact", "representative", "talk to"]
    # Define keywords for order status queries
    order_keywords = ["order", "shipped", "where is", "tracking", "when will"]
    # Define keywords for stock availability queries
    stock_keywords = ["stock", "available", "size", "restock", "in stock"]
    
    # Prioritize human escalation requests first
    for kw in support_keywords:
        if kw in text:
            return "support"
            
    # Check for order status intent next
    for kw in order_keywords:
        if kw in text:
            return "order_status"
            
    # Check for stock intent next
    for kw in stock_keywords:
        if kw in text:
            return "stock"
            
    # Default to unknown intent if no keywords match
    return "unknown"


def handle_support():
    """
    Handles support escalation requests.
    Returns a message inviting the user to fill out the inline ticket form.
    
    Returns:
        str: A response message explaining the escalation options.
    """
    return "I can help you connect with our support team. Please fill out the support form below, and one of our human agents will get back to you as soon as possible."


def handle_order_status(order_id):
    """
    Retrieves and formats the status of a specific order from the SQLite database.
    Handles SQL queries, missing IDs, unknown IDs, and malformed inputs.
    
    Parameters:
        order_id (str/int/None): The ID of the order to query.
        
    Returns:
        str: A friendly response message regarding the order status.
    """
    try:
        # Check if order_id is missing or None
        if order_id is None or str(order_id).strip() == "":
            return "Please provide an order number so I can look up the status."
            
        # Clean up the order_id by trimming whitespace
        clean_id = str(order_id).strip()
        
        # Validate that the order ID contains only digits
        if not clean_id.isdigit():
            raise ValueError("Order ID must be numeric.")
            
        # Locate the SQLite database file path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "database.db")
        
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query the order details from the 'orders' table
        cursor.execute("SELECT product, status, eta FROM orders WHERE id = ?;", (clean_id,))
        row = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        # If the order does not exist in the database
        if row is None:
            return f"I couldn't find order #{clean_id}. Please double check the number."
            
        # Extract row details
        product, status, eta = row
        
        # Construct and return a friendly response
        return f"Your order for {product} is currently {status}. The estimated delivery date (ETA) is {eta}."
        
    except Exception:
        # Safely catch database connection errors or malformed input structures
        return "Please enter a valid order number."


def handle_stock(product_name):
    """
    Checks the SQLite database inventory for a specific product.
    Handles database querying, case-insensitive matches, and stock details.
    
    Parameters:
        product_name (str/None): The name of the product to query.
        
    Returns:
        str: A friendly response message regarding product stock status.
    """
    try:
        # Check if product_name is missing or empty
        if product_name is None or str(product_name).strip() == "":
            return "Please provide a product name to check availability."
            
        # Trim whitespace and convert to lowercase for case-insensitive matching
        search_name = str(product_name).strip().lower()
        
        # Locate the SQLite database file path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "database.db")
        
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query product details from the 'inventory' table
        cursor.execute("SELECT sizes, stock_status, restock_date FROM inventory WHERE product_name = ?;", (search_name,))
        row = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        # Check if the product exists in the catalog
        if row is None:
            return f"I don't have '{product_name}' in our catalog. Could you check the spelling?"
            
        # Extract row details
        sizes_str, status, restock_date = row
        
        # Construct response based on stock availability
        if status == "in_stock":
            return f"Yes, '{product_name}' is currently in stock. Available sizes: {sizes_str}."
        else:
            restock_info = f" on {restock_date}" if restock_date else " soon"
            return f"Sorry, '{product_name}' is currently out of stock. It is expected to restock{restock_info}. Sizes normally available: {sizes_str}."
            
    except Exception:
        # Safely catch database connection errors or database table structure errors
        return "I encountered an error checking our inventory. Please try again."


def get_response(user_text, extracted_id=None, extracted_product=None):
    """
    Main router for the chatbot. Detects user intent and routes to the appropriate handler.
    Queries the SQLite database dynamically. Guarantees no unhandled exceptions are thrown to the caller.
    
    Parameters:
        user_text (any): The raw user query.
        extracted_id (str/int/None): Pre-extracted order ID, if any.
        extracted_product (str/None): Pre-extracted product name, if any.
        
    Returns:
        str: The chatbot's response text.
    """
    try:
        # 1. Detect user intent
        intent = detect_intent(user_text)
        
        # 2. Route based on intent
        if intent == "support":
            return handle_support()
            
        elif intent == "order_status":
            # Attempt to extract order ID if not explicitly provided
            if extracted_id is None and user_text:
                text_str = str(user_text).lower()
                # Regex looks for "order", optional "#" or spaces, followed by an alphanumeric ID
                match = re.search(r'order\s*(?:#\s*)?([a-zA-Z0-9]+)', text_str)
                if match:
                    extracted_id = match.group(1)
            
            return handle_order_status(extracted_id)
            
        elif intent == "stock":
            # Attempt to extract product name if not explicitly provided
            if extracted_product is None and user_text:
                text_str = str(user_text).lower()
                
                # Fetch all known product names dynamically from the SQLite catalog
                try:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    db_path = os.path.join(base_dir, "database.db")
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT product_name FROM inventory;")
                    products = [r[0] for r in cursor.fetchall()]
                    conn.close()
                    
                    # Check if any catalog product name is in the user text
                    for product_key in products:
                        if product_key in text_str:
                            extracted_product = product_key
                            break
                except Exception:
                    pass
                
                # Fallback to regex pattern extraction if catalog match is not found
                if extracted_product is None:
                    match = re.search(r'(?:is|are|have|check)\s+(?:the\s+)?(.+?)\s+(?:in\s+stock|available|in-stock|sizes|stock|restock)', text_str)
                    if match:
                        extracted_product = match.group(1).strip()
            
            return handle_stock(extracted_product)
            
        else:
            # Handle unknown intent or invalid queries
            return "Sorry, I can help with order status or stock availability. Could you rephrase your question?"
            
    except Exception:
        # Catch-all exception block to ensure the application never crashes
        return "Sorry, I encountered an unexpected error. Could you try asking that in a different way?"


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING ESCALATION-ENABLED CHATBOT MVP TEST SUITE")
    print("=" * 60)
    
    # Define test cases: (input_text, expected_substring_or_match, description)
    test_cases = [
        (
            "Where is my order 1001?", 
            lambda res: "shipped" in res and "2026-08-13" in res, 
            "Valid order ID query (1001)"
        ),
        (
            "Where is my order 9999?", 
            lambda res: "couldn't find order #9999" in res, 
            "Non-existent order ID query (9999)"
        ),
        (
            "", 
            lambda res: "rephrase" in res.lower(), 
            "Empty string query"
        ),
        (
            None, 
            lambda res: "rephrase" in res.lower(), 
            "None type query"
        ),
        (
            "Is the blue sneakers in stock?", 
            lambda res: "in stock" in res.lower() and "8, 9, 10" in res, 
            "Valid stock query (blue sneakers)"
        ),
        (
            "asdkfjasdf random text", 
            lambda res: "rephrase" in res.lower(), 
            "Unknown intent query"
        ),
        (
            "Where is my order abc?", 
            lambda res: "valid order number" in res.lower(), 
            "Malformed order ID query (abc)"
        ),
        (
            "I need to talk to a human agent",
            lambda res: "support form below" in res.lower(),
            "Support escalation intent query"
        )
    ]
    
    all_passed = True
    for i, (user_input, validator, desc) in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {desc}")
        print(f"  Input: {repr(user_input)}")
        
        # Execute the function call under test
        response = get_response(user_input)
        print(f"  Response: {repr(response)}")
        
        # Check validation
        if validator(response):
            print("  Status: PASS")
        else:
            print("  Status: FAIL")
            all_passed = False
            
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED SUCCESSFULLY!")
    else:
        print("SOME TESTS FAILED. Please review the responses.")
    print("=" * 60)
