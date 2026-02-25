"""Document indexing pipeline — embeds and stores knowledge base content."""

from __future__ import annotations

import os
import uuid

import structlog

logger = structlog.get_logger()


async def index_document(
    domain: str,
    title: str,
    content: str,
    metadata: dict | None = None,
    platform_version: str | None = None,
) -> str:
    """
    Index a single document into pgvector and Neo4j.

    Steps:
    1. Generate embedding via sentence-transformers
    2. Store in PostgreSQL kb_embeddings table
    3. Create/update Neo4j knowledge graph node
    """
    doc_id = str(uuid.uuid4())
    logger.info("indexer.index_document", domain=domain, title=title, doc_id=doc_id)

    # 1. Generate embedding
    embedding = await _generate_embedding(content)

    # 2. Store in PostgreSQL
    await _store_in_postgres(doc_id, domain, title, content, metadata or {}, platform_version, embedding)

    # 3. Store in Neo4j
    await _store_in_neo4j(doc_id, domain, title, content, metadata or {})

    return doc_id


async def index_knowledge_base_directory(base_path: str) -> int:
    """Bulk-index all files from the knowledge-base directory."""
    from pathlib import Path

    count = 0
    kb_path = Path(base_path)

    domain_mapping = {
        "api-reference": "api_reference",
        "code-patterns": "code_pattern",
        "deprecated-apis": "deprecated_api",
        "best-practices": "best_practice",
        "migration-patterns": "migration_pattern",
        "dimension-models": "dimension_model",
    }

    for domain_dir, domain_id in domain_mapping.items():
        dir_path = kb_path / domain_dir
        if not dir_path.exists():
            continue

        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in {".md", ".yml", ".yaml", ".vb", ".cs", ".txt"}:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                if len(content.strip()) < 10:
                    continue

                await index_document(
                    domain=domain_id,
                    title=file_path.stem,
                    content=content,
                    metadata={"file_path": str(file_path.relative_to(kb_path)), "format": file_path.suffix},
                )
                count += 1

    logger.info("indexer.bulk_complete", documents_indexed=count)
    return count


async def _generate_embedding(text: str) -> list[float]:
    """Generate embedding using sentence-transformers."""
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text[:8192]).tolist()  # Truncate to model max
    except ImportError:
        logger.warning("sentence_transformers not available, using zero embedding")
        return [0.0] * 1536


async def _store_in_postgres(
    doc_id: str,
    domain: str,
    title: str,
    content: str,
    metadata: dict,
    platform_version: str | None,
    embedding: list[float],
) -> None:
    """Store document and embedding in PostgreSQL."""
    try:
        import asyncpg
        import json

        db_url = os.getenv("DATABASE_URL", "postgresql://ide_agent:localdev@localhost:5432/onestream_ide")
        conn = await asyncpg.connect(dsn=db_url)
        try:
            await conn.execute(
                """
                INSERT INTO kb_embeddings (id, domain, title, content, metadata, platform_version, embedding)
                VALUES ($1::uuid, $2, $3, $4, $5::jsonb, $6, $7::vector)
                ON CONFLICT (id) DO UPDATE SET content = $4, embedding = $7::vector
                """,
                doc_id,
                domain,
                title,
                content,
                json.dumps(metadata),
                platform_version,
                str(embedding),
            )
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("postgres_store_failed", error=str(e))


async def _store_in_neo4j(
    doc_id: str,
    domain: str,
    title: str,
    content: str,
    metadata: dict,
) -> None:
    """Create or update knowledge graph node in Neo4j."""
    try:
        from neo4j import AsyncGraphDatabase

        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        auth = ("neo4j", os.getenv("NEO4J_PASSWORD", "localdev"))
        driver = AsyncGraphDatabase.driver(uri, auth=auth)

        async with driver.session() as session:
            await session.run(
                """
                MERGE (n:KnowledgeNode {id: $id})
                SET n.domain = $domain,
                    n.title = $title,
                    n.content = $content,
                    n.metadata = $metadata
                """,
                id=doc_id,
                domain=domain,
                title=title,
                content=content[:5000],
                metadata=str(metadata),
            )
        await driver.close()
    except Exception as e:
        logger.warning("neo4j_store_failed", error=str(e))
