import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
from data_mining.config import settings
from data_mining.db.models import SCHEMA_SQL


def get_db_path(custom_path: Optional[Path] = None) -> Path:
    path = custom_path or settings.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db(custom_path: Optional[Path] = None) -> None:
    db_path = get_db_path(custom_path)
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db(custom_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    db_path = get_db_path(custom_path)
    conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
