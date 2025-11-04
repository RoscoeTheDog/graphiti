"""
Unified Configuration System for Graphiti

Consolidates all configuration sources:
- Database backend selection and connection settings
- LLM provider chain and model settings
- Embedder configuration
- Memory filter settings
- Project-specific preferences
- MCP server settings

Config search order:
1. ./graphiti.config.json (project root)
2. ~/.claude/graphiti.config.json (global)
3. Built-in defaults
4. Environment variable overrides (for sensitive data only)
"""

import json
import os
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Database Configuration
# ============================================================================


class Neo4jConfig(BaseModel):
    """Neo4j database configuration"""

    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password_env: str = "NEO4J_PASSWORD"
    database: str = "neo4j"
    pool_size: int = 50
    connection_timeout: int = 30
    max_connection_lifetime: int = 3600

    @property
    def password(self) -> str:
        """Resolve password from environment"""
        return os.environ.get(self.password_env, "password")


class FalkorDBConfig(BaseModel):
    """FalkorDB database configuration"""

    uri: str = "redis://localhost:6379"
    user: str = "default"
    password_env: str = "FALKORDB_PASSWORD"
    database: str = "graphiti"
    pool_size: int = 50

    @property
    def password(self) -> str:
        """Resolve password from environment"""
        return os.environ.get(self.password_env, "")


class DatabaseConfig(BaseModel):
    """Database backend configuration"""

    backend: Literal["neo4j", "falkordb"] = "neo4j"
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    falkordb: FalkorDBConfig = Field(default_factory=FalkorDBConfig)

    def get_active_config(self) -> Neo4jConfig | FalkorDBConfig:
        """Get the active database configuration based on backend"""
        if self.backend == "neo4j":
            return self.neo4j
        elif self.backend == "falkordb":
            return self.falkordb
        else:
            raise ValueError(f"Unknown database backend: {self.backend}")


# ============================================================================
# LLM Configuration
# ============================================================================


class OpenAIProviderConfig(BaseModel):
    """OpenAI provider configuration"""

    api_key_env: str = "OPENAI_API_KEY"
    base_url: Optional[str] = None
    organization: Optional[str] = None

    @property
    def api_key(self) -> Optional[str]:
        """Resolve API key from environment"""
        return os.environ.get(self.api_key_env)


class AzureOpenAIProviderConfig(BaseModel):
    """Azure OpenAI provider configuration"""

    endpoint_env: str = "AZURE_OPENAI_ENDPOINT"
    api_key_env: str = "AZURE_OPENAI_API_KEY"
    api_version: str = "2025-01-01-preview"
    deployment_name: Optional[str] = None
    use_managed_identity: bool = False

    @property
    def endpoint(self) -> Optional[str]:
        """Resolve endpoint from environment"""
        return os.environ.get(self.endpoint_env)

    @property
    def api_key(self) -> Optional[str]:
        """Resolve API key from environment"""
        return os.environ.get(self.api_key_env)


class AnthropicProviderConfig(BaseModel):
    """Anthropic provider configuration"""

    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: Optional[str] = None

    @property
    def api_key(self) -> Optional[str]:
        """Resolve API key from environment"""
        return os.environ.get(self.api_key_env)


class LLMConfig(BaseModel):
    """LLM provider configuration"""

    provider: Literal["openai", "azure_openai", "anthropic"] = "openai"
    default_model: str = "gpt-4.1-mini"
    small_model: str = "gpt-4.1-nano"
    temperature: float = 0.0
    semaphore_limit: int = 10
    max_retries: int = 3
    timeout: int = 60

    openai: OpenAIProviderConfig = Field(default_factory=OpenAIProviderConfig)
    azure_openai: AzureOpenAIProviderConfig = Field(
        default_factory=AzureOpenAIProviderConfig
    )
    anthropic: AnthropicProviderConfig = Field(default_factory=AnthropicProviderConfig)

    def get_active_provider_config(
        self,
    ) -> OpenAIProviderConfig | AzureOpenAIProviderConfig | AnthropicProviderConfig:
        """Get the active provider configuration"""
        if self.provider == "openai":
            return self.openai
        elif self.provider == "azure_openai":
            return self.azure_openai
        elif self.provider == "anthropic":
            return self.anthropic
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")


# ============================================================================
# Embedder Configuration
# ============================================================================


class EmbedderOpenAIConfig(BaseModel):
    """OpenAI embedder configuration"""

    api_key_env: str = "OPENAI_API_KEY"

    @property
    def api_key(self) -> Optional[str]:
        """Resolve API key from environment"""
        return os.environ.get(self.api_key_env)


class EmbedderAzureOpenAIConfig(BaseModel):
    """Azure OpenAI embedder configuration"""

    endpoint_env: str = "AZURE_OPENAI_EMBEDDING_ENDPOINT"
    api_key_env: str = "AZURE_OPENAI_EMBEDDING_API_KEY"
    api_version: str = "2023-05-15"
    deployment_name: Optional[str] = None
    use_managed_identity: bool = False

    @property
    def endpoint(self) -> Optional[str]:
        """Resolve endpoint from environment"""
        return os.environ.get(self.endpoint_env)

    @property
    def api_key(self) -> Optional[str]:
        """Resolve API key from environment"""
        return os.environ.get(self.api_key_env)


class EmbedderConfig(BaseModel):
    """Embedder configuration"""

    provider: Literal["openai", "azure_openai"] = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    batch_size: int = 100

    openai: EmbedderOpenAIConfig = Field(default_factory=EmbedderOpenAIConfig)
    azure_openai: EmbedderAzureOpenAIConfig = Field(
        default_factory=EmbedderAzureOpenAIConfig
    )

    def get_active_config(self) -> EmbedderOpenAIConfig | EmbedderAzureOpenAIConfig:
        """Get the active embedder configuration"""
        if self.provider == "openai":
            return self.openai
        elif self.provider == "azure_openai":
            return self.azure_openai
        else:
            raise ValueError(f"Unknown embedder provider: {self.provider}")


# ============================================================================
# Memory Filter Configuration
# ============================================================================


class LLMFilterProviderConfig(BaseModel):
    """Configuration for a single LLM filter provider"""

    name: Literal["openai", "anthropic"]
    model: str
    api_key_env: str
    temperature: float = 0.0
    max_tokens: int = 200
    enabled: bool = True
    priority: int = 1

    @property
    def api_key(self) -> Optional[str]:
        """Resolve API key from environment"""
        return os.environ.get(self.api_key_env)


class FilterSessionConfig(BaseModel):
    """Session management configuration for filter"""

    max_context_tokens: int = 5000
    auto_cleanup: bool = True
    session_timeout_minutes: int = 60


class FilterCategoriesConfig(BaseModel):
    """Filter categories configuration"""

    store: list[str] = Field(
        default_factory=lambda: [
            "env-quirk",
            "user-pref",
            "external-api",
            "historical-context",
            "cross-project",
            "workaround",
        ]
    )
    skip: list[str] = Field(
        default_factory=lambda: [
            "bug-in-code",
            "config-in-repo",
            "docs-added",
            "first-success",
        ]
    )


class LLMFilterConfig(BaseModel):
    """LLM-based filter configuration"""

    providers: list[LLMFilterProviderConfig] = Field(default_factory=list)
    session: FilterSessionConfig = Field(default_factory=FilterSessionConfig)
    categories: FilterCategoriesConfig = Field(default_factory=FilterCategoriesConfig)

    def get_sorted_providers(self) -> list[LLMFilterProviderConfig]:
        """Get providers sorted by priority (lower number = higher priority)"""
        return sorted(
            [p for p in self.providers if p.enabled], key=lambda p: p.priority
        )


class RuleBasedFilterConfig(BaseModel):
    """Rule-based filter configuration (future implementation)"""

    enabled: bool = False
    rules: list[dict[str, Any]] = Field(default_factory=list)


class MemoryFilterConfig(BaseModel):
    """Memory filter configuration"""

    enabled: bool = True
    mode: Literal["llm", "rule_based", "hybrid"] = "llm"

    llm_filter: LLMFilterConfig = Field(default_factory=LLMFilterConfig)
    rule_based_filter: RuleBasedFilterConfig = Field(
        default_factory=RuleBasedFilterConfig
    )


# ============================================================================
# Project Configuration
# ============================================================================


class ProjectConfig(BaseModel):
    """Project-specific configuration"""

    default_group_id: Optional[str] = None
    namespace: Optional[str] = None
    enable_entity_types: bool = True
    custom_entity_types: list[str] = Field(
        default_factory=lambda: ["Requirement", "Preference", "Procedure"]
    )
    max_reflexion_iterations: int = 3


# ============================================================================
# Search Configuration
# ============================================================================


class SearchConfig(BaseModel):
    """Search configuration"""

    default_max_nodes: int = 10
    default_max_facts: int = 10
    default_method: Literal["hybrid_rrf", "hybrid_node_distance", "vector", "text"] = (
        "hybrid_rrf"
    )
    vector_weight: float = 0.7
    text_weight: float = 0.3


# ============================================================================
# Logging Configuration
# ============================================================================


class LoggingConfig(BaseModel):
    """Logging configuration"""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_filter_decisions: bool = True
    log_llm_calls: bool = False
    log_database_queries: bool = False
    log_file: Optional[str] = None
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# ============================================================================
# Performance Configuration
# ============================================================================


class PerformanceConfig(BaseModel):
    """Performance tuning configuration"""

    use_parallel_runtime: bool = True
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600


# ============================================================================
# MCP Server Configuration
# ============================================================================


class MCPServerConfig(BaseModel):
    """MCP server configuration"""

    host: Optional[str] = None
    port: Optional[int] = None
    enable_cors: bool = False
    allowed_origins: list[str] = Field(default_factory=list)


# ============================================================================
# Root Configuration
# ============================================================================


class GraphitiConfig(BaseModel):
    """Root Graphiti configuration"""

    version: str = "1.0.0"
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
    memory_filter: MemoryFilterConfig = Field(default_factory=MemoryFilterConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    mcp_server: MCPServerConfig = Field(default_factory=MCPServerConfig)

    @classmethod
    def from_file(cls, config_path: str | Path | None = None) -> "GraphitiConfig":
        """Load configuration from JSON file.

        Args:
            config_path: Path to config file. If None, searches in:
                1. ./graphiti.config.json (project root)
                2. ~/.claude/graphiti.config.json (global)
                3. Falls back to defaults

        Returns:
            GraphitiConfig instance
        """
        if config_path is None:
            # Search order: project root -> global -> defaults
            search_paths = [
                Path.cwd() / "graphiti.config.json",
                Path.home() / ".claude" / "graphiti.config.json",
            ]

            for path in search_paths:
                if path.exists():
                    config_path = path
                    logger.info(f"Loading config from: {config_path}")
                    break
            else:
                logger.warning("No config file found, using defaults")
                return cls._default_config()

        config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return cls._default_config()

        try:
            with open(config_path, "r") as f:
                data = json.load(f)
            config = cls.model_validate(data)
            logger.info(f"Successfully loaded config from: {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            logger.warning("Falling back to default configuration")
            return cls._default_config()

    @classmethod
    def _default_config(cls) -> "GraphitiConfig":
        """Return default configuration"""
        return cls(
            database=DatabaseConfig(
                backend="neo4j",
                neo4j=Neo4jConfig(),
                falkordb=FalkorDBConfig(),
            ),
            llm=LLMConfig(
                provider="openai",
                default_model="gpt-4.1-mini",
                small_model="gpt-4.1-nano",
            ),
            embedder=EmbedderConfig(provider="openai", model="text-embedding-3-small"),
            memory_filter=MemoryFilterConfig(
                enabled=True,
                mode="llm",
                llm_filter=LLMFilterConfig(
                    providers=[
                        LLMFilterProviderConfig(
                            name="openai",
                            model="gpt-4o-mini",
                            api_key_env="OPENAI_API_KEY",
                            priority=1,
                        ),
                        LLMFilterProviderConfig(
                            name="anthropic",
                            model="claude-haiku-3-5-20241022",
                            api_key_env="ANTHROPIC_API_KEY",
                            priority=2,
                        ),
                    ]
                ),
            ),
        )

    def apply_env_overrides(self) -> None:
        """Apply environment variable overrides for specific settings.

        This allows sensitive data (passwords, API keys) to remain in env vars
        while structure/preferences live in the config file.
        """
        # Model overrides
        if model_name := os.environ.get("MODEL_NAME"):
            self.llm.default_model = model_name
            logger.info(f"Override: LLM default model = {model_name}")

        if small_model := os.environ.get("SMALL_MODEL_NAME"):
            self.llm.small_model = small_model
            logger.info(f"Override: LLM small model = {small_model}")

        if embedder_model := os.environ.get("EMBEDDER_MODEL_NAME"):
            self.embedder.model = embedder_model
            logger.info(f"Override: Embedder model = {embedder_model}")

        # Temperature override
        if temp := os.environ.get("LLM_TEMPERATURE"):
            try:
                self.llm.temperature = float(temp)
                logger.info(f"Override: LLM temperature = {temp}")
            except ValueError:
                logger.warning(f"Invalid LLM_TEMPERATURE value: {temp}")

        # Semaphore limit override
        if semaphore := os.environ.get("SEMAPHORE_LIMIT"):
            try:
                self.llm.semaphore_limit = int(semaphore)
                logger.info(f"Override: Semaphore limit = {semaphore}")
            except ValueError:
                logger.warning(f"Invalid SEMAPHORE_LIMIT value: {semaphore}")

        # Database backend override
        if db_backend := os.environ.get("GRAPHITI_DB_BACKEND"):
            if db_backend in ["neo4j", "falkordb"]:
                self.database.backend = db_backend
                logger.info(f"Override: Database backend = {db_backend}")
            else:
                logger.warning(f"Invalid GRAPHITI_DB_BACKEND value: {db_backend}")

        # Group ID override
        if group_id := os.environ.get("GROUP_ID"):
            self.project.default_group_id = group_id
            logger.info(f"Override: Default group ID = {group_id}")

    def to_file(self, config_path: str | Path) -> None:
        """Save configuration to JSON file.

        Args:
            config_path: Path to save config file
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(
                self.model_dump(exclude_none=False, mode="json"),
                f,
                indent=2,
            )

        logger.info(f"Saved config to: {config_path}")


# ============================================================================
# Global Config Instance
# ============================================================================

# Singleton instance - load once per process
_config_instance: Optional[GraphitiConfig] = None


def get_config(reload: bool = False) -> GraphitiConfig:
    """Get the global configuration instance.

    Args:
        reload: Force reload from file

    Returns:
        GraphitiConfig instance
    """
    global _config_instance

    if _config_instance is None or reload:
        _config_instance = GraphitiConfig.from_file()
        _config_instance.apply_env_overrides()

    return _config_instance


def set_config(config: GraphitiConfig) -> None:
    """Set the global configuration instance (for testing).

    Args:
        config: GraphitiConfig instance to use
    """
    global _config_instance
    _config_instance = config
