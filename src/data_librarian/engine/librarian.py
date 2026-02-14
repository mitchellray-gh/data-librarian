"""Main librarian orchestrator."""

from typing import Optional, Dict, Any
from pathlib import Path

from ..config.settings import settings
from ..indexing.embedder import Embedder
from ..indexing.vector_store import VectorStore
from .retriever import Retriever
from .prompt_builder import PromptBuilder
from .llm_client import create_llm_client, LLMClient


class Librarian:
    """Main orchestrator for the Data Librarian AI assistant."""

    def __init__(
        self,
        vector_store_path: Optional[Path] = None,
        embedding_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        top_k: Optional[int] = None,
    ):
        """Initialize the librarian.

        Args:
            vector_store_path: Path to vector store
            embedding_model: Embedding model name
            llm_provider: LLM provider name
            top_k: Number of results to retrieve
        """
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

        # Initialize retriever
        self.retriever = Retriever(self.embedder, self.vector_store)

        # Initialize prompt builder
        self.prompt_builder = PromptBuilder()

        # Initialize LLM client
        if llm_provider is None:
            llm_provider = settings.LLM_PROVIDER

        self.llm_client = create_llm_client(
            provider=llm_provider,
            openai_api_key=settings.OPENAI_API_KEY,
            databricks_host=settings.DATABRICKS_HOST,
            databricks_token=settings.DATABRICKS_TOKEN,
        )

        # Settings
        self.top_k = top_k or settings.TOP_K_RESULTS
        self.llm_provider = llm_provider

    def ask(self, question: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> Dict[str, Any]:
        """Ask a question about the data catalog.

        Args:
            question: Natural language question
            catalog: Optional catalog filter
            schema: Optional schema filter

        Returns:
            Dictionary with answer and metadata
        """
        # Retrieve relevant items
        if catalog or schema:
            context_items = self.retriever.retrieve_with_filters(
                query=question, catalog=catalog, schema=schema, top_k=self.top_k
            )
        else:
            context_items = self.retriever.retrieve(query=question, top_k=self.top_k)

        # If no LLM, return formatted retrieval results
        if self.llm_provider == "local":
            answer = self.prompt_builder.format_local_response(context_items)
        else:
            # Build prompt and get LLM response
            messages = self.prompt_builder.build_messages(question, context_items)
            try:
                answer = self.llm_client.generate(prompt="", messages=messages)
            except Exception as e:
                # Fallback to local response on error
                answer = f"Error generating LLM response: {str(e)}\n\n"
                answer += self.prompt_builder.format_local_response(context_items)

        return {
            "question": question,
            "answer": answer,
            "context_items": context_items,
            "num_results": len(context_items),
        }

    def explore(self, catalog: Optional[str] = None, schema: Optional[str] = None) -> Dict[str, Any]:
        """Browse catalog structure.

        Args:
            catalog: Optional catalog name
            schema: Optional schema name

        Returns:
            Dictionary with catalog structure information
        """
        from ..ingestion.metadata_store import MetadataStore

        metadata_store = MetadataStore(settings.get_metadata_db_path())
        items = metadata_store.get_searchable_items(catalog=catalog, schema=schema)

        # Group by catalog and schema
        structure = {}
        for item in items:
            cat = item.get("catalog", "unknown")
            sch = item.get("schema", "unknown")

            if cat not in structure:
                structure[cat] = {}
            if sch not in structure[cat]:
                structure[cat][sch] = {"tables": set(), "columns": []}

            if item.get("type") == "table":
                structure[cat][sch]["tables"].add(item.get("table", ""))
            elif item.get("type") == "column":
                structure[cat][sch]["columns"].append(
                    {
                        "table": item.get("table", ""),
                        "column": item.get("column", ""),
                        "type": item.get("data_type", ""),
                    }
                )

        # Convert sets to lists
        for cat in structure:
            for sch in structure[cat]:
                structure[cat][sch]["tables"] = sorted(list(structure[cat][sch]["tables"]))

        return structure

    def get_status(self) -> Dict[str, Any]:
        """Get the status of the librarian system.

        Returns:
            Dictionary with status information
        """
        from ..ingestion.metadata_store import MetadataStore

        metadata_store = MetadataStore(settings.get_metadata_db_path())
        last_updated = metadata_store.get_last_updated()

        return {
            "indexed_items": self.vector_store.size(),
            "last_updated": last_updated.isoformat() if last_updated else None,
            "embedding_model": self.embedder.model_name,
            "llm_provider": self.llm_provider,
            "top_k": self.top_k,
            "status": "ready" if self.vector_store.size() > 0 else "not_indexed",
        }
