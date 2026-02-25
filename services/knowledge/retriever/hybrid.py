"""Hybrid search — combines vector similarity, keyword search, and graph traversal."""

from __future__ import annotations

from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class SearchResult:
    id: str
    domain: str
    title: str
    content: str
    score: float
    source: str  # "vector", "keyword", "graph"
    metadata: dict


async def hybrid_search(
    query: str,
    domain: str | None = None,
    platform_version: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Execute hybrid search across three retrieval methods:
    1. Vector search (pgvector cosine similarity)
    2. Keyword search (PostgreSQL full-text search)
    3. Graph traversal (Neo4j entity relationships)

    Results are merged and re-ranked using reciprocal rank fusion.
    """
    logger.info("hybrid_search", query_length=len(query), domain=domain, top_k=top_k)

    # Run all three searches in parallel
    vector_results = await _vector_search(query, domain, platform_version, top_k * 2)
    keyword_results = await _keyword_search(query, domain, platform_version, top_k * 2)
    graph_results = await _graph_search(query, domain, top_k)

    # Reciprocal rank fusion
    fused = _reciprocal_rank_fusion(
        [vector_results, keyword_results, graph_results],
        weights=[0.5, 0.3, 0.2],
    )

    return fused[:top_k]


async def _vector_search(
    query: str,
    domain: str | None,
    platform_version: str | None,
    top_k: int,
) -> list[dict]:
    """Search using pgvector cosine similarity on embeddings."""
    try:
        import asyncpg

        # Generate query embedding
        embedding = await _get_embedding(query)

        conn = await asyncpg.connect(dsn=_get_db_url())
        try:
            sql = """
                SELECT id, domain, title, content, metadata,
                       1 - (embedding <=> $1::vector) AS score
                FROM kb_embeddings
                WHERE ($2::text IS NULL OR domain = $2)
                  AND ($3::text IS NULL OR platform_version IS NULL OR platform_version = $3)
                ORDER BY embedding <=> $1::vector
                LIMIT $4
            """
            rows = await conn.fetch(sql, str(embedding), domain, platform_version, top_k)
            return [
                {
                    "id": str(row["id"]),
                    "domain": row["domain"],
                    "title": row["title"],
                    "content": row["content"][:500],
                    "score": float(row["score"]),
                    "source": "vector",
                    "metadata": row["metadata"] or {},
                }
                for row in rows
            ]
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("vector_search_failed", error=str(e))
        return []


async def _keyword_search(
    query: str,
    domain: str | None,
    platform_version: str | None,
    top_k: int,
) -> list[dict]:
    """Full-text search using PostgreSQL tsvector."""
    try:
        import asyncpg

        conn = await asyncpg.connect(dsn=_get_db_url())
        try:
            sql = """
                SELECT id, domain, title, content, metadata,
                       ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) AS score
                FROM kb_embeddings
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
                  AND ($2::text IS NULL OR domain = $2)
                  AND ($3::text IS NULL OR platform_version IS NULL OR platform_version = $3)
                ORDER BY score DESC
                LIMIT $4
            """
            rows = await conn.fetch(sql, query, domain, platform_version, top_k)
            return [
                {
                    "id": str(row["id"]),
                    "domain": row["domain"],
                    "title": row["title"],
                    "content": row["content"][:500],
                    "score": float(row["score"]),
                    "source": "keyword",
                    "metadata": row["metadata"] or {},
                }
                for row in rows
            ]
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("keyword_search_failed", error=str(e))
        return []


async def _graph_search(query: str, domain: str | None, top_k: int) -> list[dict]:
    """Traverse Neo4j knowledge graph for entity relationships."""
    try:
        from neo4j import AsyncGraphDatabase
        import os

        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        auth = ("neo4j", os.getenv("NEO4J_PASSWORD", "localdev"))
        driver = AsyncGraphDatabase.driver(uri, auth=auth)

        async with driver.session() as session:
            result = await session.run(
                """
                CALL db.index.fulltext.queryNodes('knowledge_index', $query)
                YIELD node, score
                WHERE ($domain IS NULL OR node.domain = $domain)
                RETURN node.id AS id, node.domain AS domain, node.title AS title,
                       node.content AS content, score, node.metadata AS metadata
                LIMIT $top_k
                """,
                query=query,
                domain=domain,
                top_k=top_k,
            )
            records = [record async for record in result]
            return [
                {
                    "id": str(r["id"]),
                    "domain": r["domain"],
                    "title": r["title"],
                    "content": (r["content"] or "")[:500],
                    "score": float(r["score"]),
                    "source": "graph",
                    "metadata": r["metadata"] or {},
                }
                for r in records
            ]
    except Exception as e:
        logger.warning("graph_search_failed", error=str(e))
        return []


def _reciprocal_rank_fusion(
    result_lists: list[list[dict]],
    weights: list[float],
    k: int = 60,
) -> list[dict]:
    """Merge multiple ranked lists using weighted reciprocal rank fusion."""
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for result_list, weight in zip(result_lists, weights):
        for rank, doc in enumerate(result_list):
            doc_id = doc["id"]
            rrf_score = weight / (k + rank + 1)
            scores[doc_id] = scores.get(doc_id, 0.0) + rrf_score
            if doc_id not in docs:
                docs[doc_id] = doc

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [
        {**docs[doc_id], "score": round(scores[doc_id], 4)}
        for doc_id in sorted_ids
        if doc_id in docs
    ]


async def _get_embedding(text: str) -> list[float]:
    """Generate embedding using sentence-transformers."""
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = model.encode(text).tolist()
        return embedding
    except ImportError:
        # Fallback: return zeros (for development without the model)
        return [0.0] * 1536


def _get_db_url() -> str:
    import os

    return os.getenv("DATABASE_URL", "postgresql://ide_agent:localdev@localhost:5432/onestream_ide")
