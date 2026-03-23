"""
database.py — Supabase (PostgreSQL) connection pool
"""
import os
import psycopg2
import psycopg2.pool
import logging
import socket
from dotenv import load_dotenv

# WORKAROUND: Force IPv4 for environments with broken IPv6 routing (like some Railway regions)
original_getaddrinfo = socket.getaddrinfo
def forced_getaddrinfo(*args, **kwargs):
    # Force address family to AF_INET (IPv4)
    return original_getaddrinfo(args[0], args[1], socket.AF_INET, *args[3:])

socket.getaddrinfo = forced_getaddrinfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.strip()

# Connection pool: min 1, max 10 simultaneous connections
_pool = None


def get_pool():
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            logger.error("DATABASE_URL environment variable is not set!")
            raise RuntimeError("DATABASE_URL is not set. Please check your Railway environment variables.")
        
        try:
            logger.info("Initializing connection pool...")
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DATABASE_URL
            )
            logger.info("Connection pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise RuntimeError(f"Could not connect to database: {e}")
    return _pool


def get_conn():
    """Get a connection from the pool."""
    try:
        pool = get_pool()
        return pool.getconn()
    except Exception as e:
        logger.error(f"Error getting connection from pool: {e}")
        raise


def release_conn(conn):
    """Return a connection to the pool."""
    if conn:
        try:
            get_pool().putconn(conn)
        except Exception as e:
            logger.error(f"Error releasing connection: {e}")


def execute(query: str, params=None, fetch=False):
    """Run a query and optionally return results."""
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            conn.commit()
            if fetch:
                if cur.description:
                    cols = [d[0] for d in cur.description]
                    rows = cur.fetchall()
                    return [dict(zip(cols, row)) for row in rows]
                return []
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database execute error: {e}")
        raise
    finally:
        if conn:
            release_conn(conn)


def fetchone(query: str, params=None):
    """Run a query and return a single row as dict."""
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if cur.description:
                cols = [d[0] for d in cur.description]
                row = cur.fetchone()
                return dict(zip(cols, row)) if row else None
            return None
    except Exception as e:
        logger.error(f"Database fetchone error: {e}")
        raise
    finally:
        if conn:
            release_conn(conn)


def bulk_execute(query: str, params_list: list):
    """Run a bulk insert/update operation."""
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.executemany(query, params_list)
            conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database bulk_execute error: {e}")
        raise
    finally:
        if conn:
            release_conn(conn)


def rollback_and_release(conn):
    """Rollback and return a connection to the pool."""
    if conn:
        try:
            conn.rollback()
        except:
            pass
        release_conn(conn)
