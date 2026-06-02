from companion.api.routes.ingest import IngestFeature, IngestRelationship, IngestRequest


def test_ingest_request_model():
    req = IngestRequest(
        repo_path="/some/repo",
        features=[
            IngestFeature(name="Auth", description="Login flow", domain="auth", confidence=0.9),
            IngestFeature(name="Billing", description="Payments", domain="billing", confidence=0.85),
        ],
        relationships=[
            IngestRelationship(source_id="Auth", target_id="Billing", kind="depends_on"),
        ],
    )
    assert len(req.features) == 2
    assert req.features[0].name == "Auth"
    assert req.relationships[0].kind == "depends_on"


def test_ingest_feature_defaults():
    f = IngestFeature(name="Test")
    assert f.domain == "unknown"
    assert f.confidence == 1.0
    assert f.source_files == []
    assert f.tags == []
