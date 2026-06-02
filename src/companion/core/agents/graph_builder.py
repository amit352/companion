"""Agent 5: Persist extracted features and relationships to Neo4j."""
from typing import Any

import structlog

from companion.graph.models.nodes import Feature, Service
from companion.graph.models.relationships import feature_depends_on
from companion.graph.neo4j_client import Neo4jClient

log = structlog.get_logger()


class GraphBuilder:
    def __init__(self, neo4j: Neo4jClient) -> None:
        self.neo4j = neo4j

    async def build(
        self,
        features: dict[str, Any],
        arch_result: dict[str, Any],
    ) -> dict[str, Any]:
        nodes_created = 0
        edges_created = 0
        feature_id_map: dict[str, str] = {}

        for f in features.get("features", []):
            node = Feature(
                name=f["name"],
                description=f.get("description", ""),
                domain=f.get("domain", "unknown"),
                confidence=f.get("confidence", 1.0),
                source_files=f.get("source_files", []),
                tags=f.get("tags", []),
            )
            await self.neo4j.upsert_node(node)
            feature_id_map[f["name"]] = node.id
            nodes_created += 1

        for rel in features.get("relationships", []):
            src_id = feature_id_map.get(rel["source_id"])
            tgt_id = feature_id_map.get(rel["target_id"])
            if src_id and tgt_id:
                edge = feature_depends_on(src_id, tgt_id, weight=rel.get("weight", 1.0))
                await self.neo4j.upsert_relationship(edge)
                edges_created += 1

        log.info("graph_built", nodes=nodes_created, edges=edges_created)
        return {
            "nodes_created": nodes_created,
            "edges_created": edges_created,
            "feature_id_map": feature_id_map,
        }
