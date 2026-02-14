"""Parser for Databricks catalog metadata."""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ColumnMetadata:
    """Metadata for a table column."""

    name: str
    type_text: str
    type_name: str
    position: int
    comment: str = ""
    nullable: bool = True

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "ColumnMetadata":
        """Create ColumnMetadata from API response.

        Args:
            data: Column data from API

        Returns:
            ColumnMetadata instance
        """
        return cls(
            name=data.get("name", ""),
            type_text=data.get("type_text", ""),
            type_name=data.get("type_name", ""),
            position=data.get("position", 0),
            comment=data.get("comment", ""),
            nullable=data.get("nullable", True),
        )


@dataclass
class TableMetadata:
    """Metadata for a catalog table."""

    name: str
    full_name: str
    catalog_name: str
    schema_name: str
    table_type: str
    comment: str = ""
    columns: List[ColumnMetadata] = field(default_factory=list)

    @classmethod
    def from_api_response(
        cls, data: Dict[str, Any], catalog_name: str, schema_name: str
    ) -> "TableMetadata":
        """Create TableMetadata from API response.

        Args:
            data: Table data from API
            catalog_name: Name of the catalog
            schema_name: Name of the schema

        Returns:
            TableMetadata instance
        """
        columns = [ColumnMetadata.from_api_response(col) for col in data.get("columns", [])]

        return cls(
            name=data.get("name", ""),
            full_name=data.get("full_name", ""),
            catalog_name=catalog_name,
            schema_name=schema_name,
            table_type=data.get("table_type", ""),
            comment=data.get("comment", ""),
            columns=columns,
        )


@dataclass
class SchemaMetadata:
    """Metadata for a catalog schema."""

    name: str
    catalog_name: str
    comment: str = ""
    tables: List[TableMetadata] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any], catalog_name: str) -> "SchemaMetadata":
        """Create SchemaMetadata from API response.

        Args:
            data: Schema data from API
            catalog_name: Name of the catalog

        Returns:
            SchemaMetadata instance
        """
        schema_name = data.get("name", "")
        tables = [
            TableMetadata.from_api_response(table, catalog_name, schema_name)
            for table in data.get("tables", [])
        ]

        return cls(
            name=schema_name,
            catalog_name=catalog_name,
            comment=data.get("comment", ""),
            tables=tables,
        )


@dataclass
class CatalogMetadata:
    """Metadata for a Unity Catalog."""

    name: str
    comment: str = ""
    schemas: List[SchemaMetadata] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "CatalogMetadata":
        """Create CatalogMetadata from API response.

        Args:
            data: Catalog data from API

        Returns:
            CatalogMetadata instance
        """
        catalog_name = data.get("name", "")
        schemas = [
            SchemaMetadata.from_api_response(schema, catalog_name)
            for schema in data.get("schemas", [])
        ]

        return cls(
            name=catalog_name,
            comment=data.get("comment", ""),
            schemas=schemas,
        )


@dataclass
class CatalogStructure:
    """Complete catalog structure."""

    catalogs: List[CatalogMetadata] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "CatalogStructure":
        """Create CatalogStructure from API response.

        Args:
            data: Complete catalog structure from API

        Returns:
            CatalogStructure instance
        """
        catalogs = [
            CatalogMetadata.from_api_response(catalog) for catalog in data.get("catalogs", [])
        ]

        return cls(
            catalogs=catalogs,
            last_updated=datetime.now(),
        )


class CatalogParser:
    """Parser for Databricks catalog metadata."""

    @staticmethod
    def parse_catalog_structure(api_response: Dict[str, Any]) -> CatalogStructure:
        """Parse the complete catalog structure from API response.

        Args:
            api_response: Raw API response

        Returns:
            Parsed CatalogStructure
        """
        return CatalogStructure.from_api_response(api_response)

    @staticmethod
    def flatten_to_searchable_items(structure: CatalogStructure) -> List[Dict[str, Any]]:
        """Flatten catalog structure to searchable items for embedding.

        Args:
            structure: Parsed catalog structure

        Returns:
            List of searchable items with metadata
        """
        items = []

        for catalog in structure.catalogs:
            for schema in catalog.schemas:
                for table in schema.tables:
                    # Add table-level item
                    table_item = {
                        "type": "table",
                        "catalog": catalog.name,
                        "schema": schema.name,
                        "table": table.name,
                        "full_name": table.full_name,
                        "table_type": table.table_type,
                        "comment": table.comment,
                        "text": f"Table: {table.full_name}\nType: {table.table_type}\nDescription: {table.comment}",
                    }
                    items.append(table_item)

                    # Add column-level items
                    for column in table.columns:
                        column_item = {
                            "type": "column",
                            "catalog": catalog.name,
                            "schema": schema.name,
                            "table": table.name,
                            "column": column.name,
                            "full_name": f"{table.full_name}.{column.name}",
                            "data_type": column.type_name,
                            "comment": column.comment,
                            "text": f"Column: {table.full_name}.{column.name}\nType: {column.type_name}\nDescription: {column.comment}",
                        }
                        items.append(column_item)

        return items
