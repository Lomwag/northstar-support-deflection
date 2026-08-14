"""
Northstar Support Deflection - Chatbot Engine

Handles:
- Order tracking
- Stock availability
- Returns
- Refunds
- Shipping questions
- Human escalation fallback
- Basic conversation context
"""

import os
import re
import sqlite3
from typing import Any, Dict, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_db():
    """Create a SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------
# INTENT DETECTION
# ---------------------------------------------------------

def detect_intent(message: Any) -> str:
    """
    Determine what the customer wants.

    This is deliberately deterministic for the MVP.
    It can later be replaced with an LLM classifier.
    """

    if message is None:
        return "unknown"

    text = str(message).strip().lower()

    if not text:
        return "unknown"

    # Human support
    human_patterns = [
        "talk to human",
        "talk to an agent",
        "human agent",
        "customer service",
        "customer support",
        "representative",
        "real person",
        "speak to someone",
    ]

    if any(pattern in text for pattern in human_patterns):
        return "support"

    # Returns
    return_patterns = [
        "return",
        "send back",
        "send it back",
        "give it back",
        "return my item",
        "return my order",
        "how do i return",
    ]

    if any(pattern in text for pattern in return_patterns):
        return "return"

    # Refunds
    refund_patterns = [
        "refund",
        "money back",
        "get my money",
        "refund status",
        "when will i get my refund",
    ]

    if any(pattern in text for pattern in refund_patterns):
        return "refund"

    # Cancellation
    cancel_patterns = [
        "cancel my order",
        "cancel order",
        "i want to cancel",
        "cancel this order",
    ]

    if any(pattern in text for pattern in cancel_patterns):
        return "cancel"

    # Stock
    stock_patterns = [
        "in stock",
        "available",
        "availability",
        "stock",
        "what sizes",
        "sizes available",
        "do you have",
        "restock",
    ]

    if any(pattern in text for pattern in stock_patterns):
        return "stock"

    # Shipping
    shipping_patterns = [
        "shipping",
        "delivery time",
        "how long does delivery",
        "how long will delivery",
        "delivery take",
        "when will it arrive",
        "shipping time",
    ]

    if any(pattern in text for pattern in shipping_patterns):
        return "shipping"

    # Order tracking
    order_patterns = [
        "order",
        "tracking",
        "track my",
        "where is my package",
        "where is my parcel",
        "has my package arrived",
        "has my order arrived",
        "package",
        "parcel",
    ]

    if any(pattern in text for pattern in order_patterns):
        return "order_status"

    return "unknown"


# ---------------------------------------------------------
# ENTITY EXTRACTION
# ---------------------------------------------------------

def extract_order_id(message: Any) -> Optional[str]:
    """Extract an order number such as 1001 or #1001."""

    if not message:
        return None

    text = str(message)

    patterns = [
        r"order\s*#?\s*(\d+)",
        r"#\s*(\d{3,})",
        r"\b(\d{4,})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(1)

    return None


def extract_product(message: Any) -> Optional[str]:
    """Find a product name from the inventory."""

    if not message:
        return None

    text = str(message).lower()

    try:
        with get_db() as conn:

            products = conn.execute(
                "SELECT product_name FROM inventory"
            ).fetchall()

            # Match longest product name first
            products = sorted(
                products,
                key=lambda row: len(row["product_name"]),
                reverse=True
            )

            for product in products:

                product_name = product["product_name"]

                if product_name.lower() in text:
                    return product_name

    except sqlite3.Error:
        return None

    return None


# ---------------------------------------------------------
# ORDER STATUS
# ---------------------------------------------------------

def get_order(order_id: str):

    if not order_id:
        return None

    try:

        with get_db() as conn:

            return conn.execute(
                """
                SELECT
                    id,
                    product,
                    status,
                    ship_date,
                    eta,
                    tracking_number,
                    carrier
                FROM orders
                WHERE id = ?
                """,
                (order_id,)
            ).fetchone()

    except sqlite3.Error:

        return None


def handle_order_status(order_id: Optional[str]) -> Dict[str, Any]:

    if not order_id:

        return {
            "message": (
                "I'd be happy to track your order. "
                "Please enter your order number, for example "
                "<strong>#1001</strong>."
            ),
            "type": "ask_order"
        }

    order = get_order(order_id)

    if not order:

        return {
            "message": (
                f"I couldn't find order <strong>#{order_id}</strong>. "
                "Please check the number and try again."
            ),
            "type": "error"
        }

    return {
        "message": (
            f"Your order <strong>#{order['id']}</strong> "
            f"for <strong>{order['product']}</strong> is "
            f"<strong>{order['status'].title()}</strong>."
        ),
        "type": "order",
        "order": dict(order)
    }


# ---------------------------------------------------------
# STOCK
# ---------------------------------------------------------

def handle_stock(product: Optional[str]) -> Dict[str, Any]:

    if not product:

        return {
            "message": (
                "Sure! Which product would you like me to check? "
                "For example: <strong>Are Blue Sneakers in stock?</strong>"
            ),
            "type": "ask_product"
        }

    try:

        with get_db() as conn:

            item = conn.execute(
                """
                SELECT
                    product_name,
                    sizes,
                    stock_status,
                    restock_date
                FROM inventory
                WHERE LOWER(product_name) = LOWER(?)
                """,
                (product,)
            ).fetchone()

    except sqlite3.Error:

        return {
            "message": (
                "I'm having trouble checking inventory right now. "
                "Please try again."
            ),
            "type": "error"
        }

    if not item:

        return {
            "message": (
                f"I couldn't find <strong>{product}</strong> "
                "in our product catalog."
            ),
            "type": "error"
        }

    if item["stock_status"] == "in_stock":

        return {
            "message": (
                f"Good news! <strong>{item['product_name']}</strong> "
                "is currently <strong>in stock</strong>."
            ),
            "type": "product",
            "product": dict(item)
        }

    restock = item["restock_date"]

    restock_text = ""

    if restock:
        restock_text = f" Expected restock: <strong>{restock}</strong>."

    return {
        "message": (
            f"<strong>{item['product_name']}</strong> "
            f"is currently <strong>out of stock</strong>."
            f"{restock_text}"
        ),
        "type": "product",
        "product": dict(item)
    }


# ---------------------------------------------------------
# RETURNS
# ---------------------------------------------------------

def handle_return(order_id: Optional[str]) -> Dict[str, Any]:

    if not order_id:

        return {
            "message": (
                "No problem — I can help you start a return. "
                "Please provide your order number."
            ),
            "type": "ask_order"
        }

    order = get_order(order_id)

    if not order:

        return {
            "message": (
                f"I couldn't find order <strong>#{order_id}</strong>. "
                "Please check the number."
            ),
            "type": "error"
        }

    return {
        "message": (
            f"You're requesting a return for "
            f"<strong>{order['product']}</strong> "
            f"(order #{order['id']}).<br><br>"
            "For this MVP, returns can be initiated through "
            "our self-service process. Please confirm that "
            "the item is unused and in its original condition."
        ),
        "type": "return",
        "order": dict(order)
    }


# ---------------------------------------------------------
# REFUNDS
# ---------------------------------------------------------

def handle_refund(order_id: Optional[str]) -> Dict[str, Any]:

    if not order_id:

        return {
            "message": (
                "I can help you with your refund. "
                "Please provide your order number."
            ),
            "type": "ask_order"
        }

    order = get_order(order_id)

    if not order:

        return {
            "message": (
                f"I couldn't find order <strong>#{order_id}</strong>."
            ),
            "type": "error"
        }

    return {
        "message": (
            f"I found order <strong>#{order['id']}</strong> "
            f"for <strong>{order['product']}</strong>.<br><br>"
            "Refunds are normally processed after the returned "
            "item has been received and inspected."
        ),
        "type": "refund",
        "order": dict(order)
    }


# ---------------------------------------------------------
# SHIPPING
# ---------------------------------------------------------

def handle_shipping():

    return {
        "message": (
            "🚚 <strong>Standard delivery</strong><br><br>"
            "Orders normally arrive within "
            "<strong>3–5 business days</strong> after dispatch."
            "<br><br>"
            "Want an order-specific ETA? Send me your order number."
        ),
        "type": "shipping"
    }


# ---------------------------------------------------------
# SUPPORT
# ---------------------------------------------------------

def handle_support():

    return {
        "message": (
            "I can connect you with our support team if I can't "
            "resolve your issue here. Before doing that, tell me "
            "what you need help with."
        ),
        "type": "support"
    }


# ---------------------------------------------------------
# MAIN RESPONSE ENGINE
# ---------------------------------------------------------

def get_response(
    message: Any,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    context = context or {}

    intent = detect_intent(message)

    order_id = extract_order_id(message)

    product = extract_product(message)

    # Use previous conversation context
    if not order_id:
        order_id = context.get("order_id")

    if not product:
        product = context.get("product")

    result = None

    if intent == "order_status":

        result = handle_order_status(order_id)

    elif intent == "stock":

        result = handle_stock(product)

    elif intent == "return":

        result = handle_return(order_id)

    elif intent == "refund":

        result = handle_refund(order_id)

    elif intent == "shipping":

        result = handle_shipping()

    elif intent == "cancel":

        result = {
            "message": (
                "I can help with cancellation. "
                "Please provide your order number so I can "
                "check whether the order is still eligible."
            ),
            "type": "ask_order"
        }

    elif intent == "support":

        result = handle_support()

    else:

        result = {
            "message": (
                "I'm Northstar, your instant support assistant. "
                "I can help you with:<br><br>"
                "📦 <strong>Order tracking</strong><br>"
                "👟 <strong>Product availability</strong><br>"
                "↩️ <strong>Returns</strong><br>"
                "💰 <strong>Refunds</strong><br>"
                "🚚 <strong>Shipping</strong><br><br>"
                "What would you like help with?"
            ),
            "type": "general"
        }

    # Metadata
    result["intent"] = intent
    result["order_id"] = order_id
    result["product"] = product

    return result
