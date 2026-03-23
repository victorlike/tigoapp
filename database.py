"""
database.py — Supabase (PostgreSQL) connection pool
"""
import os
import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Connection pool: min 1, max 10 simultaneous connections
_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL
        )
    return _pool


def get_conn():
    """Get a connection from the pool."""
    return get_pool().getconn()


def release_conn(conn):
    """Return a connection to the pool."""
    get_pool().putconn(conn)


def execute(query: str, params=None, fetch=False):
    """Run a query and optionally return results."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            conn.commit()
            if fetch:
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                return [dict(zip(cols, row)) for row in rows]
    except Exception:
        conn.rollback()
        raise
    finally:
        release_conn(conn)


def fetchone(query: str, params=None):
    """Run a query and return a single row as dict."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if cur.description:
                cols = [d[0] for d in cur.description]
                row = cur.fetchone()
                return dict(zip(cols, row)) if row else None
            return None
    finally:
        release_conn(conn)
