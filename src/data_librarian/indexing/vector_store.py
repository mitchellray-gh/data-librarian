"""Vector store for similarity search using FAISS."""

import faiss
import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple


class VectorStore:
    """FAISS-based vector store for similarity search."""

    def __init__(self, dimension: int, store_path: Path):
        """Initialize the vector store.

        Args:
            dimension: Dimension of the embedding vectors
            store_path: Path to store the index and metadata
        """
        self.dimension = dimension
        self.store_path = store_path
        self.store_path.mkdir(parents=True, exist_ok=True)

        self.index_path = self.store_path / "faiss.index"
        self.metadata_path = self.store_path / "metadata.json"

        # Initialize or load index
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            self.metadata = self._load_metadata()
        else:
            # Use IndexFlatL2 for exact search (good for small-medium datasets)
            self.index = faiss.IndexFlatL2(dimension)
            self.metadata = []

    def _load_metadata(self) -> List[Dict[str, Any]]:
        """Load metadata from file.

        Returns:
            List of metadata dictionaries
        """
        if self.metadata_path.exists():
            with open(self.metadata_path, "r") as f:
                return json.load(f)
        return []

    def _save_metadata(self):
        """Save metadata to file."""
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)

    def add_vectors(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
        """Add vectors and their metadata to the store.

        Args:
            vectors: Array of embedding vectors
            metadata: List of metadata dictionaries corresponding to vectors
        """
        if len(vectors) != len(metadata):
            raise ValueError("Number of vectors must match number of metadata items")

        # Normalize vectors for cosine similarity (optional but recommended)
        faiss.normalize_L2(vectors)

        # Add to index
        self.index.add(vectors)

        # Store metadata
        self.metadata.extend(metadata)

    def search(
        self, query_vector: np.ndarray, k: int = 5
    ) -> Tuple[List[float], List[Dict[str, Any]]]:
        """Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            k: Number of results to return

        Returns:
            Tuple of (distances, metadata) for top k results
        """
        # Normalize query vector
        query_vector = query_vector.reshape(1, -1)
        faiss.normalize_L2(query_vector)

        # Search
        distances, indices = self.index.search(query_vector, k)

        # Get metadata for results
        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.metadata):
                results.append(self.metadata[idx])

        return distances[0].tolist(), results

    def save(self):
        """Save the index and metadata to disk."""
        faiss.write_index(self.index, str(self.index_path))
        self._save_metadata()

    def clear(self):
        """Clear the index and metadata."""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []

        # Remove saved files
        if self.index_path.exists():
            self.index_path.unlink()
        if self.metadata_path.exists():
            self.metadata_path.unlink()

    def size(self) -> int:
        """Get the number of vectors in the store.

        Returns:
            Number of vectors
        """
        return self.index.ntotal
