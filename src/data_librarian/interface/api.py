"""FastAPI web server for Data Librarian."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn

from ..config.settings import settings
from ..indexing.index_builder import IndexBuilder
from ..engine.librarian import Librarian

app = FastAPI(
    title="Data Librarian API",
    description="AI-powered Databricks Unity Catalog assistant",
    version="0.1.0",
)

# Global librarian instance
librarian = None


def get_librarian() -> Librarian:
    """Get or create librarian instance."""
    global librarian
    if librarian is None:
        librarian = Librarian()
    return librarian


class AskRequest(BaseModel):
    """Request model for ask endpoint."""

    question: str
    catalog: Optional[str] = None
    schema: Optional[str] = None
    top_k: Optional[int] = None


class AskResponse(BaseModel):
    """Response model for ask endpoint."""

    question: str
    answer: str
    num_results: int
    context_items: list


class IngestRequest(BaseModel):
    """Request model for ingest endpoint."""

    force_refresh: bool = False


class IngestResponse(BaseModel):
    """Response model for ingest endpoint."""

    success: bool
    stats: Dict[str, int]


class StatusResponse(BaseModel):
    """Response model for status endpoint."""

    status: str
    indexed_items: int
    last_updated: Optional[str]
    embedding_model: str
    llm_provider: str
    top_k: int


@app.get("/", tags=["General"])
def root():
    """Root endpoint."""
    return {
        "service": "Data Librarian",
        "version": "0.1.0",
        "description": "AI-powered Databricks Unity Catalog assistant",
    }


@app.get("/health", tags=["General"])
def health():
    """Health check endpoint."""
    lib = get_librarian()
    status = lib.get_status()

    return {
        "status": "healthy",
        "catalog_status": status["status"],
        "indexed_items": status["indexed_items"],
    }


@app.post("/ask", response_model=AskResponse, tags=["Query"])
def ask_question(request: AskRequest):
    """Ask a natural language question about the catalog.

    Args:
        request: Question and optional filters

    Returns:
        Answer with context items
    """
    try:
        lib = get_librarian()

        # Check if indexed
        status = lib.get_status()
        if status["status"] != "ready":
            raise HTTPException(
                status_code=400,
                detail="Catalog not indexed. Call /ingest endpoint first.",
            )

        # Ask question
        result = lib.ask(
            question=request.question, catalog=request.catalog, schema=request.schema
        )

        return AskResponse(
            question=result["question"],
            answer=result["answer"],
            num_results=result["num_results"],
            context_items=result["context_items"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/catalog", tags=["Browse"])
def browse_catalog(catalog: Optional[str] = None, schema: Optional[str] = None):
    """Browse the catalog structure.

    Args:
        catalog: Optional catalog filter
        schema: Optional schema filter

    Returns:
        Catalog structure
    """
    try:
        lib = get_librarian()
        structure = lib.explore(catalog=catalog, schema=schema)
        return {"catalog": structure}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest", response_model=IngestResponse, tags=["Admin"])
def ingest_catalog(request: IngestRequest):
    """Trigger catalog ingestion and indexing.

    Args:
        request: Ingestion options

    Returns:
        Ingestion statistics
    """
    try:
        # Validate settings
        settings.validate()

        # Create index builder
        index_builder = IndexBuilder()

        # Run ingestion
        stats = index_builder.ingest_and_index(force_refresh=request.force_refresh)

        return IngestResponse(success=True, stats=stats)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=StatusResponse, tags=["General"])
def get_status():
    """Get system status and configuration.

    Returns:
        Status information
    """
    try:
        lib = get_librarian()
        status = lib.get_status()

        return StatusResponse(
            status=status["status"],
            indexed_items=status["indexed_items"],
            last_updated=status["last_updated"],
            embedding_model=status["embedding_model"],
            llm_provider=status["llm_provider"],
            top_k=status["top_k"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
