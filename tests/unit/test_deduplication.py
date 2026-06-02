from feature_graph.core.deduplication import deduplicate, _token_overlap


def feat(name, domain="auth", confidence=0.8, files=None, tags=None):
    return {
        "name": name,
        "domain": domain,
        "confidence": confidence,
        "source_files": files or [],
        "tags": tags or [],
        "description": f"{name} description",
    }


def test_empty_input():
    assert deduplicate([]) == []


def test_no_duplicates_unchanged():
    features = [feat("Login"), feat("Logout"), feat("Register")]
    result = deduplicate(features)
    assert len(result) == 3


def test_exact_name_duplicate_keeps_higher_confidence():
    features = [feat("Login", confidence=0.7), feat("Login", confidence=0.9)]
    result = deduplicate(features)
    assert len(result) == 1
    assert result[0]["confidence"] >= 0.9


def test_case_insensitive_dedup():
    features = [feat("User Login", confidence=0.9), feat("user login", confidence=0.7)]
    result = deduplicate(features)
    assert len(result) == 1


def test_fuzzy_match_merges():
    features = [
        feat("User Authentication", confidence=0.9),
        feat("User Auth", confidence=0.7),
    ]
    result = deduplicate(features)
    assert len(result) == 1


def test_different_names_not_merged():
    features = [feat("Login Flow"), feat("Payment Processing")]
    result = deduplicate(features)
    assert len(result) == 2


def test_tags_unioned_on_merge():
    features = [
        feat("Login", tags=["jwt", "session"], confidence=0.9),
        feat("Login", tags=["oauth", "jwt"], confidence=0.7),
    ]
    result = deduplicate(features)
    assert len(result) == 1
    assert set(result[0]["tags"]) == {"jwt", "session", "oauth"}


def test_same_source_files_merges():
    files = ["auth/login.py"]
    features = [
        feat("User Login", files=files, confidence=0.8),
        feat("Login Feature", files=files, confidence=0.7),
    ]
    result = deduplicate(features)
    assert len(result) == 1


def test_confidence_boost_on_merge():
    original_confidence = 0.8
    features = [
        feat("Login", confidence=original_confidence),
        feat("Login", confidence=0.6),
    ]
    result = deduplicate(features)
    assert result[0]["confidence"] > original_confidence


def test_token_overlap():
    assert _token_overlap("user authentication flow", "user auth flow") >= 0.5
    assert _token_overlap("user authentication", "user auth") > 0.5  # prefix match
    assert _token_overlap("login", "payment") == 0.0
    assert _token_overlap("", "login") == 0.0
