"""Tests for catalog parser."""

import pytest
from data_librarian.ingestion.catalog_parser import (
    CatalogParser,
    ColumnMetadata,
    TableMetadata,
    SchemaMetadata,
    CatalogMetadata,
    CatalogStructure,
)


def test_column_metadata_from_api():
    """Test creating ColumnMetadata from API response."""
    data = {
        "name": "user_id",
        "type_text": "bigint",
        "type_name": "BIGINT",
        "position": 0,
        "comment": "User identifier",
        "nullable": False,
    }

    column = ColumnMetadata.from_api_response(data)

    assert column.name == "user_id"
    assert column.type_name == "BIGINT"
    assert column.comment == "User identifier"
    assert column.nullable is False


def test_table_metadata_from_api():
    """Test creating TableMetadata from API response."""
    data = {
        "name": "users",
        "full_name": "catalog.schema.users",
        "table_type": "MANAGED",
        "comment": "User data",
        "columns": [
            {"name": "id", "type_text": "int", "type_name": "INT", "position": 0}
        ],
    }

    table = TableMetadata.from_api_response(data, "catalog", "schema")

    assert table.name == "users"
    assert table.catalog_name == "catalog"
    assert table.schema_name == "schema"
    assert len(table.columns) == 1
    assert table.columns[0].name == "id"


def test_catalog_parser_flatten():
    """Test flattening catalog structure."""
    api_response = {
        "catalogs": [
            {
                "name": "test_catalog",
                "comment": "Test catalog",
                "schemas": [
                    {
                        "name": "test_schema",
                        "comment": "Test schema",
                        "tables": [
                            {
                                "name": "test_table",
                                "full_name": "test_catalog.test_schema.test_table",
                                "table_type": "MANAGED",
                                "comment": "Test table",
                                "columns": [
                                    {
                                        "name": "id",
                                        "type_text": "int",
                                        "type_name": "INT",
                                        "position": 0,
                                        "comment": "ID column",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    parser = CatalogParser()
    structure = parser.parse_catalog_structure(api_response)
    items = parser.flatten_to_searchable_items(structure)

    # Should have 1 table + 1 column = 2 items
    assert len(items) == 2

    # Check table item
    table_item = items[0]
    assert table_item["type"] == "table"
    assert table_item["full_name"] == "test_catalog.test_schema.test_table"

    # Check column item
    column_item = items[1]
    assert column_item["type"] == "column"
    assert column_item["column"] == "id"
