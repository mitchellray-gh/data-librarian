"""Tests for librarian."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import shutil
from data_librarian.engine.librarian import Librarian


@pytest.fixture
def temp_data_dir():
    """Fixture for temporary data directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


def test_librarian_initialization(temp_data_dir):
    """Test librarian initialization."""
    vector_store_path = temp_data_dir / "vector_store"

    librarian = Librarian(
        vector_store_path=vector_store_path,
        llm_provider="local",
    )

    assert librarian.embedder is not None
    assert librarian.vector_store is not None
    assert librarian.retriever is not None
    assert librarian.llm_provider == "local"


def test_librarian_status(temp_data_dir):
    """Test getting librarian status."""
    vector_store_path = temp_data_dir / "vector_store"

    librarian = Librarian(
        vector_store_path=vector_store_path,
        llm_provider="local",
    )

    status = librarian.get_status()

    assert "status" in status
    assert "indexed_items" in status
    assert "llm_provider" in status
    assert status["llm_provider"] == "local"
