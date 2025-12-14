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
from graphiti_core.extraction_config import ExtractionConfig
from graphiti_core.session_tracking.filter_config import FilterConfig
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
# LLM Resilience Configuration (Story 20)
# ============================================================================


class LLMHealthCheckConfig(BaseModel):
    """LLM health check configuration for proactive availability monitoring.

    The health check system periodically validates LLM connectivity and responsiveness,
    enabling proactive detection of outages before they impact user operations.
    """

    enabled: bool = Field(
        default=True,
        description="Enable periodic LLM health checks"
    )
    interval_seconds: int = Field(
        default=60,
        description="Interval between health checks in seconds"
    )
    on_startup: bool = Field(
        default=True,
        description="Run health check on server startup"
    )
    timeout_seconds: int = Field(
        default=10,
        description="Timeout for health check requests"
    )


class LLMRetryConfig(BaseModel):
    """LLM retry policy configuration with exponential backoff.

    Configures automatic retry behavior for transient LLM failures such as
    rate limits, timeouts, and temporary service unavailability.
    """

    max_attempts: int = Field(
        default=4,
        description="Maximum number of retry attempts (including initial attempt)"
    )
    initial_delay_seconds: float = Field(
        default=5.0,
        description="Initial delay before first retry in seconds"
    )
    max_delay_seconds: float = Field(
        default=120.0,
        description="Maximum delay between retries in seconds"
    )
    exponential_base: float = Field(
        default=2.0,
        description="Base for exponential backoff calculation"
    )
    retry_on_rate_limit: bool = Field(
        default=True,
        description="Retry on rate limit errors (429)"
    )
    retry_on_timeout: bool = Field(
        default=True,
        description="Retry on timeout errors"
    )


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration for LLM failure protection.

    Implements the circuit breaker pattern to prevent cascading failures
    when the LLM service is experiencing issues. After a threshold of
    failures, the circuit opens and fast-fails requests without attempting
    LLM calls, allowing the service to recover.
    """

    enabled: bool = Field(
        default=True,
        description="Enable circuit breaker for LLM calls"
    )
    failure_threshold: int = Field(
        default=5,
        description="Number of consecutive failures before opening circuit"
    )
    recovery_timeout_seconds: int = Field(
        default=300,
        description="Time to wait before attempting recovery (half-open state)"
    )
    half_open_max_calls: int = Field(
        default=3,
        description="Maximum calls allowed in half-open state to test recovery"
    )


class LLMResilienceConfig(BaseModel):
    """Unified LLM resilience configuration.

    Consolidates all LLM resilience features:
    - Health checks for proactive monitoring
    - Retry policies for transient failures
    - Circuit breaker for failure protection
    """

    health_check: LLMHealthCheckConfig = Field(
        default_factory=LLMHealthCheckConfig,
        description="Health check configuration"
    )
    retry: LLMRetryConfig = Field(
        default_factory=LLMRetryConfig,
        description="Retry policy configuration"
    )
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig,
        description="Circuit breaker configuration"
    )


# ============================================================================
# MCP Tools Configuration (Story 20)
# ============================================================================


class MCPToolsBehaviorConfig(BaseModel):
    """MCP tools behavior configuration when LLM is unavailable.

    Defines how MCP tools behave when the underlying LLM service is
    unavailable or degraded. This provides explicit control over
    failure modes for different operational requirements.
    """

    on_llm_unavailable: Literal["FAIL", "STORE_RAW", "QUEUE_RETRY"] = Field(
        default="FAIL",
        description=(
            "Behavior when LLM is unavailable:\n"
            "- FAIL: Immediately return error (best for interactive use)\n"
            "- STORE_RAW: Store data without LLM processing (best for data preservation)\n"
            "- QUEUE_RETRY: Queue for later retry when LLM recovers (best for batch operations)"
        )
    )
    wait_for_completion_default: bool = Field(
        default=True,
        description="Default wait behavior for async operations"
    )
    timeout_seconds: int = Field(
        default=60,
        description="Default timeout for MCP tool operations"
    )


# ============================================================================
# Session Tracking Resilience Configuration (Story 20)
# ============================================================================


class RetryQueueConfig(BaseModel):
    """Retry queue configuration for session tracking resilience.

    Configures the persistent queue used to retry failed session processing
    when the LLM becomes available again. Ensures no session data is lost
    during LLM outages.
    """

    max_retries: int = Field(
        default=5,
        description="Maximum retry attempts per session"
    )
    retry_delays_seconds: list[int] = Field(
        default_factory=lambda: [300, 900, 2700, 7200, 21600],
        description=(
            "Delay in seconds before each retry attempt. "
            "Default: 5m, 15m, 45m, 2h, 6h (progressive backoff)"
        )
    )
    max_queue_size: int = Field(
        default=1000,
        description="Maximum number of sessions in retry queue"
    )
    persist_to_disk: bool = Field(
        default=True,
        description="Persist retry queue to disk for crash recovery"
    )


class SessionNotificationsConfig(BaseModel):
    """Notification configuration for session tracking failures."""

    on_permanent_failure: bool = Field(
        default=True,
        description="Notify on permanent processing failure (after all retries exhausted)"
    )
    notification_method: Literal["log", "webhook", "both"] = Field(
        default="log",
        description="Method for sending failure notifications"
    )
    webhook_url: Optional[str] = Field(
        default=None,
        description="Webhook URL for failure notifications (if method includes webhook)"
    )


class SessionTrackingResilienceConfig(BaseModel):
    """Session tracking resilience configuration.

    Defines how session tracking handles LLM unavailability to ensure
    no session data is lost. The default STORE_RAW_AND_RETRY mode
    stores sessions with raw content and queues them for LLM processing
    when service recovers.
    """

    on_llm_unavailable: Literal["FAIL", "STORE_RAW", "STORE_RAW_AND_RETRY"] = Field(
        default="STORE_RAW_AND_RETRY",
        description=(
            "Behavior when LLM is unavailable during session processing:\n"
            "- FAIL: Skip session (data loss risk)\n"
            "- STORE_RAW: Store raw session content without summarization\n"
            "- STORE_RAW_AND_RETRY: Store raw and queue for later processing (recommended)"
        )
    )
    retry_queue: RetryQueueConfig = Field(
        default_factory=RetryQueueConfig,
        description="Retry queue configuration for failed sessions"
    )
    notifications: SessionNotificationsConfig = Field(
        default_factory=SessionNotificationsConfig,
        description="Notification configuration for session failures"
    )


# ============================================================================
# Summarization Configuration
# ============================================================================


class SummarizationConfig(BaseModel):
    """Configuration for intelligent session summarization features.

    Controls how sessions are analyzed, categorized, and summarized for
    efficient cross-session retrieval. Uses dynamic extraction based on
    activity priority to balance detail preservation with token efficiency.
    """

    template: Optional[str] = Field(
        default=None,
        description="Custom summarization template path. If None, uses dynamic extraction."
    )
    type_detection: Literal["auto", "manual"] = Field(
        default="auto",
        description="Activity detection mode. 'auto' infers from messages, 'manual' requires explicit config."
    )
    extraction_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum priority score to include extraction field"
    )
    include_decisions: bool = Field(
        default=True,
        description="Extract key_decisions (prevents repeated debates)"
    )
    include_errors_resolved: bool = Field(
        default=True,
        description="Extract errors_resolved (debugging continuity)"
    )
    tool_classification_cache: Optional[str] = Field(
        default=None,
        description="Path to tool classification cache. Default: ~/.graphiti/tool_cache.json"
    )

    @field_validator('extraction_threshold')
    def validate_extraction_threshold(cls, v):
        """Enforce extraction_threshold is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("extraction_threshold must be between 0.0 and 1.0")
        return v


# ============================================================================
# Daemon Configuration
# ============================================================================


class DaemonLogRotationConfig(BaseModel):
    """Log rotation configuration for daemon."""

    max_bytes: int = Field(
        default=10485760,  # 10MB
        description="Maximum log file size before rotation"
    )
    backup_count: int = Field(
        default=5,
        description="Number of rotated log files to keep"
    )


class DaemonConfig(BaseModel):
    """Daemon service configuration (Two-Layer Architecture).

    The daemon architecture consists of:
    1. Bootstrap service (always running) - watches config, manages MCP server lifecycle
    2. MCP server (conditional) - only runs when daemon.enabled is true

    See: .claude/implementation/DAEMON_ARCHITECTURE_SPEC_v1.0.md
    """

    enabled: bool = Field(
        default=False,
        description=(
            "Master switch for daemon mode. "
            "false (default) = MCP server stopped, true = MCP server running. "
            "Bootstrap service watches this flag and starts/stops the MCP server accordingly."
        )
    )
    host: str = Field(
        default="127.0.0.1",
        description=(
            "Bind address for HTTP API. "
            "Use 127.0.0.1 (localhost-only, secure). "
            "WARNING: Binding to 0.0.0.0 exposes server to network."
        )
    )
    port: int = Field(
        default=8321,
        description=(
            "HTTP port for MCP API. "
            "8321 is default (mnemonic: 8=graphiti, 321=countdown/launch). "
            "Change if port conflict occurs."
        ),
        ge=1024,
        le=65535
    )
    config_poll_seconds: int = Field(
        default=5,
        description=(
            "How often bootstrap service checks config file for changes (seconds). "
            "Changes take effect within this interval (default: 5s)."
        ),
        ge=1,
        le=300
    )
    pid_file: Optional[str] = Field(
        default=None,
        description=(
            "Path to PID file for daemon process. "
            "null = ~/.graphiti/graphiti-mcp.pid"
        )
    )
    log_file: Optional[str] = Field(
        default=None,
        description=(
            "Path to daemon log file. "
            "null = ~/.graphiti/logs/graphiti-mcp.log"
        )
    )
    log_level: str = Field(
        default="INFO",
        description="Log level for daemon (DEBUG | INFO | WARNING | ERROR | CRITICAL)"
    )
    log_rotation: DaemonLogRotationConfig = Field(
        default_factory=DaemonLogRotationConfig,
        description="Log rotation settings"
    )
    health_check_interval: int = Field(
        default=30,
        description=(
            "Seconds between MCP server health checks by bootstrap service. "
            "If server crashes, bootstrap will restart it within this interval."
        ),
        ge=5,
        le=300
    )

    @field_validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level is a valid Python logging level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of: {', '.join(valid_levels)}")
        return v.upper()


# ============================================================================
# Resilience Configuration (Legacy - kept for backward compatibility)
# ============================================================================


class ResilienceConfig(BaseModel):
    """Resilience and error recovery configuration (legacy).

    Note: This section is maintained for backward compatibility.
    New resilience configuration should use the llm.resilience section
    for LLM-specific settings and session_tracking.resilience for
    session-specific settings.
    """

    max_retries: int = 3
    retry_backoff_base: int = 2
    episode_timeout: int = 60
    health_check_interval: int = 300


# ============================================================================
# Session Tracking Configuration
# ============================================================================


class SessionTrackingConfig(BaseModel):
    """Session tracking configuration for automatic JSONL monitoring.

    Configures the session tracking system that monitors Claude Code session files
    (JSONL format) and automatically indexes them into the Graphiti knowledge graph.
    """

    enabled: bool = Field(
        default=False,
        description="Enable or disable session tracking (opt-in model, disabled by default for security)"
    )
    watch_path: Optional[str] = Field(
        default=None,
        description=(
            "Path to directory containing Claude Code session files. "
            "If None, defaults to ~/.claude/projects/. "
            "Must be an absolute path (native OS format: C:\\ on Windows, / on Unix)."
        )
    )
    store_in_graph: bool = Field(
        default=True,
        description=(
            "Store session summaries in the Graphiti knowledge graph. "
            "If False, sessions are logged but not persisted to Neo4j."
        )
    )
    keep_length_days: Optional[int] = Field(
        default=1,
        description=(
            "Rolling window filter for session discovery in days. "
            "Only sessions modified within the last N days will be indexed. "
            "Set to null to index all sessions (not recommended, may cause bulk LLM costs)."
        )
    )
    filter: FilterConfig = Field(
        default_factory=FilterConfig,
        description=(
            "Filtering configuration for session content. "
            "Controls how messages and tool results are filtered for token reduction. "
            "Default: template-based tool summarization, preserve user/agent messages."
        )
    )
    resilience: SessionTrackingResilienceConfig = Field(
        default_factory=SessionTrackingResilienceConfig,
        description=(
            "Resilience configuration for session tracking. "
            "Defines behavior when LLM is unavailable during session processing."
        )
    )
    summarization: SummarizationConfig = Field(
        default_factory=SummarizationConfig,
        description=(
            "Intelligent session summarization configuration. "
            "Controls activity detection, dynamic extraction, and summary generation."
        )
    )

    # -------------------------------------------------------------------------
    # Global Scope Settings (v2.0)
    # -------------------------------------------------------------------------

    group_id: Optional[str] = Field(
        default=None,
        description=(
            "Global group ID for all indexed sessions. "
            "If None, defaults to '{hostname}__global' at runtime. "
            "All sessions from all projects are indexed to this single group, "
            "enabling cross-project knowledge sharing."
        )
    )
    cross_project_search: bool = Field(
        default=True,
        description=(
            "Allow searching across all project namespaces. "
            "When True, search results include sessions from all indexed projects. "
            "When False, results are filtered to the current project namespace only."
        )
    )
    trusted_namespaces: Optional[list[str]] = Field(
        default=None,
        description=(
            "List of project namespace hashes to trust for cross-project search. "
            "If specified, only sessions from these namespaces are included in search results. "
            "Each namespace must be a valid hexadecimal hash (e.g., 'a1b2c3d4'). "
            "If None, all namespaces are trusted (when cross_project_search is True)."
        )
    )
    include_project_path: bool = Field(
        default=True,
        description=(
            "Include human-readable project path in episode metadata. "
            "When True, the full project directory path is embedded in indexed sessions. "
            "Set to False to redact paths for privacy (only namespace hash is stored)."
        )
    )

    @field_validator('keep_length_days')
    def validate_keep_length_days(cls, v):
        if v is not None and v <= 0:
            raise ValueError("keep_length_days must be > 0 or null")
        return v

    @field_validator('trusted_namespaces')
    def validate_trusted_namespaces(cls, v):
        """Validate that trusted_namespaces contains only valid hex hashes."""
        if v is not None:
            import re
            hex_pattern = re.compile(r'^[a-f0-9]+$', re.IGNORECASE)
            for ns in v:
                if not isinstance(ns, str):
                    raise ValueError(f"Namespace must be a string, got: {type(ns).__name__}")
                if not hex_pattern.match(ns):
                    raise ValueError(
                        f"Invalid namespace format: '{ns}'. "
                        "Must be a hexadecimal hash (e.g., 'a1b2c3d4e5f6')."
                    )
        return v


# ============================================================================
# Root Configuration
# ============================================================================


class GraphitiConfig(BaseModel):
    """Root Graphiti configuration"""

    version: str = "1.0.0"
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    mcp_server: MCPServerConfig = Field(default_factory=MCPServerConfig)
    daemon: DaemonConfig = Field(default_factory=DaemonConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)
    session_tracking: SessionTrackingConfig = Field(default_factory=SessionTrackingConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    llm_resilience: LLMResilienceConfig = Field(default_factory=LLMResilienceConfig)
    mcp_tools: MCPToolsBehaviorConfig = Field(default_factory=MCPToolsBehaviorConfig)

    @classmethod
    def from_file(cls, config_path: str | Path | None = None) -> "GraphitiConfig":
        """Load configuration from JSON file.

        Args:
            config_path: Path to config file. If None, searches in:
                1. ./graphiti.config.json (project root)
                2. ~/.graphiti/graphiti.config.json (global)
                3. Falls back to defaults

        Returns:
            GraphitiConfig instance
        """
        if config_path is None:
            # Search order: project root -> global -> defaults
            global_config_path = Path.home() / ".graphiti" / "graphiti.config.json"
            old_global_config_path = Path.home() / ".claude" / "graphiti.config.json"

            # Migration: Check for old ~/.claude/ location and migrate to ~/.graphiti/
            if old_global_config_path.exists() and not global_config_path.exists():
                try:
                    global_config_path.parent.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(old_global_config_path, global_config_path)
                    logger.info(f"Migrated config from {old_global_config_path} to {global_config_path}")

                    # Create deprecation notice
                    deprecation_notice = old_global_config_path.parent / "graphiti.config.json.deprecated"
                    deprecation_notice.write_text(
                        "This config has been migrated to ~/.graphiti/graphiti.config.json\n"
                        "Graphiti now uses ~/.graphiti/ for global configuration (MCP server independence).\n"
                    )
                except Exception as e:
                    logger.warning(f"Failed to migrate config from {old_global_config_path}: {e}")

            search_paths = [
                Path.cwd() / "graphiti.config.json",
                global_config_path,
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
    def validate_file(cls, config_path: str | Path) -> "ValidationResult":
        """Validate configuration file without loading it.

        Args:
            config_path: Path to config file to validate

        Returns:
            ValidationResult with validation errors/warnings

        Example:
            result = GraphitiConfig.validate_file("./graphiti.config.json")
            if not result.valid:
                print(f"Config has {len(result.errors)} errors")
        """
        from mcp_server.config_validator import ConfigValidator

        validator = ConfigValidator()
        return validator.validate_all(Path(config_path))

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

    def log_effective_config(self) -> None:
        """Log the effective configuration on startup.

        Logs key configuration values for debugging and auditing.
        Sensitive values (API keys, passwords) are masked.
        """
        logger.info("=" * 60)
        logger.info("Graphiti Configuration Summary")
        logger.info("=" * 60)

        # Database
        logger.info(f"Database backend: {self.database.backend}")
        if self.database.backend == "neo4j":
            logger.info(f"  URI: {self.database.neo4j.uri}")
            logger.info(f"  Database: {self.database.neo4j.database}")

        # LLM
        logger.info(f"LLM provider: {self.llm.provider}")
        logger.info(f"  Default model: {self.llm.default_model}")
        logger.info(f"  Small model: {self.llm.small_model}")
        logger.info(f"  Temperature: {self.llm.temperature}")

        # LLM Resilience
        logger.info(f"LLM Resilience:")
        logger.info(f"  Health check enabled: {self.llm_resilience.health_check.enabled}")
        logger.info(f"  Health check interval: {self.llm_resilience.health_check.interval_seconds}s")
        logger.info(f"  Retry max attempts: {self.llm_resilience.retry.max_attempts}")
        logger.info(f"  Circuit breaker enabled: {self.llm_resilience.circuit_breaker.enabled}")
        logger.info(f"  Circuit breaker threshold: {self.llm_resilience.circuit_breaker.failure_threshold}")

        # MCP Tools
        logger.info(f"MCP Tools:")
        logger.info(f"  On LLM unavailable: {self.mcp_tools.on_llm_unavailable}")
        logger.info(f"  Timeout: {self.mcp_tools.timeout_seconds}s")

        # Session Tracking
        logger.info(f"Session Tracking:")
        logger.info(f"  Enabled: {self.session_tracking.enabled}")
        if self.session_tracking.enabled:
            logger.info(f"  Watch path: {self.session_tracking.watch_path or '~/.claude/projects/'}")
            logger.info(f"  On LLM unavailable: {self.session_tracking.resilience.on_llm_unavailable}")

        # Embedder
        logger.info(f"Embedder: {self.embedder.provider} ({self.embedder.model})")

        logger.info("=" * 60)


# ============================================================================
# Global Config Instance
# ============================================================================

# Singleton instance - load once per process
_config_instance: Optional[GraphitiConfig] = None


def get_config(reload: bool = False, force_reload: bool = False) -> GraphitiConfig:
    """Get the global configuration instance.

    Args:
        reload: Force reload from file (deprecated, use force_reload)
        force_reload: Force reload from file

    Returns:
        GraphitiConfig instance
    """
    global _config_instance

    # Support both reload and force_reload for compatibility
    should_reload = reload or force_reload

    if _config_instance is None or should_reload:
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
