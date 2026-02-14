"""Tests for metadata store."""

import pytest
from pathlib import Path
import tempfile
from data_librarian.ingestion.metadata_store import MetadataStore


@pytest.fixture
def temp_db():
    """Fixture for temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


def test_metadata_store_initialization(temp_db):
    """Test metadata store initialization."""
    store = MetadataStore(temp_db)
    assert temp_db.exists()


def test_store_and_retrieve_catalog(temp_db):
    """Test storing and retrieving catalog structure."""
    store = MetadataStore(temp_db)

    structure = {"catalogs": [{"name": "test", "schemas": []}]}

    store.store_catalog_structure(structure)
    retrieved = store.get_catalog_structure()

    assert retrieved == structure


def test_store_searchable_items(temp_db):
    """Test storing searchable items."""
    store = MetadataStore(temp_db)

    items = [
        {
            "type": "table",
            "catalog": "test_catalog",
            "schema": "test_schema",
            "table": "test_table",
            "full_name": "test_catalog.test_schema.test_table",
        }
    ]

    store.store_searchable_items(items)
    retrieved = store.get_searchable_items()

    assert len(retrieved) == 1
    assert retrieved[0]["full_name"] == "test_catalog.test_schema.test_table"


def test_filter_searchable_items(temp_db):
    """Test filtering searchable items."""
    store = MetadataStore(temp_db)

    items = [
        {
            "type": "table",
            "catalog": "catalog1",
            "schema": "schema1",
            "table": "table1",
            "full_name": "catalog1.schema1.table1",
        },
        {
            "type": "table",
            "catalog": "catalog2",
            "schema": "schema2",
            "table": "table2",
            "full_name": "catalog2.schema2.table2",
        },
    ]

    store.store_searchable_items(items)

    # Filter by catalog
    filtered = store.get_searchable_items(catalog="catalog1")
    assert len(filtered) == 1
    assert filtered[0]["catalog"] == "catalog1"


def test_clear_data(temp_db):
    """Test clearing data."""
    store = MetadataStore(temp_db)

    structure = {"catalogs": []}
    store.store_catalog_structure(structure)

    store.clear()

    assert store.get_catalog_structure() is None
    assert len(store.get_searchable_items()) == 0
