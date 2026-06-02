"""
Knowledge Graph relationships (Section 9).

Feature -> uses -> Service
Feature -> exposes -> API
Service -> reads -> DatabaseTable
UIComponent -> calls -> API
Requirement -> validates -> Feature
Feature -> depends_on -> Feature
"""
from pydantic import BaseModel, Field
from uuid import uuid4


def _uuid() -> str:
    return str(uuid4())


class GraphRelationship(BaseModel):
    id: str = Field(default_factory=_uuid)
    source_id: str
    target_id: str
    rel_type: str
    weight: float = 1.0
    metadata: dict = {}


# Typed convenience constructors
def feature_uses_service(feature_id: str, service_id: str) -> GraphRelationship:
    return GraphRelationship(source_id=feature_id, target_id=service_id, rel_type="USES")


def feature_exposes_api(feature_id: str, api_id: str) -> GraphRelationship:
    return GraphRelationship(source_id=feature_id, target_id=api_id, rel_type="EXPOSES")


def service_reads_table(service_id: str, table_id: str) -> GraphRelationship:
    return GraphRelationship(source_id=service_id, target_id=table_id, rel_type="READS")


def ui_calls_api(ui_id: str, api_id: str) -> GraphRelationship:
    return GraphRelationship(source_id=ui_id, target_id=api_id, rel_type="CALLS")


def requirement_validates_feature(req_id: str, feature_id: str) -> GraphRelationship:
    return GraphRelationship(source_id=req_id, target_id=feature_id, rel_type="VALIDATES")


def feature_depends_on(source_id: str, target_id: str, weight: float = 1.0) -> GraphRelationship:
    return GraphRelationship(
        source_id=source_id, target_id=target_id, rel_type="DEPENDS_ON", weight=weight
    )
