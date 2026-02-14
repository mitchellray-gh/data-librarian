"""Tests for retriever."""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil
from data_librarian.indexing.embedder import Embedder
from data_librarian.indexing.vector_store import VectorStore
from data_librarian.engine.retriever import Retriever


@pytest.fixture
def temp_store_path():
    """Fixture for temporary vector store path."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def retriever(temp_store_path):
    """Fixture for retriever with sample data."""
    embedder = Embedder()
    vector_store = VectorStore(
        dimension=embedder.get_embedding_dimension(), store_path=temp_store_path
    )

    # Add sample data
    texts = [
        "User table with customer information",
        "Order table with transaction data",
        "Product catalog with item details",
    ]
    embeddings = embedder.embed_texts(texts)

    metadata = [
        {
            "type": "table",
            "catalog": "main",
            "schema": "sales",
            "table": "users",
            "full_name": "main.sales.users",
        },
        {
            "type": "table",
            "catalog": "main",
            "schema": "sales",
            "table": "orders",
            "full_name": "main.sales.orders",
        },
        {
            "type": "table",
            "catalog": "main",
            "schema": "inventory",
            "table": "products",
            "full_name": "main.inventory.products",
        },
    ]

    vector_store.add_vectors(embeddings, metadata)

    return Retriever(embedder, vector_store)


def test_retriever_basic_search(retriever):
    """Test basic retrieval."""
    results = retriever.retrieve("Find customer data", top_k=2)

    assert len(results) == 2
    assert "similarity_score" in results[0]


def test_retriever_with_catalog_filter(retriever):
    """Test retrieval with catalog filter."""
    results = retriever.retrieve_with_filters(
        "Find data", catalog="main", top_k=5
    )

    assert len(results) <= 5
    for result in results:
        assert result["catalog"] == "main"


def test_retriever_with_schema_filter(retriever):
    """Test retrieval with schema filter."""
    results = retriever.retrieve_with_filters(
        "Find data", schema="sales", top_k=5
    )

    assert len(results) <= 5
    for result in results:
        assert result["schema"] == "sales"
