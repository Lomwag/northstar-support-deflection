import os
import sqlite3
import uuid
from datetime import datetime

from flask import Flask, jsonify, render_template, request, session

from chatbot import get_response


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


app = Flask(__name__)

# Never hard-code production secrets.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "northstar-development-secret"
)


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_db():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

@app.route("/")
def home():

    if "conversation_id" not in session:

        session["conversation_id"] = str(uuid.uuid4())

    return render_template("index.html")


# ---------------------------------------------------------
# CHAT API
# ---------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True) or {}

    user_message = data.get("message")

    if not isinstance(user_message, str):

        return jsonify({
            "success": False,
            "error": "Message must be text."
        }), 400

    user_message = user_message.strip()

    if not user_message:

        return jsonify({
            "success": False,
            "error": "Please enter a message."
        }), 400

    if len(user_message) > 1000:

        return jsonify({
            "success": False,
            "error": "Message is too long."
        }), 400

    conversation_id = session.get("conversation_id")

    if not conversation_id:

        conversation_id = str(uuid.uuid4())

        session["conversation_id"] = conversation_id

    # Retrieve context
    context = {}

    try:

        with get_db() as conn:

            rows = conn.execute(
                """
                SELECT role, message
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT 10
                """,
                (conversation_id,)
            ).fetchall()

            for row in rows:

                if row["role"] == "assistant":
                    continue

    except sqlite3.Error:

        pass

    response = get_response(
        user_message,
        context
    )

    # Save conversation
    try:

        with get_db() as conn:

            conn.execute(
                """
                INSERT INTO conversations
                (conversation_id, created_at)
                VALUES (?, ?)
                ON CONFLICT(conversation_id)
                DO NOTHING
                """,
                (
                    conversation_id,
                    datetime.utcnow().isoformat()
                )
            )

            conn.execute(
                """
                INSERT INTO messages
                (conversation_id, role, message, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    "user",
                    user_message,
                    response.get("intent"),
                    datetime.utcnow().isoformat()
                )
            )

            conn.execute(
                """
                INSERT INTO messages
                (conversation_id, role, message, intent, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    "assistant",
                    response["message"],
                    response.get("intent"),
                    datetime.utcnow().isoformat()
                )
            )

            conn.commit()

    except sqlite3.Error:

        # The chatbot can still answer even if analytics persistence fails.
        pass

    return jsonify({
        "success": True,
        "conversation_id": conversation_id,
        **response
    })


# ---------------------------------------------------------
# FEEDBACK
# ---------------------------------------------------------

@app.route("/api/feedback", methods=["POST"])
def feedback():

    data = request.get_json(silent=True) or {}

    rating = data.get("rating")

    if rating not in ["positive", "negative"]:

        return jsonify({
            "success": False,
            "error": "Invalid feedback."
        }), 400

    conversation_id = session.get("conversation_id")

    try:

        with get_db() as conn:

            conn.execute(
                """
                INSERT INTO feedback
                (conversation_id, rating, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    conversation_id,
                    rating,
                    datetime.utcnow().isoformat()
                )
            )

            conn.commit()

    except sqlite3.Error:

        return jsonify({
            "success": False,
            "error": "Unable to save feedback."
        }), 500

    return jsonify({
        "success": True
    })


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.route("/api/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "Northstar Support Deflection"
    })


# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )
