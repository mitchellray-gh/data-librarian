"""Local storage for catalog metadata."""

import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager


class MetadataStore:
    """SQLite-based storage for catalog metadata."""

    def __init__(self, db_path: Path):
        """Initialize metadata store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Get a database connection context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Metadata table for storing complete catalog structure
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Searchable items table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS searchable_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    catalog TEXT NOT NULL,
                    schema TEXT NOT NULL,
                    table_name TEXT,
                    column_name TEXT,
                    full_name TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_searchable_catalog 
                ON searchable_items(catalog)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_searchable_schema 
                ON searchable_items(schema)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_searchable_full_name 
                ON searchable_items(full_name)
            """
            )

            conn.commit()

    def store_catalog_structure(self, structure: Dict[str, Any]) -> int:
        """Store the complete catalog structure.

        Args:
            structure: Catalog structure dictionary

        Returns:
            ID of the stored record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Clear old data
            cursor.execute("DELETE FROM catalog_metadata")

            # Insert new data
            cursor.execute(
                """
                INSERT INTO catalog_metadata (data, last_updated)
                VALUES (?, ?)
            """,
                (json.dumps(structure), datetime.now().isoformat()),
            )

            conn.commit()
            return cursor.lastrowid

    def get_catalog_structure(self) -> Optional[Dict[str, Any]]:
        """Retrieve the stored catalog structure.

        Returns:
            Catalog structure dictionary or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT data FROM catalog_metadata 
                ORDER BY last_updated DESC 
                LIMIT 1
            """
            )
            row = cursor.fetchone()

            if row:
                return json.loads(row["data"])
            return None

    def store_searchable_items(self, items: List[Dict[str, Any]]):
        """Store searchable items.

        Args:
            items: List of searchable item dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Clear old items
            cursor.execute("DELETE FROM searchable_items")

            # Insert new items
            for item in items:
                cursor.execute(
                    """
                    INSERT INTO searchable_items 
                    (item_type, catalog, schema, table_name, column_name, full_name, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item.get("type", ""),
                        item.get("catalog", ""),
                        item.get("schema", ""),
                        item.get("table", ""),
                        item.get("column", ""),
                        item.get("full_name", ""),
                        json.dumps(item),
                    ),
                )

            conn.commit()

    def get_searchable_items(
        self, catalog: Optional[str] = None, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve searchable items with optional filters.

        Args:
            catalog: Optional catalog name filter
            schema: Optional schema name filter

        Returns:
            List of searchable items
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT metadata FROM searchable_items WHERE 1=1"
            params = []

            if catalog:
                query += " AND catalog = ?"
                params.append(catalog)

            if schema:
                query += " AND schema = ?"
                params.append(schema)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [json.loads(row["metadata"]) for row in rows]

    def get_last_updated(self) -> Optional[datetime]:
        """Get the timestamp of the last catalog update.

        Returns:
            Datetime of last update or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT last_updated FROM catalog_metadata 
                ORDER BY last_updated DESC 
                LIMIT 1
            """
            )
            row = cursor.fetchone()

            if row:
                return datetime.fromisoformat(row["last_updated"])
            return None

    def clear(self):
        """Clear all stored data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM catalog_metadata")
            cursor.execute("DELETE FROM searchable_items")
            conn.commit()
