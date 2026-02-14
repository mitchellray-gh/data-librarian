"""Retriever for finding relevant catalog entries."""

from typing import List, Dict, Any, Tuple
from ..indexing.embedder import Embedder
from ..indexing.vector_store import VectorStore


class Retriever:
    """Retrieves relevant catalog entries for user queries."""

    def __init__(self, embedder: Embedder, vector_store: VectorStore):
        """Initialize the retriever.

        Args:
            embedder: Embedder instance for query encoding
            vector_store: Vector store for similarity search
        """
        self.embedder = embedder
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-K most relevant catalog entries for a query.

        Args:
            query: Natural language query
            top_k: Number of results to retrieve

        Returns:
            List of relevant catalog items with metadata
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_text(query)

        # Search vector store
        distances, results = self.vector_store.search(query_embedding, k=top_k)

        # Add similarity scores
        for i, result in enumerate(results):
            result["similarity_score"] = float(distances[i])

        return results

    def retrieve_with_filters(
        self, query: str, catalog: str = None, schema: str = None, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant entries with optional filters.

        Args:
            query: Natural language query
            catalog: Optional catalog name filter
            schema: Optional schema name filter
            top_k: Number of results to retrieve

        Returns:
            List of relevant catalog items with metadata
        """
        # Get all results
        results = self.retrieve(query, top_k=top_k * 2)  # Get more to allow for filtering

        # Apply filters
        filtered_results = []
        for result in results:
            if catalog and result.get("catalog") != catalog:
                continue
            if schema and result.get("schema") != schema:
                continue
            filtered_results.append(result)

        # Return top-k after filtering
        return filtered_results[:top_k]
