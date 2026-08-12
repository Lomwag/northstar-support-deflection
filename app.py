import os
import sqlite3
import re
from flask import Flask, request, jsonify, render_template

# Import our custom chatbot logic function from chatbot.py
from chatbot import get_response, detect_intent

# Initialize the Flask application
# template_folder tells Flask where to look for HTML files (index.html)
app = Flask(__name__, template_folder="templates")
app.secret_key = "northstar_support_deflection_mvp_secret"

# Locate the SQLite database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


@app.route("/")
def index():
    """
    GET Route: Renders and serves the main chatbot UI page.
    When you visit http://127.0.0.1:5000/ in a browser, this function runs.
    """
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    POST Route: Receives the user's typed message, queries the database chatbot,
    and returns a JSON response containing the chatbot's text.
    Supports both JSON payloads and standard Form submissions.
    """
    try:
        user_message = ""
        
        # 1. Parse the request message from JSON or standard HTML Form data
        if request.is_json:
            data = request.get_json()
            if data and "message" in data:
                user_message = data["message"]
        else:
            user_message = request.form.get("message", "")
            
        # Validate that we have a message to process
        if not user_message and user_message != "":
            return jsonify({
                "status": "error",
                "response": "Please enter a message to chat."
            }), 400
            
        # 2. Query our chatbot core logic to retrieve the bot response text
        bot_reply = get_response(user_message)
        
        # 3. Detect intent to provide metadata flags for the frontend (like ticket forms)
        intent = detect_intent(user_message)
        
        show_ticket_form = False
        suggest_ticket = False
        prefilled_order_id = ""
        
        if intent == "support":
            show_ticket_form = True
        elif "couldn't find order" in bot_reply:
            suggest_ticket = True
            # Attempt to extract order ID from user query to prefill form
            match = re.search(r'order\s*(?:#\s*)?([a-zA-Z0-9]+)', user_message.lower())
            if match:
                prefilled_order_id = match.group(1)
        
        # 4. Return response payload back to the browser Javascript
        return jsonify({
            "status": "success",
            "response": bot_reply,
            "intent": intent,
            "show_ticket_form": show_ticket_form,
            "suggest_ticket": suggest_ticket,
            "prefilled_order_id": prefilled_order_id
        })
        
    except Exception as e:
        # Wrap everything in try/except to prevent 500 error pages
        # Returns a friendly JSON error message instead of crashing
        return jsonify({
            "status": "error",
            "response": "I encountered an error processing your query. Please try again."
        }), 500


@app.route("/api/ticket", methods=["POST"])
def create_ticket():
    """
    POST Route: Creates a support ticket in the SQLite database.
    Expects customer_name, customer_email, issue_description, and optional order_id.
    """
    try:
        # Check input source (JSON vs Form Data)
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
            
        if not data:
            return jsonify({
                "status": "error",
                "response": "Missing form data."
            }), 400
            
        customer_name = data.get("customer_name", "").strip()
        customer_email = data.get("customer_email", "").strip()
        issue_description = data.get("issue_description", "").strip()
        order_id = data.get("order_id", "").strip()
        
        # Validate inputs
        if not customer_name or not customer_email or not issue_description:
            return jsonify({
                "status": "error",
                "response": "Please fill out all required fields."
            }), 400
            
        if "@" not in customer_email or "." not in customer_email:
            return jsonify({
                "status": "error",
                "response": "Please enter a valid email address."
            }), 400
            
        # Save to SQLite tickets table
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickets (order_id, customer_name, customer_email, issue_description)
            VALUES (?, ?, ?, ?);
        """, (order_id if order_id else None, customer_name, customer_email, issue_description))
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success",
            "ticket_id": ticket_id,
            "message": f"Successfully created Support Ticket #{ticket_id}."
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "response": "Could not create support ticket. Please try again later."
        }), 500


if __name__ == "__main__":
    print("=" * 60)
    print("Starting Northstar Web Chatbot on http://127.0.0.1:5000")
    print("=" * 60)
    # Runs the server locally in debug mode
    # debug=True automatically reloads the server when code files change
    app.run(host="127.0.0.1", port=5000, debug=True)
