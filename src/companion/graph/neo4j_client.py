from typing import Any

import structlog
from neo4j import AsyncDriver, AsyncGraphDatabase

from companion.graph.models.nodes import (
    API, DatabaseTable, Feature, Requirement, Service, UIComponent,
)
from companion.graph.models.relationships import GraphRelationship

log = structlog.get_logger()

_NODE_UNION = Feature | Service | API | DatabaseTable | UIComponent | Requirement


def _serialize(value: Any) -> Any:
    """Recursively convert Neo4j Node/Relationship objects to plain dicts."""
    if hasattr(value, "items"):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    return value


def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Neo4j RETURN f gives {"f": Node{...}}.
    If the record has exactly one key whose value is a Node, unwrap it.
    Otherwise serialize all values in place.
    """
    values = list(record.values())
    if len(values) == 1 and hasattr(values[0], "items"):
        return _serialize(values[0])
    return {k: _serialize(v) for k, v in record.items()}


class Neo4jClient:
    """Thin async wrapper around Neo4j driver for graph persistence."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._uri = uri
        self._user = user
        self._password = password
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            self._uri, auth=(self._user, self._password)
        )
        log.info("neo4j_connected", uri=self._uri)

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()

    @property
    def driver(self) -> AsyncDriver:
        if not self._driver:
            raise RuntimeError("Neo4j not connected — call connect() first")
        return self._driver

    async def ensure_schema(self) -> None:
        """Create indexes and constraints once on startup."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Feature) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Service) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:API) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:DatabaseTable) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:UIComponent) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Requirement) REQUIRE n.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (n:Feature) ON (n.domain)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Feature) ON (n.name)",
        ]
        async with self.driver.session() as session:
            for cypher in constraints:
                await session.run(cypher)
        log.info("neo4j_schema_ensured")

    async def upsert_node(self, node: _NODE_UNION) -> None:
        import json
        label = node.neo4j_label
        raw   = node.model_dump(exclude={"neo4j_label"})
        # Neo4j only stores primitives/lists — serialize nested dicts to JSON strings
        props = {
            k: json.dumps(v) if isinstance(v, dict) else v
            for k, v in raw.items()
        }
        cypher = (
            f"MERGE (n:{label} {{id: $id}}) "
            "SET n += $props"
        )
        async with self.driver.session() as session:
            await session.run(cypher, id=node.id, props=props)

    async def upsert_relationship(self, rel: GraphRelationship) -> None:
        cypher = (
            "MATCH (a {id: $source_id}), (b {id: $target_id}) "
            f"MERGE (a)-[r:{rel.rel_type}]->(b) "
            "SET r += $props"
        )
        async with self.driver.session() as session:
            await session.run(
                cypher,
                source_id=rel.source_id,
                target_id=rel.target_id,
                props={"weight": rel.weight, **rel.metadata},
            )

    async def query(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        async with self.driver.session() as session:
            result = await session.run(cypher, **params)
            rows = [dict(record) async for record in result]
            return [_flatten_record(row) for row in rows]

    async def get_feature_subgraph(self, feature_id: str, depth: int = 2) -> dict[str, Any]:
        """Return a feature and all connected nodes up to `depth` hops."""
        cypher = """
        MATCH path = (f:Feature {id: $id})-[*0..%d]-(n)
        RETURN path
        """ % depth
        records = await self.query(cypher, id=feature_id)
        return {"feature_id": feature_id, "depth": depth, "paths": records}

    async def impact_analysis(self, feature_id: str) -> list[dict[str, Any]]:
        """What breaks if this feature changes? (FR-4, UI requirement §11.2)"""
        cypher = """
        MATCH (f:Feature {id: $id})<-[:DEPENDS_ON*1..5]-(dependent)
        RETURN DISTINCT dependent.id as id, dependent.name as name, labels(dependent) as labels
        """
        return await self.query(cypher, id=feature_id)
