"""
database.py
Camada de acesso ao banco de dados (SQLite).
Responsável por criar o schema e fornecer funções de acesso aos dados.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "stockflow.db"


def get_connection():
    """Retorna uma conexão SQLite com row_factory configurado para dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria as tabelas do banco caso ainda não existam."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Geral',
            quantity INTEGER NOT NULL DEFAULT 0,
            min_stock INTEGER NOT NULL DEFAULT 5,
            unit_price REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            rows_total INTEGER NOT NULL,
            rows_imported INTEGER NOT NULL,
            rows_rejected INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# CRUD de produtos
# ---------------------------------------------------------------------------

def list_products(search: str = "", category: str = ""):
    conn = get_connection()
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY name ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(product_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_product(name, category, quantity, min_stock, unit_price):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO products (name, category, quantity, min_stock, unit_price)
           VALUES (?, ?, ?, ?, ?)""",
        (name, category, quantity, min_stock, unit_price),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_product(product_id, name, category, quantity, min_stock, unit_price):
    conn = get_connection()
    conn.execute(
        """UPDATE products
           SET name = ?, category = ?, quantity = ?, min_stock = ?, unit_price = ?,
               updated_at = datetime('now')
           WHERE id = ?""",
        (name, category, quantity, min_stock, unit_price, product_id),
    )
    conn.commit()
    conn.close()


def delete_product(product_id):
    conn = get_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()


def get_categories():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()
    conn.close()
    return [r["category"] for r in rows]


# ---------------------------------------------------------------------------
# Métricas para o dashboard
# ---------------------------------------------------------------------------

def get_dashboard_metrics():
    conn = get_connection()
    total_products = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    total_value = conn.execute(
        "SELECT COALESCE(SUM(quantity * unit_price), 0) AS v FROM products"
    ).fetchone()["v"]
    low_stock = conn.execute(
        "SELECT * FROM products WHERE quantity <= min_stock ORDER BY quantity ASC"
    ).fetchall()
    by_category = conn.execute(
        """SELECT category, COUNT(*) AS total, SUM(quantity) AS units
           FROM products GROUP BY category ORDER BY total DESC"""
    ).fetchall()
    conn.close()
    return {
        "total_products": total_products,
        "total_value": total_value,
        "low_stock": [dict(r) for r in low_stock],
        "by_category": [dict(r) for r in by_category],
    }


def log_import(filename, rows_total, rows_imported, rows_rejected):
    conn = get_connection()
    conn.execute(
        """INSERT INTO import_log (filename, rows_total, rows_imported, rows_rejected)
           VALUES (?, ?, ?, ?)""",
        (filename, rows_total, rows_imported, rows_rejected),
    )
    conn.commit()
    conn.close()


def get_import_history(limit=10):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM import_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
