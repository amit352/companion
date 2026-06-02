"""
Knowledge Graph node models (Section 8).
All nodes are persisted to Neo4j via the Neo4jClient.
"""
from typing import Any

from pydantic import BaseModel, Field
from uuid import uuid4


def _uuid() -> str:
    return str(uuid4())


class GraphNode(BaseModel):
    id: str = Field(default_factory=_uuid)
    labels: list[str] = []
    properties: dict[str, Any] = {}


class Feature(BaseModel):
    """Business capability node — the primary organizing unit."""
    id: str = Field(default_factory=_uuid)
    name: str
    description: str
    domain: str
    confidence: float = 1.0
    source_files: list[str] = []
    tags: list[str] = []
    ai_summary: str = ""

    @property
    def neo4j_label(self) -> str:
        return "Feature"


class Service(BaseModel):
    """Backend service node."""
    id: str = Field(default_factory=_uuid)
    name: str
    technology: str = ""
    port: int | None = None
    endpoints: list[str] = []

    @property
    def neo4j_label(self) -> str:
        return "Service"


class API(BaseModel):
    """Exposed HTTP / gRPC endpoint node."""
    id: str = Field(default_factory=_uuid)
    path: str
    method: str
    service_id: str
    request_schema: dict[str, Any] = {}
    response_schema: dict[str, Any] = {}
    auth_required: bool = True

    @property
    def neo4j_label(self) -> str:
        return "API"


class DatabaseTable(BaseModel):
    """Persistence layer node."""
    id: str = Field(default_factory=_uuid)
    name: str
    database: str
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")
    engine: str = "postgresql"

    @property
    def neo4j_label(self) -> str:
        return "DatabaseTable"


class UIComponent(BaseModel):
    """Frontend screen / component node."""
    id: str = Field(default_factory=_uuid)
    name: str
    path: str
    framework: str = "react"
    calls_apis: list[str] = []

    @property
    def neo4j_label(self) -> str:
        return "UIComponent"


class Requirement(BaseModel):
    """Business requirement node — enables traceability (Section 2)."""
    id: str = Field(default_factory=_uuid)
    title: str
    description: str
    source: str = ""  # e.g. "JIRA-123", "PRD-section-4"
    priority: str = "medium"

    @property
    def neo4j_label(self) -> str:
        return "Requirement"
