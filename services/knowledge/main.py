"""Knowledge Service — RAG retrieval, embeddings, and GraphRAG integration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("knowledge.starting")
    # Initialize embedding model, DB connections
    yield
    logger.info("knowledge.shutdown")


app = FastAPI(title="OneStream Knowledge Service", version="0.1.0", lifespan=lifespan)


class SearchRequest(BaseModel):
    query: str
    domain: str | None = None  # api_reference, code_pattern, best_practice, etc.
    platform_version: str | None = None
    top_k: int = 5


class IndexRequest(BaseModel):
    domain: str
    title: str
    content: str
    metadata: dict = {}
    platform_version: str | None = None


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "knowledge"}


@app.post("/api/search")
async def search(request: SearchRequest) -> dict:
    """Hybrid search: vector similarity + keyword + graph traversal."""
    from retriever.hybrid import hybrid_search

    results = await hybrid_search(
        query=request.query,
        domain=request.domain,
        platform_version=request.platform_version,
        top_k=request.top_k,
    )
    return {"results": results, "query": request.query, "count": len(results)}


@app.post("/api/index")
async def index_document(request: IndexRequest) -> dict:
    """Index a document into the knowledge base."""
    from indexer.pipeline import index_document

    doc_id = await index_document(
        domain=request.domain,
        title=request.title,
        content=request.content,
        metadata=request.metadata,
        platform_version=request.platform_version,
    )
    return {"id": doc_id, "status": "indexed"}


@app.get("/api/domains")
async def list_domains() -> dict:
    """List available knowledge domains."""
    return {
        "domains": [
            {"id": "api_reference", "name": "API Reference", "description": "BRApi, HS namespace documentation"},
            {"id": "code_pattern", "name": "Code Patterns", "description": "VB.NET/C# pattern templates"},
            {"id": "deprecated_api", "name": "Deprecated APIs", "description": "Per-version deprecated API registry"},
            {"id": "best_practice", "name": "Best Practices", "description": "OneStream certified patterns"},
            {"id": "migration_pattern", "name": "Migration Patterns", "description": "BPC/HFM → OneStream mappings"},
            {"id": "dimension_model", "name": "Dimension Models", "description": "Standard dimension designs"},
            {"id": "error_pattern", "name": "Error Patterns", "description": "Common errors and resolutions"},
            {"id": "performance", "name": "Performance", "description": "Optimization patterns and anti-patterns"},
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
