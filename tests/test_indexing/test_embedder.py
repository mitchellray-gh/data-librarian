"""Tests for embedder."""

import pytest
import numpy as np
from data_librarian.indexing.embedder import Embedder


@pytest.fixture
def embedder():
    """Fixture for embedder."""
    return Embedder()


def test_embedder_initialization(embedder):
    """Test embedder initialization."""
    assert embedder.model is not None
    assert embedder.get_embedding_dimension() > 0


def test_embed_single_text(embedder):
    """Test embedding a single text."""
    text = "This is a test table for user data"
    embedding = embedder.embed_text(text)

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape[0] == embedder.get_embedding_dimension()


def test_embed_multiple_texts(embedder):
    """Test embedding multiple texts."""
    texts = [
        "User table with customer information",
        "Order table with transaction data",
        "Product catalog with item details",
    ]

    embeddings = embedder.embed_texts(texts)

    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape[0] == len(texts)
    assert embeddings.shape[1] == embedder.get_embedding_dimension()


def test_embedding_consistency(embedder):
    """Test that same text produces same embedding."""
    text = "Test table"

    embedding1 = embedder.embed_text(text)
    embedding2 = embedder.embed_text(text)

    np.testing.assert_array_almost_equal(embedding1, embedding2)
