"""Microsoft GraphRAG integration for entity knowledge graph indexing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import structlog

logger = structlog.get_logger()


@dataclass
class GraphEntity:
    """An entity extracted from knowledge documents."""
    id: str
    name: str
    entity_type: str
    description: str
    properties: dict = field(default_factory=dict)
    source_document: str = ""


@dataclass
class GraphRelationship:
    """A relationship between two entities."""
    source_id: str
    target_id: str
    relationship_type: str
    weight: float = 1.0
    properties: dict = field(default_factory=dict)


@dataclass
class GraphCommunity:
    """A community of related entities detected via graph algorithms."""
    id: str
    title: str
    summary: str
    entities: list[str] = field(default_factory=list)
    level: int = 0


class GraphRAGIndexer:
    """Indexes OneStream knowledge into a graph structure using Microsoft GraphRAG patterns.

    The indexing pipeline:
    1. Extract entities and relationships from documents via LLM
    2. Build knowledge graph in Neo4j
    3. Detect communities via Leiden algorithm
    4. Generate community summaries for hierarchical search
    """

    def __init__(self, neo4j_uri: str = "", neo4j_user: str = "", neo4j_password: str = "") -> None:
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self._driver = None

        # In-memory store for development
        self.entities: dict[str, GraphEntity] = {}
        self.relationships: list[GraphRelationship] = []
        self.communities: dict[str, GraphCommunity] = {}

    async def extract_entities(self, document: str, doc_id: str) -> list[GraphEntity]:
        """Extract entities from a document.

        In production, this would call an LLM to identify entities.
        For now, uses pattern matching for common OneStream concepts.
        """
        entities = []

        # Pattern: detect BRApi references
        import re
        api_pattern = re.compile(r"BRApi\.\w+(?:\.\w+)*")
        for match in api_pattern.finditer(document):
            api_name = match.group()
            entity_id = f"api_{api_name.replace('.', '_').lower()}"
            if entity_id not in self.entities:
                entity = GraphEntity(
                    id=entity_id,
                    name=api_name,
                    entity_type="API",
                    description=f"OneStream API: {api_name}",
                    source_document=doc_id,
                )
                entities.append(entity)
                self.entities[entity_id] = entity

        # Pattern: detect dimension types
        dim_pattern = re.compile(r"\b(Entity|Account|Scenario|Time|View|Currency|Consolidation)\b")
        for match in dim_pattern.finditer(document):
            dim_name = match.group()
            entity_id = f"dim_{dim_name.lower()}"
            if entity_id not in self.entities:
                entity = GraphEntity(
                    id=entity_id,
                    name=dim_name,
                    entity_type="Dimension",
                    description=f"OneStream dimension: {dim_name}",
                    source_document=doc_id,
                )
                entities.append(entity)
                self.entities[entity_id] = entity

        logger.info("graphrag.entities_extracted", doc_id=doc_id, count=len(entities))
        return entities

    async def build_relationships(self, entities: list[GraphEntity]) -> list[GraphRelationship]:
        """Build relationships between extracted entities."""
        new_rels = []

        # Connect APIs to dimensions they operate on
        api_dim_map = {
            "BRApi.Finance.Members": ["Entity", "Account"],
            "BRApi.Finance.Data": ["Entity", "Account", "Scenario", "Time"],
            "BRApi.Finance.Dim": ["Entity", "Account", "Scenario"],
        }

        for entity in entities:
            if entity.entity_type == "API" and entity.name in api_dim_map:
                for dim_name in api_dim_map[entity.name]:
                    dim_id = f"dim_{dim_name.lower()}"
                    if dim_id in self.entities:
                        rel = GraphRelationship(
                            source_id=entity.id,
                            target_id=dim_id,
                            relationship_type="OPERATES_ON",
                        )
                        new_rels.append(rel)
                        self.relationships.append(rel)

        logger.info("graphrag.relationships_built", count=len(new_rels))
        return new_rels

    async def index_document(self, document: str, doc_id: str) -> dict:
        """Full indexing pipeline for a single document."""
        entities = await self.extract_entities(document, doc_id)
        relationships = await self.build_relationships(entities)

        return {
            "doc_id": doc_id,
            "entities_extracted": len(entities),
            "relationships_built": len(relationships),
            "total_entities": len(self.entities),
            "total_relationships": len(self.relationships),
        }

    def get_entity_neighborhood(self, entity_id: str, depth: int = 1) -> dict:
        """Get an entity and its neighbors up to specified depth."""
        if entity_id not in self.entities:
            return {"error": f"Entity {entity_id} not found"}

        visited = {entity_id}
        current_layer = {entity_id}

        for _ in range(depth):
            next_layer = set()
            for eid in current_layer:
                for rel in self.relationships:
                    if rel.source_id == eid and rel.target_id not in visited:
                        next_layer.add(rel.target_id)
                        visited.add(rel.target_id)
                    elif rel.target_id == eid and rel.source_id not in visited:
                        next_layer.add(rel.source_id)
                        visited.add(rel.source_id)
            current_layer = next_layer

        return {
            "center": entity_id,
            "entities": [self.entities[eid].__dict__ for eid in visited if eid in self.entities],
            "relationships": [
                r.__dict__ for r in self.relationships
                if r.source_id in visited and r.target_id in visited
            ],
        }
