"""
database.py — Supabase (PostgreSQL) connection pool
"""
import os
import psycopg2
import psycopg2.pool
import logging
from dotenv import load_dotenv

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
            
            # Diagnostic: log parsed params (WITHOUT password)
            try:
                from psycopg2.extensions import parse_dsn
                params = parse_dsn(DATABASE_URL)
                # Mask sensitive info
                safe_params = {k: (v if k != 'password' else '********') for k, v in params.items()}
                logger.info(f"Connecting with params: {safe_params}")
            except Exception as de:
                logger.warning(f"Could not parse DSN for logging: {de}")

            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DATABASE_URL,
                connect_timeout=10,
                options="-c timezone=America/Montevideo -c prepare_threshold=0"
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


def log_audit(actor: str, action: str, target: str = None, details: str = None):
    """Log an audit event asynchronously via execute."""
    try:
        execute(
            "INSERT INTO audit_logs (actor, action, target, details) VALUES (%s, %s, %s, %s)",
            (actor, action, target, details)
        )
    except Exception as e:
        logger.error(f"Failed to write audit log [{action}]: {e}")
