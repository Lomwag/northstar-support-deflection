import os
import sqlite3
import tempfile

import pytest

import chatbot


@pytest.fixture
def test_database(monkeypatch):

    fd, path = tempfile.mkstemp(
        suffix=".db"
    )

    os.close(fd)

    monkeypatch.setattr(
        chatbot,
        "DB_PATH",
        path
    )

    conn = sqlite3.connect(path)

    conn.execute("""
        CREATE TABLE orders (
            id TEXT PRIMARY KEY,
            product TEXT,
            status TEXT,
            ship_date TEXT,
            eta TEXT,
            tracking_number TEXT,
            carrier TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE inventory (
            product_name TEXT PRIMARY KEY,
            sizes TEXT,
            stock_status TEXT,
            restock_date TEXT
        )
    """)

    conn.execute("""
        INSERT INTO orders
        VALUES (
            '1001',
            'Blue Sneakers',
            'shipped',
            '2026-08-08',
            '2026-08-13',
            'NS1001',
            'Northstar Express'
        )
    """)

    conn.execute("""
        INSERT INTO inventory
        VALUES (
            'blue sneakers',
            '8, 9, 10',
            'in_stock',
            NULL
        )
    """)

    conn.commit()

    conn.close()

    yield

    os.remove(path)


def test_order_intent():

    assert (
        chatbot.detect_intent(
            "Where is my order #1001?"
        )
        == "order_status"
    )


def test_stock_intent():

    assert (
        chatbot.detect_intent(
            "Do you have blue sneakers?"
        )
        == "stock"
    )


def test_return_intent():

    assert (
        chatbot.detect_intent(
            "How do I return this?"
        )
        == "return"
    )


def test_refund_intent():

    assert (
        chatbot.detect_intent(
            "When will I get my refund?"
        )
        == "refund"
    )


def test_order_lookup(test_database):

    response = chatbot.get_response(
        "Where is my order #1001?"
    )

    assert response["type"] == "order"

    assert response["order_id"] == "1001"

    assert "Blue Sneakers" in response["message"]


def test_stock_lookup(test_database):

    response = chatbot.get_response(
        "Are blue sneakers in stock?"
    )

    assert response["type"] == "product"

    assert "in stock" in response["message"]


def test_missing_order():

    response = chatbot.get_response(
        "Where is my order?"
    )

    assert response["type"] == "ask_order"


def test_unknown_question():

    response = chatbot.get_response(
        "Tell me something random"
    )

    assert response["type"] == "general"


def test_empty_message():

    assert (
        chatbot.detect_intent("")
        == "unknown"
    )
