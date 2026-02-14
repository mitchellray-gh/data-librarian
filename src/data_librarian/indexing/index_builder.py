"""Index builder orchestrating the ingestion and indexing pipeline."""

from typing import Optional
from pathlib import Path

from ..config.settings import settings
from ..ingestion.databricks_client import DatabricksClient, DatabricksConfig
from ..ingestion.catalog_parser import CatalogParser
from ..ingestion.metadata_store import MetadataStore
from .embedder import Embedder
from .vector_store import VectorStore


class IndexBuilder:
    """Orchestrates the catalog ingestion and indexing pipeline."""

    def __init__(
        self,
        databricks_config: Optional[DatabricksConfig] = None,
        metadata_db_path: Optional[Path] = None,
        vector_store_path: Optional[Path] = None,
        embedding_model: Optional[str] = None,
    ):
        """Initialize the index builder.

        Args:
            databricks_config: Databricks configuration
            metadata_db_path: Path to metadata database
            vector_store_path: Path to vector store
            embedding_model: Embedding model name
        """
        # Initialize Databricks client
        if databricks_config is None:
            databricks_config = DatabricksConfig(
                host=settings.DATABRICKS_HOST, token=settings.DATABRICKS_TOKEN
            )
        self.databricks_client = DatabricksClient(databricks_config)

        # Initialize metadata store
        if metadata_db_path is None:
            metadata_db_path = settings.get_metadata_db_path()
        self.metadata_store = MetadataStore(metadata_db_path)

        # Initialize embedder
        if embedding_model is None:
            embedding_model = settings.EMBEDDING_MODEL
        self.embedder = Embedder(embedding_model)

        # Initialize vector store
        if vector_store_path is None:
            vector_store_path = settings.get_vector_store_path()
        self.vector_store = VectorStore(
            dimension=self.embedder.get_embedding_dimension(), store_path=vector_store_path
        )

        self.parser = CatalogParser()

    def ingest_and_index(self, force_refresh: bool = False) -> dict:
        """Ingest catalog data and build the index.

        Args:
            force_refresh: If True, force a complete refresh even if data exists

        Returns:
            Dictionary with ingestion statistics
        """
        stats = {
            "catalogs": 0,
            "schemas": 0,
            "tables": 0,
            "columns": 0,
            "searchable_items": 0,
        }

        # Check if we need to refresh
        last_updated = self.metadata_store.get_last_updated()
        if last_updated and not force_refresh:
            print(f"Catalog last updated: {last_updated}. Use force_refresh=True to rebuild.")
            return stats

        print("Fetching catalog structure from Databricks...")
        raw_structure = self.databricks_client.get_catalog_structure()

        print("Parsing catalog structure...")
        parsed_structure = self.parser.parse_catalog_structure(raw_structure)

        # Store metadata
        print("Storing catalog metadata...")
        self.metadata_store.store_catalog_structure(raw_structure)

        # Flatten to searchable items
        print("Creating searchable items...")
        searchable_items = self.parser.flatten_to_searchable_items(parsed_structure)
        self.metadata_store.store_searchable_items(searchable_items)

        # Generate embeddings
        print(f"Generating embeddings for {len(searchable_items)} items...")
        texts = [item["text"] for item in searchable_items]
        embeddings = self.embedder.embed_texts(texts)

        # Clear and rebuild vector store
        print("Building vector index...")
        self.vector_store.clear()
        self.vector_store.add_vectors(embeddings, searchable_items)
        self.vector_store.save()

        # Calculate stats
        stats["catalogs"] = len(parsed_structure.catalogs)
        stats["schemas"] = sum(len(cat.schemas) for cat in parsed_structure.catalogs)
        stats["tables"] = sum(
            len(schema.tables) for cat in parsed_structure.catalogs for schema in cat.schemas
        )
        stats["columns"] = sum(
            len(table.columns)
            for cat in parsed_structure.catalogs
            for schema in cat.schemas
            for table in schema.tables
        )
        stats["searchable_items"] = len(searchable_items)

        print(f"\n✓ Indexing complete!")
        print(f"  Catalogs: {stats['catalogs']}")
        print(f"  Schemas: {stats['schemas']}")
        print(f"  Tables: {stats['tables']}")
        print(f"  Columns: {stats['columns']}")
        print(f"  Indexed items: {stats['searchable_items']}")

        return stats

    def get_status(self) -> dict:
        """Get the current index status.

        Returns:
            Dictionary with status information
        """
        last_updated = self.metadata_store.get_last_updated()
        vector_count = self.vector_store.size()

        return {
            "last_updated": last_updated.isoformat() if last_updated else None,
            "indexed_items": vector_count,
            "status": "ready" if vector_count > 0 else "not_indexed",
        }
