import re
import sqlite3
import logging

log = logging.getLogger(__name__)


def connect(db_path):
    """Open sounds.db with Row factory and register REGEXP function."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    def regexp(expr, item):
        if item is None:
            return False
        try:
            return re.search(expr, item) is not None
        except re.error as e:
            log.warning("Invalid regex %r: %s", expr, e)
            return False

    conn.create_function("REGEXP", 2, regexp)
    return conn


def get_samples(conn, category_config):
    """Query samples matching a category's tag/file regex filters."""
    if "query" in category_config:
        return conn.execute(category_config["query"]).fetchall()

    tag_regex = category_config.get("tag_regex", "")
    file_regex = category_config.get("file_regex", "")
    include_loops = category_config.get("include_loops", True)

    clauses = ["local_path IS NOT NULL"]
    if tag_regex:
        clauses.append(f"tags REGEXP '{tag_regex}'")
    if file_regex:
        clauses.append(f"filename REGEXP '{file_regex}'")
    if not include_loops:
        clauses.append("sample_type = 'oneshot'")

    query = "SELECT * FROM samples WHERE " + " AND ".join(clauses)
    return conn.execute(query).fetchall()


def get_all_samples(conn):
    """Get all samples with a local_path."""
    return conn.execute(
        "SELECT * FROM samples WHERE local_path IS NOT NULL"
    ).fetchall()
