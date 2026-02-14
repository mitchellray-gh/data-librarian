"""Text embedding generation for catalog metadata."""

from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np


class Embedder:
    """Text embedder using sentence transformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the embedder.

        Args:
            model_name: Name of the sentence transformer model
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        return self.model.encode(text, convert_to_numpy=True)

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for encoding

        Returns:
            Array of embedding vectors
        """
        return self.model.encode(
            texts, convert_to_numpy=True, batch_size=batch_size, show_progress_bar=True
        )

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors.

        Returns:
            Embedding dimension
        """
        return self.model.get_sentence_embedding_dimension()
