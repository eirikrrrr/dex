"""SQLite helper to initialize and connect the local crawler database."""

from pathlib import Path
import sqlite3

from crawler.database.schema import SCHEMA_SQL


class SQLiteDatabase:
    def __init__(self, db_path: str = "crawler.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.commit()
