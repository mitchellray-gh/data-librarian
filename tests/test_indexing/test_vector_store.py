"""Tests for vector store."""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil
from data_librarian.indexing.vector_store import VectorStore


@pytest.fixture
def temp_store_path():
    """Fixture for temporary vector store path."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def vector_store(temp_store_path):
    """Fixture for vector store."""
    return VectorStore(dimension=384, store_path=temp_store_path)


def test_vector_store_initialization(vector_store):
    """Test vector store initialization."""
    assert vector_store.index is not None
    assert vector_store.size() == 0


def test_add_vectors(vector_store):
    """Test adding vectors."""
    vectors = np.random.rand(3, 384).astype("float32")
    metadata = [
        {"id": 1, "name": "item1"},
        {"id": 2, "name": "item2"},
        {"id": 3, "name": "item3"},
    ]

    vector_store.add_vectors(vectors, metadata)

    assert vector_store.size() == 3


def test_search_vectors(vector_store):
    """Test searching vectors."""
    # Add some vectors
    vectors = np.random.rand(5, 384).astype("float32")
    metadata = [{"id": i, "name": f"item{i}"} for i in range(5)]

    vector_store.add_vectors(vectors, metadata)

    # Search with first vector
    query = vectors[0]
    distances, results = vector_store.search(query, k=3)

    assert len(results) == 3
    assert results[0]["id"] == 0  # Should match itself


def test_save_and_load(temp_store_path):
    """Test saving and loading vector store."""
    # Create and populate store
    store1 = VectorStore(dimension=384, store_path=temp_store_path)
    vectors = np.random.rand(3, 384).astype("float32")
    metadata = [{"id": i} for i in range(3)]
    store1.add_vectors(vectors, metadata)
    store1.save()

    # Load in new instance
    store2 = VectorStore(dimension=384, store_path=temp_store_path)

    assert store2.size() == 3
    assert len(store2.metadata) == 3


def test_clear_store(vector_store):
    """Test clearing the store."""
    vectors = np.random.rand(3, 384).astype("float32")
    metadata = [{"id": i} for i in range(3)]

    vector_store.add_vectors(vectors, metadata)
    assert vector_store.size() == 3

    vector_store.clear()
    assert vector_store.size() == 0
