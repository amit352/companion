from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "feature-graph-dev"

    # Postgres
    postgres_dsn: str = "postgresql://featuregraph:featuregraph-dev@localhost:5432/featuregraph"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Anthropic
    anthropic_api_key: str = ""

    # LLM backend: "direct" = call Anthropic API directly (needs API key)
    #              "claude-code" = features ingested by /fg-analyze Claude Code skill (no key needed)
    llm_backend: str = "direct"

    # Plugin discovery
    plugin_dirs: list[str] = ["plugins/parsers", "plugins/extractors", "plugins/compression", "plugins"]

    # Analysis
    max_concurrent_analyzers: int = 5
    file_batch_size: int = 20

    @property
    def plugin_paths(self) -> list[Path]:
        repo_root = Path(__file__).resolve().parents[1]
        return [repo_root / d for d in self.plugin_dirs]


settings = Settings()
