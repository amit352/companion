from companion.graph.models.nodes import Feature, Service, API, DatabaseTable, Requirement
from companion.graph.models.relationships import (
    feature_depends_on, feature_uses_service, service_reads_table,
)


def test_feature_node_defaults():
    f = Feature(name="Auth", description="Authentication", domain="security")
    assert f.id  # auto-generated UUID
    assert f.neo4j_label == "Feature"
    assert f.confidence == 1.0
    assert f.tags == []


def test_feature_depends_on_relationship():
    rel = feature_depends_on("feat-a", "feat-b", weight=0.8)
    assert rel.source_id == "feat-a"
    assert rel.target_id == "feat-b"
    assert rel.rel_type == "DEPENDS_ON"
    assert rel.weight == 0.8


def test_all_node_types_have_labels():
    assert Service(name="auth-svc", technology="python").neo4j_label == "Service"
    assert API(path="/login", method="POST", service_id="svc-1").neo4j_label == "API"
    assert DatabaseTable(name="users", database="postgres").neo4j_label == "DatabaseTable"
    assert Requirement(title="FR-1", description="Plugin registration").neo4j_label == "Requirement"


def test_relationship_unique_ids():
    r1 = feature_uses_service("f1", "s1")
    r2 = feature_uses_service("f1", "s1")
    assert r1.id != r2.id  # each relationship gets a unique ID
