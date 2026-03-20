import sqlite3
import logging

log = logging.getLogger(__name__)


def connect(db_path):
    """Open sounds.db with Row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def get_all_samples(conn):
    """Get all samples with a local_path."""
    return conn.execute(
        "SELECT * FROM samples WHERE local_path IS NOT NULL"
    ).fetchall()
