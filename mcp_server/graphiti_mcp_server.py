#!/usr/bin/env python3
"""
Graphiti MCP Server - Exposes Graphiti functionality through the Model Context Protocol (MCP)
"""

import argparse
import asyncio
import json
import logging
import logging.handlers
import os
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from typing_extensions import TypedDict

try:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    AZURE_IDENTITY_AVAILABLE = True
except ImportError:
    AZURE_IDENTITY_AVAILABLE = False

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field

from graphiti_core import Graphiti
from graphiti_core.edges import EntityEdge
from graphiti_core.embedder.azure_openai import AzureOpenAIEmbedderClient
from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client import LLMClient
from graphiti_core.llm_client.azure_openai_client import AzureOpenAILLMClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.nodes import EpisodeType, EpisodicNode
from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_NODE_DISTANCE,
    NODE_HYBRID_SEARCH_RRF,
)
from graphiti_core.search.search_filters import SearchFilters
from graphiti_core.utils.maintenance.graph_data_operations import clear_data
from mcp_server.export_helpers import _resolve_path_pattern, _scan_for_credentials, _resolve_absolute_path, _normalize_msys_path
from mcp_server.unified_config import get_config

from mcp_server.responses import (
    MCPResponse,
    SuccessResponse,
    DegradedResponse,
    QueuedResponse,
    ErrorResponse as MCPErrorResponse,
    DegradationReason,
    create_success,
    create_degraded,
    create_queued,
    create_error,
    create_llm_unavailable_error,
    create_llm_auth_error,
    create_llm_rate_limit_error,
    create_database_error,
    create_timeout_error,
    format_response,
    ErrorCategory,
)
# Session tracking imports
from graphiti_core.session_tracking.path_resolver import ClaudePathResolver
from graphiti_core.session_tracking.session_manager import SessionManager
from graphiti_core.session_tracking.filter import SessionFilter
from graphiti_core.session_tracking.indexer import SessionIndexer
from graphiti_core.session_tracking.prompts import DEFAULT_TEMPLATES
from mcp_server.manual_sync import session_tracking_sync_history as _session_tracking_sync_history

# Session tracking resilience imports (Story 19)
from graphiti_core.session_tracking.resilient_indexer import (
    ResilientSessionIndexer,
    ResilientIndexerConfig,
    OnLLMUnavailable,
)
from graphiti_core.session_tracking.retry_queue import FailedEpisode, RetryQueue
from graphiti_core.session_tracking.status import (
    SessionTrackingHealth,
    SessionTrackingStatusAggregator,
    DegradationLevel,
    ServiceStatus,
)

load_dotenv()

# Load unified config instance (will replace local GraphitiConfig)
unified_config = get_config()


DEFAULT_LLM_MODEL = 'gpt-4.1-mini'
SMALL_LLM_MODEL = 'gpt-4.1-nano'
DEFAULT_EMBEDDER_MODEL = 'text-embedding-3-small'

# Semaphore limit for concurrent Graphiti operations.
# Decrease this if you're experiencing 429 rate limit errors from your LLM provider.
# Increase if you have high rate limits.
SEMAPHORE_LIMIT = int(os.getenv('SEMAPHORE_LIMIT', 10))

# Global session manager instance (initialized in initialize_server)
session_manager: SessionManager | None = None

# Global inactivity checker task (initialized in initialize_session_tracking)
_inactivity_checker_task: asyncio.Task | None = None

# Runtime session tracking state (per-session overrides)
# Maps session_id -> enabled (True/False)
runtime_session_tracking_state: dict[str, bool] = {}

# Session tracking resilience components (Story 19)
resilient_indexer: ResilientSessionIndexer | None = None
status_aggregator: SessionTrackingStatusAggregator | None = None


class Requirement(BaseModel):
    """A Requirement represents a specific need, feature, or functionality that a product or service must fulfill.

    Always ensure an edge is created between the requirement and the project it belongs to, and clearly indicate on the
    edge that the requirement is a requirement.

    Instructions for identifying and extracting requirements:
    1. Look for explicit statements of needs or necessities ("We need X", "X is required", "X must have Y")
    2. Identify functional specifications that describe what the system should do
    3. Pay attention to non-functional requirements like performance, security, or usability criteria
    4. Extract constraints or limitations that must be adhered to
    5. Focus on clear, specific, and measurable requirements rather than vague wishes
    6. Capture the priority or importance if mentioned ("critical", "high priority", etc.)
    7. Include any dependencies between requirements when explicitly stated
    8. Preserve the original intent and scope of the requirement
    9. Categorize requirements appropriately based on their domain or function
    """

    project_name: str = Field(
        ...,
        description='The name of the project to which the requirement belongs.',
    )
    description: str = Field(
        ...,
        description='Description of the requirement. Only use information mentioned in the context to write this description.',
    )


class Preference(BaseModel):
    """A Preference represents a user's expressed like, dislike, or preference for something.

    Instructions for identifying and extracting preferences:
    1. Look for explicit statements of preference such as "I like/love/enjoy/prefer X" or "I don't like/hate/dislike X"
    2. Pay attention to comparative statements ("I prefer X over Y")
    3. Consider the emotional tone when users mention certain topics
    4. Extract only preferences that are clearly expressed, not assumptions
    5. Categorize the preference appropriately based on its domain (food, music, brands, etc.)
    6. Include relevant qualifiers (e.g., "likes spicy food" rather than just "likes food")
    7. Only extract preferences directly stated by the user, not preferences of others they mention
    8. Provide a concise but specific description that captures the nature of the preference
    """

    category: str = Field(
        ...,
        description="The category of the preference. (e.g., 'Brands', 'Food', 'Music')",
    )
    description: str = Field(
        ...,
        description='Brief description of the preference. Only use information mentioned in the context to write this description.',
    )


class Procedure(BaseModel):
    """A Procedure informing the agent what actions to take or how to perform in certain scenarios. Procedures are typically composed of several steps.

    Instructions for identifying and extracting procedures:
    1. Look for sequential instructions or steps ("First do X, then do Y")
    2. Identify explicit directives or commands ("Always do X when Y happens")
    3. Pay attention to conditional statements ("If X occurs, then do Y")
    4. Extract procedures that have clear beginning and end points
    5. Focus on actionable instructions rather than general information
    6. Preserve the original sequence and dependencies between steps
    7. Include any specified conditions or triggers for the procedure
    8. Capture any stated purpose or goal of the procedure
    9. Summarize complex procedures while maintaining critical details
    """

    description: str = Field(
        ...,
        description='Brief description of the procedure. Only use information mentioned in the context to write this description.',
    )


ENTITY_TYPES: dict[str, BaseModel] = {
    'Requirement': Requirement,  # type: ignore
    'Preference': Preference,  # type: ignore
    'Procedure': Procedure,  # type: ignore
}


# Type definitions for API responses
class ErrorResponse(TypedDict):
    error: str


class SuccessResponse(TypedDict):
    message: str


class NodeResult(TypedDict):
    uuid: str
    name: str
    summary: str
    labels: list[str]
    group_id: str
    created_at: str
    attributes: dict[str, Any]


class NodeSearchResponse(TypedDict):
    message: str
    nodes: list[NodeResult]


class FactSearchResponse(TypedDict):
    message: str
    facts: list[dict[str, Any]]


class EpisodeSearchResponse(TypedDict):
    message: str
    episodes: list[dict[str, Any]]


class StatusResponse(TypedDict):
    status: str
    message: str


class HealthCheckResponse(TypedDict):
    status: str
    database_connected: bool
    last_successful_connection: str | None
    consecutive_failures: int
    error_details: str | None


def create_azure_credential_token_provider() -> Callable[[], str]:
    if not AZURE_IDENTITY_AVAILABLE:
        raise ImportError(
            "Azure identity package not installed. "
            "Install with: pip install azure-identity"
        )
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential, 'https://cognitiveservices.azure.com/.default'
    )
    return token_provider


# Server configuration classes
# The configuration system has a hierarchy:
# - GraphitiConfig is the top-level configuration
#   - LLMConfig handles all OpenAI/LLM related settings
#   - EmbedderConfig manages embedding settings
#   - Neo4jConfig manages database connection details
#   - Various other settings like group_id and feature flags
# Configuration values are loaded from:
# 1. Default values in the class definitions
# 2. Environment variables (loaded via load_dotenv())
# 3. Command line arguments (which override environment variables)
class GraphitiLLMConfig(BaseModel):
    """Configuration for the LLM client.

    Centralizes all LLM-specific configuration parameters including API keys and model selection.
    """

    api_key: str | None = None
    model: str = DEFAULT_LLM_MODEL
    small_model: str = SMALL_LLM_MODEL
    temperature: float = 0.0
    azure_openai_endpoint: str | None = None
    azure_openai_deployment_name: str | None = None
    azure_openai_api_version: str | None = None
    azure_openai_use_managed_identity: bool = False

    @classmethod
    def from_env(cls) -> 'GraphitiLLMConfig':
        """Create LLM configuration from environment variables."""
        # Get model from environment, or use default if not set or empty
        model_env = os.environ.get('MODEL_NAME', '')
        model = model_env if model_env.strip() else DEFAULT_LLM_MODEL

        # Get small_model from environment, or use default if not set or empty
        small_model_env = os.environ.get('SMALL_MODEL_NAME', '')
        small_model = small_model_env if small_model_env.strip() else SMALL_LLM_MODEL

        azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT', None)
        azure_openai_api_version = os.environ.get('AZURE_OPENAI_API_VERSION', None)
        azure_openai_deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', None)
        azure_openai_use_managed_identity = (
            os.environ.get('AZURE_OPENAI_USE_MANAGED_IDENTITY', 'false').lower() == 'true'
        )

        if azure_openai_endpoint is None:
            # Setup for OpenAI API
            # Log if empty model was provided
            if model_env == '':
                logger.debug(
                    f'MODEL_NAME environment variable not set, using default: {DEFAULT_LLM_MODEL}'
                )
            elif not model_env.strip():
                logger.warning(
                    f'Empty MODEL_NAME environment variable, using default: {DEFAULT_LLM_MODEL}'
                )

            return cls(
                api_key=os.environ.get('OPENAI_API_KEY'),
                model=model,
                small_model=small_model,
                temperature=float(os.environ.get('LLM_TEMPERATURE', '0.0')),
            )
        else:
            # Setup for Azure OpenAI API
            # Log if empty deployment name was provided
            if azure_openai_deployment_name is None:
                logger.error('AZURE_OPENAI_DEPLOYMENT_NAME environment variable not set')

                raise ValueError('AZURE_OPENAI_DEPLOYMENT_NAME environment variable not set')
            if not azure_openai_use_managed_identity:
                # api key
                api_key = os.environ.get('OPENAI_API_KEY', None)
            else:
                # Managed identity
                api_key = None

            return cls(
                azure_openai_use_managed_identity=azure_openai_use_managed_identity,
                azure_openai_endpoint=azure_openai_endpoint,
                api_key=api_key,
                azure_openai_api_version=azure_openai_api_version,
                azure_openai_deployment_name=azure_openai_deployment_name,
                model=model,
                small_model=small_model,
                temperature=float(os.environ.get('LLM_TEMPERATURE', '0.0')),
            )

    @classmethod
    def from_cli_and_env(cls, args: argparse.Namespace) -> 'GraphitiLLMConfig':
        """Create LLM configuration from CLI arguments, falling back to environment variables."""
        # Start with environment-based config
        config = cls.from_env()

        # CLI arguments override environment variables when provided
        if hasattr(args, 'model') and args.model:
            # Only use CLI model if it's not empty
            if args.model.strip():
                config.model = args.model
            else:
                # Log that empty model was provided and default is used
                logger.warning(f'Empty model name provided, using default: {DEFAULT_LLM_MODEL}')

        if hasattr(args, 'small_model') and args.small_model:
            if args.small_model.strip():
                config.small_model = args.small_model
            else:
                logger.warning(f'Empty small_model name provided, using default: {SMALL_LLM_MODEL}')

        if hasattr(args, 'temperature') and args.temperature is not None:
            config.temperature = args.temperature

        return config

    def create_client(self) -> LLMClient:
        """Create an LLM client based on this configuration.

        Returns:
            LLMClient instance
        """

        if self.azure_openai_endpoint is not None:
            # Azure OpenAI API setup
            if self.azure_openai_use_managed_identity:
                # Use managed identity for authentication
                token_provider = create_azure_credential_token_provider()
                return AzureOpenAILLMClient(
                    azure_client=AsyncAzureOpenAI(
                        azure_endpoint=self.azure_openai_endpoint,
                        azure_deployment=self.azure_openai_deployment_name,
                        api_version=self.azure_openai_api_version,
                        azure_ad_token_provider=token_provider,
                    ),
                    config=LLMConfig(
                        api_key=self.api_key,
                        model=self.model,
                        small_model=self.small_model,
                        temperature=self.temperature,
                    ),
                )
            elif self.api_key:
                # Use API key for authentication
                return AzureOpenAILLMClient(
                    azure_client=AsyncAzureOpenAI(
                        azure_endpoint=self.azure_openai_endpoint,
                        azure_deployment=self.azure_openai_deployment_name,
                        api_version=self.azure_openai_api_version,
                        api_key=self.api_key,
                    ),
                    config=LLMConfig(
                        api_key=self.api_key,
                        model=self.model,
                        small_model=self.small_model,
                        temperature=self.temperature,
                    ),
                )
            else:
                raise ValueError('OPENAI_API_KEY must be set when using Azure OpenAI API')

        if not self.api_key:
            raise ValueError('OPENAI_API_KEY must be set when using OpenAI API')

        llm_client_config = LLMConfig(
            api_key=self.api_key, model=self.model, small_model=self.small_model
        )

        # Set temperature
        llm_client_config.temperature = self.temperature

        return OpenAIClient(config=llm_client_config)


class GraphitiEmbedderConfig(BaseModel):
    """Configuration for the embedder client.

    Centralizes all embedding-related configuration parameters.
    """

    model: str = DEFAULT_EMBEDDER_MODEL
    api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment_name: str | None = None
    azure_openai_api_version: str | None = None
    azure_openai_use_managed_identity: bool = False

    @classmethod
    def from_env(cls) -> 'GraphitiEmbedderConfig':
        """Create embedder configuration from environment variables."""

        # Get model from environment, or use default if not set or empty
        model_env = os.environ.get('EMBEDDER_MODEL_NAME', '')
        model = model_env if model_env.strip() else DEFAULT_EMBEDDER_MODEL

        azure_openai_endpoint = os.environ.get('AZURE_OPENAI_EMBEDDING_ENDPOINT', None)
        azure_openai_api_version = os.environ.get('AZURE_OPENAI_EMBEDDING_API_VERSION', None)
        azure_openai_deployment_name = os.environ.get(
            'AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME', None
        )
        azure_openai_use_managed_identity = (
            os.environ.get('AZURE_OPENAI_USE_MANAGED_IDENTITY', 'false').lower() == 'true'
        )
        if azure_openai_endpoint is not None:
            # Setup for Azure OpenAI API
            # Log if empty deployment name was provided
            azure_openai_deployment_name = os.environ.get(
                'AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME', None
            )
            if azure_openai_deployment_name is None:
                logger.error('AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME environment variable not set')

                raise ValueError(
                    'AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME environment variable not set'
                )

            if not azure_openai_use_managed_identity:
                # api key
                api_key = os.environ.get('AZURE_OPENAI_EMBEDDING_API_KEY', None) or os.environ.get(
                    'OPENAI_API_KEY', None
                )
            else:
                # Managed identity
                api_key = None

            return cls(
                azure_openai_use_managed_identity=azure_openai_use_managed_identity,
                azure_openai_endpoint=azure_openai_endpoint,
                api_key=api_key,
                azure_openai_api_version=azure_openai_api_version,
                azure_openai_deployment_name=azure_openai_deployment_name,
            )
        else:
            return cls(
                model=model,
                api_key=os.environ.get('OPENAI_API_KEY'),
            )

    def create_client(self) -> EmbedderClient | None:
        if self.azure_openai_endpoint is not None:
            # Azure OpenAI API setup
            if self.azure_openai_use_managed_identity:
                # Use managed identity for authentication
                token_provider = create_azure_credential_token_provider()
                return AzureOpenAIEmbedderClient(
                    azure_client=AsyncAzureOpenAI(
                        azure_endpoint=self.azure_openai_endpoint,
                        azure_deployment=self.azure_openai_deployment_name,
                        api_version=self.azure_openai_api_version,
                        azure_ad_token_provider=token_provider,
                    ),
                    model=self.model,
                )
            elif self.api_key:
                # Use API key for authentication
                return AzureOpenAIEmbedderClient(
                    azure_client=AsyncAzureOpenAI(
                        azure_endpoint=self.azure_openai_endpoint,
                        azure_deployment=self.azure_openai_deployment_name,
                        api_version=self.azure_openai_api_version,
                        api_key=self.api_key,
                    ),
                    model=self.model,
                )
            else:
                logger.error('OPENAI_API_KEY must be set when using Azure OpenAI API')
                return None
        else:
            # OpenAI API setup
            if not self.api_key:
                return None

            embedder_config = OpenAIEmbedderConfig(api_key=self.api_key, embedding_model=self.model)

            return OpenAIEmbedder(config=embedder_config)


class Neo4jConfig(BaseModel):
    """Configuration for Neo4j database connection."""

    uri: str = 'bolt://localhost:7687'
    user: str = 'neo4j'
    password: str = 'password'

    @classmethod
    def from_env(cls) -> 'Neo4jConfig':
        """Create Neo4j configuration from environment variables."""
        return cls(
            uri=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'),
            user=os.environ.get('NEO4J_USER', 'neo4j'),
            password=os.environ.get('NEO4J_PASSWORD', 'password'),
        )


class GraphitiConfig(BaseModel):
    """Configuration for Graphiti client.

    Centralizes all configuration parameters for the Graphiti client.
    """

    llm: GraphitiLLMConfig = Field(default_factory=GraphitiLLMConfig)
    embedder: GraphitiEmbedderConfig = Field(default_factory=GraphitiEmbedderConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    group_id: str | None = None
    use_custom_entities: bool = False
    destroy_graph: bool = False

    @classmethod
    def from_env(cls) -> 'GraphitiConfig':
        """Create a configuration instance from environment variables."""
        return cls(
            llm=GraphitiLLMConfig.from_env(),
            embedder=GraphitiEmbedderConfig.from_env(),
            neo4j=Neo4jConfig.from_env(),
        )

    @classmethod
    def from_cli_and_env(cls, args: argparse.Namespace) -> 'GraphitiConfig':
        """Create configuration from CLI arguments, falling back to environment variables."""
        # Start with environment configuration
        config = cls.from_env()

        # Apply CLI overrides
        if args.group_id:
            config.group_id = args.group_id
        else:
            config.group_id = 'default'

        config.use_custom_entities = args.use_custom_entities
        config.destroy_graph = args.destroy_graph

        # Update LLM config using CLI args
        config.llm = GraphitiLLMConfig.from_cli_and_env(args)

        return config


class MCPConfig(BaseModel):
    """Configuration for MCP server."""

    transport: str = 'sse'  # Default to SSE transport

    @classmethod
    def from_cli(cls, args: argparse.Namespace) -> 'MCPConfig':
        """Create MCP configuration from CLI arguments."""
        return cls(transport=args.transport)


# Configure logging with file rotation
def setup_logging():
    """Set up logging with file rotation and console output."""
    # Create logs directory if it doesn't exist
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Create formatter with detailed timestamp
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # File handler with rotation (10MB max, 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / 'graphiti_mcp.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Console handler (stderr) for real-time monitoring
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Create global config instance - will be properly initialized later
config = GraphitiConfig()

# MCP server instructions
GRAPHITI_MCP_INSTRUCTIONS = """
Graphiti is a memory service for AI agents built on a knowledge graph. Graphiti performs well
with dynamic data such as user interactions, changing enterprise data, and external information.

Graphiti transforms information into a richly connected knowledge network, allowing you to 
capture relationships between concepts, entities, and information. The system organizes data as episodes 
(content snippets), nodes (entities), and facts (relationships between entities), creating a dynamic, 
queryable memory store that evolves with new information. Graphiti supports multiple data formats, including 
structured JSON data, enabling seamless integration with existing data pipelines and systems.

Facts contain temporal metadata, allowing you to track the time of creation and whether a fact is invalid 
(superseded by new information).

Key capabilities:
1. Add episodes (text, messages, or JSON) to the knowledge graph with the add_memory tool
2. Search for nodes (entities) in the graph using natural language queries with search_nodes
3. Find relevant facts (relationships between entities) with search_facts
4. Retrieve specific entity edges or episodes by UUID
5. Manage the knowledge graph with tools like delete_episode, delete_entity_edge, and clear_graph

The server connects to a database for persistent storage and uses language models for certain operations. 
Each piece of information is organized by group_id, allowing you to maintain separate knowledge domains.

When adding information, provide descriptive names and detailed content to improve search quality. 
When searching, use specific queries and consider filtering by group_id for more relevant results.

For optimal performance, ensure the database is properly configured and accessible, and valid 
API keys are provided for any language model operations.
"""

# MCP server instance
mcp = FastMCP(
    'Graphiti Agent Memory',
    instructions=GRAPHITI_MCP_INSTRUCTIONS,
)

# Initialize Graphiti client
graphiti_client: Graphiti | None = None

# Connection state tracking
last_successful_connection: datetime | None = None
consecutive_connection_failures: int = 0


def check_deprecated_config():
    """Warn if old config files detected."""
    # Check for deprecated graphiti-filter.config.json
    if Path('graphiti-filter.config.json').exists():
        logger.warning(
            "⚠️  DEPRECATED: graphiti-filter.config.json detected\n"
            "   Migrate to: graphiti.config.json\n"
            "   See: implementation/guides/MIGRATION_GUIDE.md"
        )

    # Check for excessive env vars
    graphiti_vars = [k for k in os.environ
                     if any(x in k for x in ['NEO4J', 'MODEL', 'EMBEDDER', 'AZURE'])]
    if len(graphiti_vars) > 10:
        logger.warning(
            "⚠️  Many environment variables detected (%d found)\n"
            "   Consider migrating to graphiti.config.json\n"
            "   Run: python implementation/scripts/migrate-to-unified-config.py",
            len(graphiti_vars)
        )


async def initialize_graphiti():
    """Initialize the Graphiti client with the configured settings."""
    global graphiti_client, config, SEMAPHORE_LIMIT, last_successful_connection, consecutive_connection_failures

    try:
        # Check for deprecated configuration files
        check_deprecated_config()

        # Get active database config from unified config
        db_config = unified_config.database.get_active_config()

        # Update semaphore limit from unified config
        SEMAPHORE_LIMIT = unified_config.llm.semaphore_limit

        # Create LLM client if possible
        llm_client = config.llm.create_client()
        if not llm_client and config.use_custom_entities:
            # If custom entities are enabled, we must have an LLM client
            raise ValueError('OPENAI_API_KEY must be set when custom entities are enabled')

        # Validate database configuration
        if not db_config.uri or not db_config.user or not db_config.password:
            raise ValueError('Database URI, USER, and PASSWORD must be set')

        embedder_client = config.embedder.create_client()

        # Initialize Graphiti client with unified config database
        graphiti_client = Graphiti(
            uri=db_config.uri,
            user=db_config.user,
            password=db_config.password,
            llm_client=llm_client,
            embedder=embedder_client,
            max_coroutines=SEMAPHORE_LIMIT,
        )

        # Destroy graph if requested
        if config.destroy_graph:
            logger.info('Destroying graph...')
            await clear_data(graphiti_client.driver)

        # Initialize the graph database with Graphiti's indices
        await graphiti_client.build_indices_and_constraints()
        logger.info('Graphiti client initialized successfully')

        # Update connection tracking on successful initialization
        last_successful_connection = datetime.now(timezone.utc)
        consecutive_connection_failures = 0

        # Log configuration details for transparency
        if llm_client:
            logger.info(f'Using OpenAI model: {config.llm.model}')
            logger.info(f'Using temperature: {config.llm.temperature}')
        else:
            logger.info('No LLM client configured - entity extraction will be limited')

        logger.info(f'Using group_id: {config.group_id}')
        logger.info(
            f'Custom entity extraction: {"enabled" if config.use_custom_entities else "disabled"}'
        )
        logger.info(f'Using concurrency limit: {SEMAPHORE_LIMIT}')

    except Exception as e:
        # Track connection failure
        consecutive_connection_failures += 1
        logger.error(f'Failed to initialize Graphiti: {str(e)}')
        raise


async def initialize_graphiti_with_retry(max_retries: int = 3) -> bool:
    """Initialize Graphiti with automatic retry logic and exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    global consecutive_connection_failures

    for attempt in range(max_retries):
        try:
            await initialize_graphiti()
            logger.info('Graphiti initialized successfully')
            return True
        except Exception as e:
            # Calculate exponential backoff delay: 2^attempt seconds (1s, 2s, 4s)
            delay = 2 ** attempt

            if attempt < max_retries - 1:
                logger.warning(
                    f'Failed to initialize Graphiti (attempt {attempt + 1}/{max_retries}): {str(e)}. '
                    f'Retrying in {delay} seconds...'
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f'Failed to initialize Graphiti after {max_retries} attempts: {str(e)}'
                )
                return False

    return False


def is_recoverable_error(error: Exception) -> bool:
    """Determine if an error is recoverable (connection-related) or fatal.

    Args:
        error: The exception to check

    Returns:
        bool: True if the error is recoverable, False if it's fatal
    """
    error_str = str(error).lower()

    # Recoverable errors (connection-related)
    recoverable_indicators = [
        'connection',
        'timeout',
        'network',
        'unavailable',
        'refused',
        'reset',
        'broken pipe',
        'host unreachable',
        'no route to host',
    ]

    # Fatal errors (configuration, authentication, etc.)
    fatal_indicators = [
        'authentication',
        'unauthorized',
        'invalid credentials',
        'api key',
        'permission denied',
        'configuration',
    ]

    # Check for fatal errors first
    if any(indicator in error_str for indicator in fatal_indicators):
        return False

    # Check for recoverable errors
    if any(indicator in error_str for indicator in recoverable_indicators):
        return True

    # Default to non-recoverable for unknown errors
    return False


def format_fact_result(edge: EntityEdge) -> dict[str, Any]:
    """Format an entity edge into a readable result.

    Since EntityEdge is a Pydantic BaseModel, we can use its built-in serialization capabilities.

    Args:
        edge: The EntityEdge to format

    Returns:
        A dictionary representation of the edge with serialized dates and excluded embeddings
    """
    result = edge.model_dump(
        mode='json',
        exclude={
            'fact_embedding',
        },
    )
    result.get('attributes', {}).pop('fact_embedding', None)
    return result


# Dictionary to store queues for each group_id
# Each queue is a list of tasks to be processed sequentially
episode_queues: dict[str, asyncio.Queue] = {}
# Dictionary to track if a worker is running for each group_id
queue_workers: dict[str, bool] = {}

# Metrics tracking
class MetricsTracker:
    """Track operational metrics for logging and monitoring."""

    def __init__(self):
        self.episode_processing_times: list[float] = []
        self.episode_success_count: int = 0
        self.episode_failure_count: int = 0
        self.episode_timeout_count: int = 0
        self.last_metrics_log: datetime = datetime.now(timezone.utc)

    def record_episode_success(self, duration: float):
        """Record successful episode processing."""
        self.episode_processing_times.append(duration)
        self.episode_success_count += 1

    def record_episode_failure(self):
        """Record failed episode processing."""
        self.episode_failure_count += 1

    def record_episode_timeout(self):
        """Record episode timeout."""
        self.episode_timeout_count += 1

    def get_average_processing_time(self) -> float:
        """Get average episode processing time."""
        if not self.episode_processing_times:
            return 0.0
        return sum(self.episode_processing_times) / len(self.episode_processing_times)

    def get_success_rate(self) -> float:
        """Get episode processing success rate."""
        total = self.episode_success_count + self.episode_failure_count + self.episode_timeout_count
        if total == 0:
            return 1.0
        return self.episode_success_count / total

    def reset_metrics(self):
        """Reset metrics for next logging period."""
        self.episode_processing_times = []
        self.episode_success_count = 0
        self.episode_failure_count = 0
        self.episode_timeout_count = 0

# Global metrics tracker
metrics_tracker = MetricsTracker()

# Detect client working directory (workaround for Claude Code roots bug #3315)
# See: .claude/context/claude-code-roots-issue.md
# Note: PWD from parent process, os.getcwd() is MCP server's cwd
_detected_root = os.getenv("PWD", os.getcwd())
# Normalize MSYS paths (e.g., /c/Users/... -> C:/Users/...)
_detected_root = _normalize_msys_path(_detected_root)
# If cwd is mcp_server/, go up one level to project root
if Path(_detected_root).name == "mcp_server":
    CLIENT_ROOT = str(Path(_detected_root).parent)
else:
    CLIENT_ROOT = _detected_root


async def log_metrics_periodically(interval_seconds: int = 300):
    """Log operational metrics every interval_seconds (default: 5 minutes).

    Args:
        interval_seconds: How often to log metrics (default: 300 seconds / 5 minutes)
    """
    global metrics_tracker, episode_queues, consecutive_connection_failures, last_successful_connection

    logger.info(f'Starting metrics logging (interval: {interval_seconds}s)')

    while True:
        try:
            await asyncio.sleep(interval_seconds)

            # Gather metrics
            metrics = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'connection': {
                    'last_successful': last_successful_connection.isoformat() if last_successful_connection else None,
                    'consecutive_failures': consecutive_connection_failures,
                },
                'episode_processing': {
                    'success_count': metrics_tracker.episode_success_count,
                    'failure_count': metrics_tracker.episode_failure_count,
                    'timeout_count': metrics_tracker.episode_timeout_count,
                    'success_rate': f'{metrics_tracker.get_success_rate() * 100:.1f}%',
                    'avg_duration_seconds': f'{metrics_tracker.get_average_processing_time():.2f}',
                },
                'queues': {
                    group_id: {
                        'depth': episode_queues[group_id].qsize(),
                        'worker_active': queue_workers.get(group_id, False),
                    }
                    for group_id in episode_queues
                },
            }

            # Log as structured JSON for easy parsing
            logger.info(f'METRICS: {json.dumps(metrics)}')

            # Reset counters for next period
            metrics_tracker.reset_metrics()

        except asyncio.CancelledError:
            logger.info('Metrics logging task cancelled')
            break
        except Exception as e:
            logger.error(f'Error logging metrics: {str(e)}')


async def process_episode_queue(group_id: str):
    """Process episodes for a specific group_id sequentially.

    This function runs as a long-lived task that processes episodes
    from the queue one at a time. On recoverable errors, it attempts
    to reconnect and restart the worker.
    """
    global queue_workers, graphiti_client, metrics_tracker

    logger.info(f'Starting episode queue worker for group_id: {group_id}')
    queue_workers[group_id] = True

    # Get episode timeout from unified config
    episode_timeout = unified_config.resilience.episode_timeout

    try:
        while True:
            # Get the next episode processing function from the queue
            # This will wait if the queue is empty
            process_func = await episode_queues[group_id].get()

            # Track processing time
            start_time = datetime.now(timezone.utc)

            try:
                # Process the episode with timeout
                await asyncio.wait_for(process_func(), timeout=episode_timeout)

                # Record success metrics
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                metrics_tracker.record_episode_success(duration)

            except asyncio.TimeoutError:
                # Log timeout error with episode context
                logger.error(
                    f'Episode processing timed out after {episode_timeout} seconds for group_id {group_id}. '
                    'Continuing with next episode...'
                )
                # Record timeout metric
                metrics_tracker.record_episode_timeout()
                # Continue processing next episodes without stopping the worker
            except Exception as e:
                error_msg = str(e)
                logger.error(f'Error processing queued episode for group_id {group_id}: {error_msg}')

                # Record failure metric
                metrics_tracker.record_episode_failure()

                # Check if this is a recoverable error
                if is_recoverable_error(e):
                    logger.warning(
                        f'Detected recoverable error in queue worker for group_id {group_id}. '
                        'Attempting reconnection...'
                    )

                    # Attempt to reconnect
                    reconnection_success = await initialize_graphiti_with_retry(max_retries=3)

                    if reconnection_success:
                        logger.info(
                            f'Successfully reconnected. Resuming queue worker for group_id {group_id}'
                        )
                        # Keep the worker running (queue_workers[group_id] remains True)
                    else:
                        logger.error(
                            f'Failed to reconnect after recoverable error. '
                            f'Stopping queue worker for group_id {group_id}'
                        )
                        queue_workers[group_id] = False
                        break
                else:
                    # Non-recoverable error - log and continue with next episode
                    logger.error(
                        f'Non-recoverable error in queue worker for group_id {group_id}. '
                        'Continuing with next episode...'
                    )
            finally:
                # Mark the task as done regardless of success/failure
                episode_queues[group_id].task_done()
    except asyncio.CancelledError:
        logger.info(f'Episode queue worker for group_id {group_id} was cancelled')
    except Exception as e:
        logger.error(f'Unexpected error in queue worker for group_id {group_id}: {str(e)}')
    finally:
        queue_workers[group_id] = False
        logger.info(f'Stopped episode queue worker for group_id: {group_id}')


@mcp.tool()
async def add_memory(
    name: str,
    episode_body: str,
    group_id: str | None = None,
    source: str = 'text',
    source_description: str = '',
    uuid: str | None = None,
    filepath: str | None = None,
    wait_for_completion: bool | None = None,
) -> str:
    """Add an episode to memory and optionally export to file.

    This function returns immediately and processes the episode addition in the background.
    Episodes for the same group_id are processed sequentially to avoid race conditions.
    If filepath is provided, also saves the episode content to the specified file.

    Args:
        name (str): Name of the episode
        episode_body (str): The content of the episode to persist to memory. When source='json', this must be a
                           properly escaped JSON string, not a raw Python dictionary. The JSON data will be
                           automatically processed to extract entities and relationships.
        group_id (str, optional): A unique ID for this graph. If not provided, uses the default group_id from CLI
                                 or a generated one.
        source (str, optional): Source type, must be one of:
                               - 'text': For plain text content (default)
                               - 'json': For structured data
                               - 'message': For conversation-style content
        source_description (str, optional): Description of the source
        uuid (str, optional): Optional UUID for the episode
        filepath (str, optional): Optional file path to export episode. Supports path variables:
                                 {date}, {timestamp}, {time}, {hash}. If provided, saves episode_body to file.
        wait_for_completion (bool, optional): If True, block until processing completes.
                                             If False, return immediately after queueing.
                                             Defaults to config value (mcp_tools.wait_for_completion_default).

    Examples:
        # Adding plain text content (graph only)
        add_memory(
            name="Company News",
            episode_body="Acme Corp announced a new product line today.",
            source="text",
            source_description="news article",
            group_id="some_arbitrary_string"
        )

        # Adding plain text AND saving to file
        add_memory(
            name="Bug Report",
            episode_body="Login timeout after 5 minutes",
            filepath="bugs/{date}-auth.md"
        )

        # Adding structured JSON data with dynamic filepath
        # NOTE: episode_body must be a properly escaped JSON string. Note the triple backslashes
        add_memory(
            name="Customer Profile",
            episode_body="{\\\"company\\\": {\\\"name\\\": \\\"Acme Technologies\\\"}, \\\"products\\\": [{\\\"id\\\": \\\"P001\\\", \\\"name\\\": \\\"CloudSync\\\"}, {\\\"id\\\": \\\"P002\\\", \\\"name\\\": \\\"DataMiner\\\"}]}",
            source="json",
            source_description="CRM data",
            filepath="data/{timestamp}-profile.json"
        )

        # Adding message-style content with file export
        add_memory(
            name="Customer Conversation",
            episode_body="user: What's your return policy?\nassistant: You can return items within 30 days.",
            source="message",
            source_description="chat transcript",
            group_id="some_arbitrary_string",
            filepath="chats/{date}/{timestamp}.txt"
        )

    Notes:
        When using source='json':
        - The JSON must be a properly escaped string, not a raw Python dictionary
        - The JSON will be automatically processed to extract entities and relationships
        - Complex nested structures are supported (arrays, nested objects, mixed data types), but keep nesting to a minimum
        - Entities will be created from appropriate JSON properties
        - Relationships between entities will be established based on the JSON structure

    Response Types (Story 18):
        - Success: Full processing completed with LLM entity extraction
        - Degraded: Data stored but with reduced functionality (e.g., LLM unavailable)
        - Queued: Operation queued for later processing (when QUEUE_RETRY mode)
        - Error: Operation failed with actionable error details

    LLM Unavailable Behavior (configurable via mcp_tools.on_llm_unavailable):
        - FAIL: Return error immediately (default, best for interactive use)
        - STORE_RAW: Store episode without LLM processing (data preservation)
        - QUEUE_RETRY: Queue for retry when LLM recovers (batch operations)
    """
    global graphiti_client, episode_queues, queue_workers

    start_time = time.perf_counter()

    # Resolve wait_for_completion from config if not provided
    should_wait = wait_for_completion
    if should_wait is None:
        should_wait = unified_config.mcp_tools.wait_for_completion_default

    if graphiti_client is None:
        response = create_error(
            category=ErrorCategory.CONFIGURATION,
            message="Graphiti client not initialized",
            recoverable=False,
            suggestion="Check server startup logs. The MCP server may not have connected to Neo4j successfully."
        )
        return format_response(response)

    try:
        # Map string source to EpisodeType enum
        source_type = EpisodeType.text
        if source.lower() == 'message':
            source_type = EpisodeType.message
        elif source.lower() == 'json':
            source_type = EpisodeType.json

        # Use the provided group_id or fall back to the default from config
        effective_group_id = group_id if group_id is not None else config.group_id

        # Cast group_id to str to satisfy type checker
        # The Graphiti client expects a str for group_id, not Optional[str]
        group_id_str = str(effective_group_id) if effective_group_id is not None else ''

        # We've already checked that graphiti_client is not None above
        # This assert statement helps type checkers understand that graphiti_client is defined
        assert graphiti_client is not None, 'graphiti_client should not be None here'

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # =================================================================
        # LLM Availability Check (Story 18: AC-18.6)
        # =================================================================
        llm_available = client.llm_available
        degradation_mode = unified_config.mcp_tools.on_llm_unavailable
        is_degraded = False
        degradation_reason = None

        if not llm_available:
            logger.warning(f"LLM unavailable for episode '{name}', mode: {degradation_mode}")
            circuit_state = client._availability_manager.circuit_breaker.state.value

            if degradation_mode == "FAIL":
                # Immediate failure with actionable error (AC-18.4)
                response = create_llm_unavailable_error(
                    circuit_state=circuit_state,
                    retry_after_seconds=unified_config.llm_resilience.circuit_breaker.recovery_timeout_seconds
                )
                return format_response(response)

            elif degradation_mode == "STORE_RAW":
                # Mark as degraded - will store without LLM processing
                is_degraded = True
                degradation_reason = DegradationReason.LLM_UNAVAILABLE
                logger.info(f"Episode '{name}' will be stored raw (LLM unavailable, STORE_RAW mode)")

            elif degradation_mode == "QUEUE_RETRY":
                # Queue for later retry when LLM recovers
                # For now, we queue normally but mark for retry
                is_degraded = True
                degradation_reason = DegradationReason.LLM_UNAVAILABLE
                logger.info(f"Episode '{name}' queued for retry when LLM recovers (QUEUE_RETRY mode)")

        # =================================================================
        # Episode Processing (with wait_for_completion support - AC-18.8, AC-18.9)
        # =================================================================

        # Create an Event for synchronization if waiting
        processing_complete: asyncio.Event | None = asyncio.Event() if should_wait else None
        processing_result: dict[str, Any] = {"success": False, "error": None, "episode_id": None}

        async def process_episode():
            nonlocal processing_result
            try:
                logger.info(f"Processing queued episode '{name}' for group_id: {group_id_str}")
                # Use all entity types if use_custom_entities is enabled, otherwise use empty dict
                entity_types = ENTITY_TYPES if config.use_custom_entities else {}

                # If degraded due to LLM unavailability and using STORE_RAW mode,
                # we store the episode but skip LLM-dependent processing
                # The Graphiti client will handle this internally based on store_raw_episode_content flag
                result = await client.add_episode(
                    name=name,
                    episode_body=episode_body,
                    source=source_type,
                    source_description=source_description,
                    group_id=group_id_str,  # Using the string version of group_id
                    uuid=uuid,
                    reference_time=datetime.now(timezone.utc),
                    entity_types=entity_types,
                )

                processing_result["success"] = True
                processing_result["episode_id"] = str(result.uuid) if hasattr(result, 'uuid') else None
                logger.info(f"Episode '{name}' processed successfully")

            except Exception as e:
                error_msg = str(e)
                processing_result["error"] = error_msg
                logger.error(
                    f"Error processing episode '{name}' for group_id {group_id_str}: {error_msg}"
                )
            finally:
                if processing_complete:
                    processing_complete.set()

        # Initialize queue for this group_id if it doesn't exist
        if group_id_str not in episode_queues:
            episode_queues[group_id_str] = asyncio.Queue()

        # Add the episode processing function to the queue
        await episode_queues[group_id_str].put(process_episode)

        # Start a worker for this queue if one isn't already running
        if not queue_workers.get(group_id_str, False):
            asyncio.create_task(process_episode_queue(group_id_str))

        # =================================================================
        # Wait for Completion (if requested - AC-18.8, AC-18.9)
        # =================================================================
        if should_wait and processing_complete:
            try:
                # Wait with timeout to prevent indefinite blocking
                timeout = unified_config.mcp_tools.timeout_seconds
                await asyncio.wait_for(processing_complete.wait(), timeout=float(timeout))
            except asyncio.TimeoutError:
                processing_time_ms = (time.perf_counter() - start_time) * 1000
                response = create_timeout_error(
                    operation="add_memory",
                    timeout_seconds=timeout,
                    suggestion=(
                        f"Episode processing timed out after {timeout}s. "
                        "The operation may still complete in the background. "
                        "Consider using wait_for_completion=false for long operations."
                    )
                )
                return format_response(response)

            # Check processing result after waiting
            if not processing_result["success"]:
                response = create_error(
                    category=ErrorCategory.INTERNAL,
                    message=f"Episode processing failed: {processing_result['error']}",
                    recoverable=True,
                    suggestion="Check the error message and retry."
                )
                return format_response(response)

        # =================================================================
        # Optional File Export
        # =================================================================
        file_saved_path = None
        file_warnings = []

        if filepath:
            try:
                # Resolve path pattern variables
                resolved_path = _resolve_path_pattern(
                    filepath,
                    query=name,  # Use episode name for hash
                    fact_count=0,
                    node_count=0,
                )

                # Resolve to absolute path (relative to client root)
                output_path = _resolve_absolute_path(resolved_path, CLIENT_ROOT)
                logger.debug(f"Path resolution: resolved='{resolved_path}', CLIENT_ROOT='{CLIENT_ROOT}', output='{output_path}'")

                # Security scan
                if detected := _scan_for_credentials(episode_body):
                    file_warnings.append(f"Detected credentials: {', '.join(detected)}")

                # Write file
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(episode_body, encoding="utf-8")

                # Display path relative to client root for cleaner output
                try:
                    file_saved_path = str(output_path.relative_to(CLIENT_ROOT))
                except ValueError:
                    # Path is outside client root, show absolute
                    file_saved_path = str(output_path)

            except Exception as e:
                # File export failed, but episode still queued
                error_msg = str(e)
                logger.error(f"File export failed for episode '{name}': {error_msg}")
                file_warnings.append(f"File export failed: {error_msg}")

        # =================================================================
        # Build Response (Story 18: AC-18.1, AC-18.2, AC-18.3)
        # =================================================================
        processing_time_ms = (time.perf_counter() - start_time) * 1000

        if is_degraded:
            # Degraded response (AC-18.2)
            limitations = ["Entity extraction skipped (LLM unavailable)"]
            if degradation_mode == "QUEUE_RETRY":
                limitations.append("Episode queued for reprocessing when LLM recovers")

            response = create_degraded(
                reason=degradation_reason or DegradationReason.LLM_UNAVAILABLE,
                message=f"Episode '{name}' stored with degraded functionality",
                limitations=limitations,
                episode_id=processing_result.get("episode_id") if should_wait else None,
                processing_time_ms=processing_time_ms,
                episode_name=name,
                group_id=group_id_str,
                saved_to=file_saved_path,
            )
            result = format_response(response)
            if file_warnings:
                result += f"\nWarning: {file_warnings[0]}"
            return result

        else:
            # Success response (AC-18.1)
            if should_wait:
                # Synchronous: processing completed
                msg = f"Episode '{name}' added successfully"
                if file_saved_path:
                    msg += f"\nSaved to {file_saved_path}"
                response = create_success(
                    message=msg,
                    episode_id=processing_result.get("episode_id"),
                    processing_time_ms=processing_time_ms,
                )
                result = format_response(response)
            else:
                # Asynchronous: just queued
                if file_saved_path:
                    msg = f"Episode '{name}' queued successfully\nSaved to {file_saved_path}"
                else:
                    msg = f"Episode '{name}' queued successfully"
                result = msg

            if file_warnings:
                result += f"\nWarning: {file_warnings[0]}"
            return result

    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error queuing episode task: {error_msg}')
        response = create_error(
            category=ErrorCategory.INTERNAL,
            message=f"Error queuing episode task: {error_msg}",
            recoverable=True,
            suggestion="Check the error message and retry. If the issue persists, check server logs."
        )
        return format_response(response)


@mcp.tool()
async def search_memory_nodes(
    query: str,
    group_ids: list[str] | None = None,
    max_nodes: int = 10,
    center_node_uuid: str | None = None,
    entity: str = '',  # cursor seems to break with None
) -> NodeSearchResponse | ErrorResponse:
    """Search the graph memory for relevant node summaries.
    These contain a summary of all of a node's relationships with other nodes.

    Note: entity is a single entity type to filter results (permitted: "Preference", "Procedure").

    Args:
        query: The search query
        group_ids: Optional list of group IDs to filter results
        max_nodes: Maximum number of nodes to return (default: 10)
        center_node_uuid: Optional UUID of a node to center the search around
        entity: Optional single entity type to filter results (permitted: "Preference", "Procedure")
    """
    global graphiti_client

    if graphiti_client is None:
        return ErrorResponse(error='Graphiti client not initialized')

    try:
        # Use the provided group_ids or fall back to the default from config if none provided
        effective_group_ids = (
            group_ids if group_ids is not None else [config.group_id] if config.group_id else []
        )

        # Configure the search
        if center_node_uuid is not None:
            search_config = NODE_HYBRID_SEARCH_NODE_DISTANCE.model_copy(deep=True)
        else:
            search_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
        search_config.limit = max_nodes

        filters = SearchFilters()
        if entity != '':
            filters.node_labels = [entity]

        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Perform the search using the _search method
        search_results = await client._search(
            query=query,
            config=search_config,
            group_ids=effective_group_ids,
            center_node_uuid=center_node_uuid,
            search_filter=filters,
        )

        if not search_results.nodes:
            return NodeSearchResponse(message='No relevant nodes found', nodes=[])

        # Format the node results
        formatted_nodes: list[NodeResult] = [
            {
                'uuid': node.uuid,
                'name': node.name,
                'summary': node.summary if hasattr(node, 'summary') else '',
                'labels': node.labels if hasattr(node, 'labels') else [],
                'group_id': node.group_id,
                'created_at': node.created_at.isoformat(),
                'attributes': node.attributes if hasattr(node, 'attributes') else {},
            }
            for node in search_results.nodes
        ]

        return NodeSearchResponse(message='Nodes retrieved successfully', nodes=formatted_nodes)
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error searching nodes: {error_msg}')
        return ErrorResponse(error=f'Error searching nodes: {error_msg}')


@mcp.tool()
async def search_memory_facts(
    query: str,
    group_ids: list[str] | None = None,
    max_facts: int = 10,
    center_node_uuid: str | None = None,
) -> FactSearchResponse | ErrorResponse:
    """Search the graph memory for relevant facts.

    Args:
        query: The search query
        group_ids: Optional list of group IDs to filter results
        max_facts: Maximum number of facts to return (default: 10)
        center_node_uuid: Optional UUID of a node to center the search around
    """
    global graphiti_client

    if graphiti_client is None:
        return ErrorResponse(error='Graphiti client not initialized')

    try:
        # Validate max_facts parameter
        if max_facts <= 0:
            return ErrorResponse(error='max_facts must be a positive integer')

        # Use the provided group_ids or fall back to the default from config if none provided
        effective_group_ids = (
            group_ids if group_ids is not None else [config.group_id] if config.group_id else []
        )

        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        relevant_edges = await client.search(
            group_ids=effective_group_ids,
            query=query,
            num_results=max_facts,
            center_node_uuid=center_node_uuid,
        )

        if not relevant_edges:
            return FactSearchResponse(message='No relevant facts found', facts=[])

        facts = [format_fact_result(edge) for edge in relevant_edges]
        return FactSearchResponse(message='Facts retrieved successfully', facts=facts)
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error searching facts: {error_msg}')
        return ErrorResponse(error=f'Error searching facts: {error_msg}')


@mcp.tool()
async def delete_entity_edge(uuid: str) -> SuccessResponse | ErrorResponse:
    """Delete an entity edge from the graph memory.

    Args:
        uuid: UUID of the entity edge to delete
    """
    global graphiti_client

    if graphiti_client is None:
        return ErrorResponse(error='Graphiti client not initialized')

    try:
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Get the entity edge by UUID
        entity_edge = await EntityEdge.get_by_uuid(client.driver, uuid)
        # Delete the edge using its delete method
        await entity_edge.delete(client.driver)
        return SuccessResponse(message=f'Entity edge with UUID {uuid} deleted successfully')
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error deleting entity edge: {error_msg}')
        return ErrorResponse(error=f'Error deleting entity edge: {error_msg}')


@mcp.tool()
async def delete_episode(uuid: str) -> SuccessResponse | ErrorResponse:
    """Delete an episode from the graph memory.

    Args:
        uuid: UUID of the episode to delete
    """
    global graphiti_client

    if graphiti_client is None:
        return ErrorResponse(error='Graphiti client not initialized')

    try:
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Get the episodic node by UUID - EpisodicNode is already imported at the top
        episodic_node = await EpisodicNode.get_by_uuid(client.driver, uuid)
        # Delete the node using its delete method
        await episodic_node.delete(client.driver)
        return SuccessResponse(message=f'Episode with UUID {uuid} deleted successfully')
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error deleting episode: {error_msg}')
        return ErrorResponse(error=f'Error deleting episode: {error_msg}')


@mcp.tool()
async def get_entity_edge(uuid: str) -> dict[str, Any] | ErrorResponse:
    """Get an entity edge from the graph memory by its UUID.

    Args:
        uuid: UUID of the entity edge to retrieve
    """
    global graphiti_client

    if graphiti_client is None:
        return ErrorResponse(error='Graphiti client not initialized')

    try:
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Get the entity edge directly using the EntityEdge class method
        entity_edge = await EntityEdge.get_by_uuid(client.driver, uuid)

        # Use the format_fact_result function to serialize the edge
        # Return the Python dict directly - MCP will handle serialization
        return format_fact_result(entity_edge)
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error getting entity edge: {error_msg}')
        return ErrorResponse(error=f'Error getting entity edge: {error_msg}')


@mcp.tool()
async def get_episodes(
    group_id: str | None = None, last_n: int = 10
) -> list[dict[str, Any]] | EpisodeSearchResponse | ErrorResponse:
    """Get the most recent memory episodes for a specific group.

    Args:
        group_id: ID of the group to retrieve episodes from. If not provided, uses the default group_id.
        last_n: Number of most recent episodes to retrieve (default: 10)
    """
    global graphiti_client

    if graphiti_client is None:
        return ErrorResponse(error='Graphiti client not initialized')

    try:
        # Use the provided group_id or fall back to the default from config
        effective_group_id = group_id if group_id is not None else config.group_id

        if not isinstance(effective_group_id, str):
            return ErrorResponse(error='Group ID must be a string')

        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        episodes = await client.retrieve_episodes(
            group_ids=[effective_group_id], last_n=last_n, reference_time=datetime.now(timezone.utc)
        )

        if not episodes:
            return EpisodeSearchResponse(
                message=f'No episodes found for group {effective_group_id}', episodes=[]
            )

        # Use Pydantic's model_dump method for EpisodicNode serialization
        formatted_episodes = [
            # Use mode='json' to handle datetime serialization
            episode.model_dump(mode='json')
            for episode in episodes
        ]

        # Return the Python list directly - MCP will handle serialization
        return formatted_episodes
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error getting episodes: {error_msg}')
        return ErrorResponse(error=f'Error getting episodes: {error_msg}')


@mcp.tool()
async def clear_graph() -> SuccessResponse | ErrorResponse:
    """Clear all data from the graph memory and rebuild indices."""
    global graphiti_client

    if graphiti_client is None:
        return ErrorResponse(error='Graphiti client not initialized')

    try:
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # clear_data is already imported at the top
        await clear_data(client.driver)
        await client.build_indices_and_constraints()
        return SuccessResponse(message='Graph cleared successfully and indices rebuilt')
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error clearing graph: {error_msg}')
        return ErrorResponse(error=f'Error clearing graph: {error_msg}')


@mcp.tool()
async def health_check() -> HealthCheckResponse:
    """Check the health of the MCP server and database connection.

    Returns connection status, database connectivity, and connection metrics.
    This tool can be used to proactively detect connection issues.

    Returns:
        HealthCheckResponse with:
        - status: 'healthy' or 'unhealthy'
        - database_connected: Boolean indicating if database is accessible
        - last_successful_connection: ISO timestamp of last successful connection
        - consecutive_failures: Number of consecutive connection failures
        - error_details: Details of any error if unhealthy
    """
    global graphiti_client, last_successful_connection, consecutive_connection_failures

    if graphiti_client is None:
        return HealthCheckResponse(
            status='unhealthy',
            database_connected=False,
            last_successful_connection=None,
            consecutive_failures=consecutive_connection_failures,
            error_details='Graphiti client not initialized',
        )

    try:
        # Test database connection with a simple query
        client = cast(Graphiti, graphiti_client)

        # Execute a simple query to test connectivity
        async with client.driver.session() as session:
            result = await session.run('RETURN 1 as test')
            await result.single()

        # Update connection tracking on success
        last_successful_connection = datetime.now(timezone.utc)
        consecutive_connection_failures = 0

        return HealthCheckResponse(
            status='healthy',
            database_connected=True,
            last_successful_connection=last_successful_connection.isoformat(),
            consecutive_failures=0,
            error_details=None,
        )
    except Exception as e:
        # Track connection failure
        consecutive_connection_failures += 1
        error_msg = str(e)
        logger.error(f'Health check failed: {error_msg}')

        return HealthCheckResponse(
            status='unhealthy',
            database_connected=False,
            last_successful_connection=last_successful_connection.isoformat()
            if last_successful_connection
            else None,
            consecutive_failures=consecutive_connection_failures,
            error_details=error_msg,
        )


class LLMHealthCheckResponse(TypedDict):
    """Response from LLM health check."""

    status: str
    available: bool
    circuit_state: str
    provider: str
    healthy: bool
    success_rate: float
    latency_ms: float | None
    last_check_timestamp: str | None
    error: str | None


@mcp.tool()
async def llm_health_check() -> LLMHealthCheckResponse:
    """Check the health of the LLM service (AC-17.14).

    Performs a health check on the configured LLM (OpenAI, Azure, Anthropic, etc.)
    and returns detailed status information including circuit breaker state.

    This tool is useful for:
    - Validating LLM API credentials
    - Checking if the LLM service is responding
    - Monitoring circuit breaker state
    - Diagnosing LLM-related issues

    Returns:
        LLMHealthCheckResponse with:
        - status: 'healthy' or 'unhealthy'
        - available: Whether the LLM is available for requests
        - circuit_state: Current circuit breaker state (closed/open/half_open)
        - provider: LLM provider name (openai, anthropic, etc.)
        - healthy: Result of the last health check
        - success_rate: Recent success rate (0.0 to 1.0)
        - latency_ms: Response time of last health check in milliseconds
        - last_check_timestamp: ISO timestamp of last health check
        - error: Error message if unhealthy
    """
    global graphiti_client

    if graphiti_client is None:
        return LLMHealthCheckResponse(
            status='unhealthy',
            available=False,
            circuit_state='unknown',
            provider='unknown',
            healthy=False,
            success_rate=0.0,
            latency_ms=None,
            last_check_timestamp=None,
            error='Graphiti client not initialized',
        )

    try:
        client = cast(Graphiti, graphiti_client)

        # Perform health check and get status
        health_result = await client.llm_health_check()

        # Extract values from health result
        is_available = health_result.get('available', False)
        circuit_state = health_result.get('circuit_state', 'unknown')
        health_status = health_result.get('health_status', {})
        last_check_result = health_result.get('last_check_result', {})

        return LLMHealthCheckResponse(
            status='healthy' if last_check_result.get('healthy', False) else 'unhealthy',
            available=is_available,
            circuit_state=circuit_state,
            provider=client._get_provider_type(client.llm_client),
            healthy=last_check_result.get('healthy', False),
            success_rate=health_status.get('success_rate', 0.0),
            latency_ms=last_check_result.get('latency_ms'),
            last_check_timestamp=last_check_result.get('timestamp'),
            error=last_check_result.get('error'),
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f'LLM health check failed: {error_msg}')

        return LLMHealthCheckResponse(
            status='unhealthy',
            available=False,
            circuit_state='unknown',
            provider='unknown',
            healthy=False,
            success_rate=0.0,
            latency_ms=None,
            last_check_timestamp=None,
            error=error_msg,
        )


@mcp.tool()
async def session_tracking_start(session_id: str | None = None, force: bool = False) -> str:
    """Enable session tracking for the current or specified session.

    This tool starts automatic JSONL session tracking for Claude Code sessions. When enabled,
    the system monitors session files, filters messages, and indexes them into the Graphiti
    knowledge graph for cross-session memory and continuity.

    Runtime behavior:
    - Without force: Respects global configuration (unified_config.session_tracking.enabled)
    - With force=True: Overrides global config and always enables tracking for this session

    Args:
        session_id (str, optional): Session ID to enable tracking for. If None, uses current session.
                                    Format: UUID string (extracted from JSONL filename)
        force (bool, optional): Force enable even if globally disabled (default: False)

    Returns:
        str: Success message with session ID and tracking status

    Examples:
        # Enable for current session (respects global config)
        session_tracking_start()

        # Enable for specific session
        session_tracking_start(session_id="abc123-def456")

        # Force enable (override global config)
        session_tracking_start(force=True)

    Note:
        - Session tracking requires Neo4j database connection
        - Filtered sessions reduce token usage by 35-70% (configurable)
        - Sessions are indexed when they become inactive (default: 5 minutes)
        - Use session_tracking_status() to check current state
    """
    global session_manager, runtime_session_tracking_state

    try:
        # Check if session manager is initialized
        if session_manager is None:
            return json.dumps({
                "status": "error",
                "message": "Session tracking not initialized. Session manager is not running.",
                "session_id": session_id,
                "enabled": False
            })

        # Determine effective session ID (if not provided, we can't track without current session context)
        effective_session_id = session_id if session_id else "current"

        # Check global configuration
        global_enabled = unified_config.session_tracking.enabled

        # Determine if we should enable
        should_enable = force or global_enabled

        if not should_enable and not force:
            return json.dumps({
                "status": "disabled",
                "message": "Session tracking is globally disabled. Use force=True to override.",
                "session_id": effective_session_id,
                "enabled": False,
                "global_config": global_enabled
            })

        # Enable tracking for this session
        runtime_session_tracking_state[effective_session_id] = True

        logger.info(f"Session tracking enabled for session: {effective_session_id} (force={force})")

        return json.dumps({
            "status": "success",
            "message": f"Session tracking enabled for session {effective_session_id}",
            "session_id": effective_session_id,
            "enabled": True,
            "forced": force,
            "global_config": global_enabled
        })

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error enabling session tracking: {error_msg}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Error enabling session tracking: {error_msg}",
            "session_id": session_id,
            "enabled": False
        })


@mcp.tool()
async def session_tracking_stop(session_id: str | None = None) -> str:
    """Disable session tracking for the current or specified session.

    This tool stops automatic JSONL session tracking for a specific session. The session
    will no longer be monitored or indexed into Graphiti, even if globally enabled.

    Runtime behavior:
    - Adds session ID to exclusion list (runtime_session_tracking_state[session_id] = False)
    - Does not affect other active sessions
    - Does not modify global configuration

    Args:
        session_id (str, optional): Session ID to disable tracking for. If None, uses current session.
                                    Format: UUID string (extracted from JSONL filename)

    Returns:
        str: Success message with session ID and tracking status

    Examples:
        # Disable for current session
        session_tracking_stop()

        # Disable for specific session
        session_tracking_stop(session_id="abc123-def456")

    Note:
        - Stopping tracking does NOT delete already-indexed data
        - To re-enable, use session_tracking_start()
        - To check status, use session_tracking_status()
    """
    global runtime_session_tracking_state

    try:
        # Determine effective session ID
        effective_session_id = session_id if session_id else "current"

        # Disable tracking for this session
        runtime_session_tracking_state[effective_session_id] = False

        logger.info(f"Session tracking disabled for session: {effective_session_id}")

        return json.dumps({
            "status": "success",
            "message": f"Session tracking disabled for session {effective_session_id}",
            "session_id": effective_session_id,
            "enabled": False
        })

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error disabling session tracking: {error_msg}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Error disabling session tracking: {error_msg}",
            "session_id": session_id
        })


@mcp.tool()
async def session_tracking_status(session_id: str | None = None) -> str:
    """Get session tracking status and configuration details.

    Returns comprehensive information about session tracking state, including:
    - Global configuration (enabled/disabled)
    - Per-session runtime state (if applicable)
    - Session manager status
    - Active session count
    - Configuration details (paths, timeouts, filtering)

    Args:
        session_id (str, optional): Session ID to check status for. If None, returns global status.
                                    Format: UUID string (extracted from JSONL filename)

    Returns:
        str: JSON string with detailed status information

    Response format:
        {
            "status": "success" | "error",
            "session_id": str | null,
            "enabled": bool (effective state for this session),
            "global_config": {
                "enabled": bool,
                "watch_path": str,
                "inactivity_timeout": int (seconds),
                "check_interval": int (seconds)
            },
            "runtime_override": bool | null (true/false if overridden, null if not),
            "session_manager": {
                "running": bool,
                "active_sessions": int
            },
            "filter_config": {
                "tool_calls": str (FULL|SUMMARY|OMIT),
                "tool_content": str (FULL|SUMMARY|OMIT),
                "user_messages": str (FULL|SUMMARY|OMIT),
                "agent_messages": str (FULL|SUMMARY|OMIT)
            }
        }

    Examples:
        # Check global status
        session_tracking_status()

        # Check specific session status
        session_tracking_status(session_id="abc123-def456")

    Note:
        - Use this tool to verify configuration before starting tracking
        - Effective state = runtime override OR global config
        - Filter config shows token reduction strategy
    """
    global session_manager, runtime_session_tracking_state

    try:
        # Determine effective session ID
        effective_session_id = session_id if session_id else None

        # Get global configuration
        global_config = {
            "enabled": unified_config.session_tracking.enabled,
            "watch_path": str(unified_config.session_tracking.watch_path) if unified_config.session_tracking.watch_path else None,
            "inactivity_timeout": unified_config.session_tracking.inactivity_timeout,
            "check_interval": unified_config.session_tracking.check_interval
        }

        # Check runtime override for this session
        runtime_override = None
        if effective_session_id and effective_session_id in runtime_session_tracking_state:
            runtime_override = runtime_session_tracking_state[effective_session_id]

        # Determine effective enabled state
        if runtime_override is not None:
            effective_enabled = runtime_override
        else:
            effective_enabled = global_config["enabled"]

        # Get session manager status
        session_manager_status = {
            "running": session_manager is not None and session_manager._is_running,
            "active_sessions": session_manager.get_active_session_count() if session_manager else 0
        }

        # Get filter configuration
        filter_config = {
            "tool_calls": unified_config.session_tracking.filter.tool_calls.value if unified_config.session_tracking.filter else "SUMMARY",
            "tool_content": unified_config.session_tracking.filter.tool_content.value if unified_config.session_tracking.filter else "SUMMARY",
            "user_messages": unified_config.session_tracking.filter.user_messages.value if unified_config.session_tracking.filter else "FULL",
            "agent_messages": unified_config.session_tracking.filter.agent_messages.value if unified_config.session_tracking.filter else "FULL"
        }

        return json.dumps({
            "status": "success",
            "session_id": effective_session_id,
            "enabled": effective_enabled,
            "global_config": global_config,
            "runtime_override": runtime_override,
            "session_manager": session_manager_status,
            "filter_config": filter_config
        }, indent=2)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting session tracking status: {error_msg}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Error getting status: {error_msg}",
            "session_id": session_id
        })


@mcp.tool()
async def session_tracking_health() -> str:
    """Get comprehensive health status of the session tracking system (AC-19.10, AC-19.11).

    This tool provides detailed health information including:
    - Service status (running/stopped/degraded/error)
    - LLM availability status
    - Current degradation level (FULL=0, PARTIAL=1, RAW_ONLY=2)
    - Processing queue status (pending, processing, completed today, failed today)
    - Retry queue status (pending retries, permanent failures, next retry time)
    - Recent failures (last 10 with details)
    - Uptime and activity metrics

    This tool is useful for:
    - Monitoring session tracking health
    - Diagnosing LLM availability issues
    - Checking retry queue status
    - Understanding current degradation level

    Returns:
        JSON string with comprehensive health information:
        {
            "status": "success" | "error",
            "health": {
                "service_status": "running" | "stopped" | "degraded" | "error",
                "degradation_level": {
                    "level": 0 | 1 | 2,
                    "name": "FULL" | "PARTIAL" | "RAW_ONLY",
                    "description": str
                },
                "llm_status": {
                    "available": bool,
                    "last_check": str | null,
                    "provider": str | null,
                    "circuit_state": str | null,
                    "error": str | null,
                    "success_rate": float | null
                },
                "queue_status": {
                    "pending": int,
                    "processing": int,
                    "completed_today": int,
                    "failed_today": int
                },
                "retry_queue": {
                    "count": int,
                    "pending_retries": int,
                    "permanent_failures": int,
                    "next_retry": str | null,
                    "oldest_failure": str | null
                },
                "recent_failures": [
                    {
                        "episode_id": str,
                        "session_id": str,
                        "error": str,
                        "retry_count": int,
                        "next_retry": str | null,
                        "failed_at": str | null
                    }
                ],
                "uptime_seconds": int | null,
                "started_at": str | null,
                "last_activity": str | null,
                "active_sessions": int
            }
        }

    Examples:
        # Get full health status
        session_tracking_health()

    Note:
        - Use this tool to monitor session tracking health proactively
        - Degradation level indicates current processing capability
        - Check retry_queue.pending_retries to see queued episodes awaiting LLM recovery
    """
    global session_manager, resilient_indexer, status_aggregator

    try:
        # Create status aggregator if not exists
        if status_aggregator is None:
            aggregator = SessionTrackingStatusAggregator()
            if session_manager:
                aggregator.set_session_manager(session_manager)
            if resilient_indexer:
                aggregator.set_retry_queue(resilient_indexer.retry_queue)
        else:
            aggregator = status_aggregator

        # Get health status
        health = await aggregator.get_health()

        # If we have a resilient indexer, get its degradation level
        if resilient_indexer:
            health.degradation_level = resilient_indexer.get_degradation_level()

        return json.dumps({
            "status": "success",
            "health": health.to_dict()
        }, indent=2)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting session tracking health: {error_msg}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Error getting health: {error_msg}"
        })


@mcp.tool()
async def get_failed_episodes(
    include_permanent: bool = True,
    limit: int = 50,
) -> str:
    """Get failed episodes from the retry queue (AC-19.12).

    This tool retrieves information about episodes that failed during processing
    and are either awaiting retry or have permanently failed.

    Args:
        include_permanent: Include permanently failed episodes (default: True)
        limit: Maximum number of episodes to return (default: 50, max: 100)

    Returns:
        JSON string with failed episodes:
        {
            "status": "success" | "error",
            "total_count": int,
            "returned_count": int,
            "episodes": [
                {
                    "episode_id": str,
                    "session_id": str,
                    "session_file": str,
                    "group_id": str,
                    "error_type": str,
                    "error_message": str,
                    "failed_at": str,
                    "retry_count": int,
                    "next_retry_at": str | null,
                    "permanent_failure": bool,
                    "last_retry_at": str | null,
                    "created_at": str,
                    "metadata": dict
                }
            ],
            "stats": {
                "queue_size": int,
                "pending_retries": int,
                "permanent_failures": int,
                "total_added": int,
                "total_retried": int,
                "total_succeeded": int,
                "total_failed_permanently": int
            }
        }

    Examples:
        # Get all failed episodes
        get_failed_episodes()

        # Get only episodes awaiting retry (exclude permanent failures)
        get_failed_episodes(include_permanent=False)

        # Get top 10 failed episodes
        get_failed_episodes(limit=10)

    Note:
        - Episodes with permanent_failure=True have exhausted all retries
        - Use session_tracking_health() for aggregate status
        - Episodes are sorted by failed_at (most recent first)
    """
    global resilient_indexer

    try:
        # Clamp limit
        limit = min(max(1, limit), 100)

        if resilient_indexer is None:
            return json.dumps({
                "status": "success",
                "message": "Resilient indexer not initialized - no retry queue available",
                "total_count": 0,
                "returned_count": 0,
                "episodes": [],
                "stats": {
                    "queue_size": 0,
                    "pending_retries": 0,
                    "permanent_failures": 0,
                    "total_added": 0,
                    "total_retried": 0,
                    "total_succeeded": 0,
                    "total_failed_permanently": 0
                }
            }, indent=2)

        # Get failed episodes
        episodes = await resilient_indexer.get_failed_episodes(
            include_permanent=include_permanent,
            limit=limit
        )

        # Get queue stats
        stats = resilient_indexer.retry_queue.get_stats()

        # Convert episodes to dict
        episode_dicts = []
        for ep in episodes:
            episode_dicts.append({
                "episode_id": ep.episode_id,
                "session_id": ep.session_id,
                "session_file": ep.session_file,
                "group_id": ep.group_id,
                "error_type": ep.error_type,
                "error_message": ep.error_message,
                "failed_at": ep.failed_at.isoformat() if ep.failed_at else None,
                "retry_count": ep.retry_count,
                "next_retry_at": ep.next_retry_at.isoformat() if ep.next_retry_at else None,
                "permanent_failure": ep.permanent_failure,
                "last_retry_at": ep.last_retry_at.isoformat() if ep.last_retry_at else None,
                "created_at": ep.created_at.isoformat() if ep.created_at else None,
                "metadata": ep.metadata,
            })

        # Get total count
        all_episodes = await resilient_indexer.retry_queue.get_all()
        if not include_permanent:
            all_episodes = [ep for ep in all_episodes if not ep.permanent_failure]
        total_count = len(all_episodes)

        return json.dumps({
            "status": "success",
            "total_count": total_count,
            "returned_count": len(episode_dicts),
            "episodes": episode_dicts,
            "stats": stats
        }, indent=2)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting failed episodes: {error_msg}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Error getting failed episodes: {error_msg}"
        })


async def session_tracking_sync_history(
    project: str | None = None,
    days: int = 7,
    max_sessions: int = 100,
    dry_run: bool = True,
) -> str:
    """Manually sync historical sessions to Graphiti.

    This tool allows users to index historical sessions beyond the automatic
    rolling window. Useful for one-time imports or catching up on missed sessions.

    Args:
        project: Project path to sync (None = all projects in watch_path)
        days: Number of days to look back (0 = all history, use with caution)
        max_sessions: Maximum sessions to sync (safety limit, default 100)
        dry_run: Preview mode without actual indexing (default: True)

    Returns:
        JSON string with sync results

    Examples:
        Preview last 7 days: await session_tracking_sync_history()
        Actually sync: await session_tracking_sync_history(dry_run=False)
    """
    global session_manager, graphiti_client
    return await _session_tracking_sync_history(
        session_manager=session_manager,
        graphiti_client=graphiti_client,
        unified_config=unified_config,
        project=project,
        days=days,
        max_sessions=max_sessions,
        dry_run=dry_run,
    )


@mcp.resource('http://graphiti/status')
async def get_status() -> StatusResponse:
    """Get the status of the Graphiti MCP server and Neo4j connection."""
    global graphiti_client

    if graphiti_client is None:
        return StatusResponse(status='error', message='Graphiti client not initialized')

    try:
        # We've already checked that graphiti_client is not None above
        assert graphiti_client is not None

        # Use cast to help the type checker understand that graphiti_client is not None
        client = cast(Graphiti, graphiti_client)

        # Test database connection
        await client.driver.client.verify_connectivity()  # type: ignore

        return StatusResponse(
            status='ok', message='Graphiti MCP server is running and connected to Neo4j'
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f'Error checking Neo4j connection: {error_msg}')
        return StatusResponse(
            status='error',
            message=f'Graphiti MCP server is running but Neo4j connection failed: {error_msg}',
        )


async def check_inactive_sessions_periodically(
    manager: SessionManager,
    interval_seconds: int
) -> None:
    """Periodically check for inactive sessions and close them.

    This function runs in a loop, checking for inactive sessions at regular intervals.
    When inactive sessions are found, they are closed and indexed to Graphiti.

    Args:
        manager: SessionManager instance to check for inactive sessions
        interval_seconds: How often to check for inactive sessions (in seconds)

    Raises:
        asyncio.CancelledError: When the task is cancelled (expected on shutdown)
    """
    logger.info(f"Started periodic session inactivity checker (interval: {interval_seconds}s)")

    try:
        while True:
            await asyncio.sleep(interval_seconds)

            try:
                closed_count = manager.check_inactive_sessions()
                if closed_count > 0:
                    logger.info(f"Closed {closed_count} inactive session(s)")
            except Exception as e:
                logger.error(f"Error checking inactive sessions: {e}", exc_info=True)

    except asyncio.CancelledError:
        logger.info("Session inactivity checker stopped")
        raise



def ensure_global_config_exists() -> Path:
    """Ensure global configuration file exists with sensible defaults.

    Creates ~/.graphiti/graphiti.config.json if it doesn't exist.
    Includes inline comments (_comment and _*_help fields) to guide users.

    Returns:
        Path to config file
    """
    config_path = Path.home() / ".graphiti" / "graphiti.config.json"

    if config_path.exists():
        logger.debug(f"Config file already exists: {config_path}")
        return config_path

    # Create directory
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate config with inline comments
    default_config = {
        "_comment": "Graphiti MCP Server Configuration (auto-generated)",
        "_docs": "https://github.com/getzep/graphiti/blob/main/CONFIGURATION.md",
        "database": {
            "_comment": "Required: Configure your Neo4j connection",
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password_env": "NEO4J_PASSWORD",
        },
        "llm": {
            "_comment": "Required: Configure your OpenAI API key",
            "provider": "openai",
            "default_model": "gpt-4.1-mini",
            "small_model": "gpt-4.1-nano",
            "openai": {
                "api_key_env": "OPENAI_API_KEY",
            },
        },
        "session_tracking": {
            "_comment": "Session tracking is DISABLED by default for security",
            "_docs": "See docs/SESSION_TRACKING_USER_GUIDE.md",
            "enabled": False,
            "_enabled_help": "Set to true to enable session tracking (opt-in)",
            "watch_path": None,
            "_watch_path_help": "null = ~/.claude/projects/ | Set to specific project path",
            "inactivity_timeout": 900,
            "_inactivity_timeout_help": "Seconds before session closed (900 = 15 minutes, handles long operations)",
            "check_interval": 60,
            "_check_interval_help": "Seconds between inactivity checks (60 = 1 minute, responsive)",
            "auto_summarize": False,
            "_auto_summarize_help": "Use LLM to summarize sessions (costs money, set to true to enable)",
            "store_in_graph": True,
            "_store_in_graph_help": "Store in Neo4j graph (required for cross-session memory)",
            "keep_length_days": 7,
            "_keep_length_days_help": "Track sessions from last N days (7 = safe, null = all)",
            "filter": {
                "_comment": "Message filtering for token reduction",
                "tool_calls": True,
                "_tool_calls_help": "Preserve tool structure (recommended: true)",
                "tool_content": "default-tool-content.md",
                "_tool_content_help": "true (full) | false (omit) | 'template.md' | 'inline prompt...'",
                "user_messages": True,
                "_user_messages_help": "true (full) | false (omit) | 'template.md' | 'inline prompt...'",
                "agent_messages": True,
                "_agent_messages_help": "true (full) | false (omit) | 'template.md' | 'inline prompt...'",
            },
        },
    }

    # Write config
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=2)

    logger.info(f"Created default config: {config_path}")
    logger.info("Please update database credentials and OpenAI API key in environment variables!")

    return config_path

def ensure_default_templates_exist() -> None:
    """Ensure default summarization templates exist in global config directory.

    Creates ~/.graphiti/auto-tracking/templates/ directory and populates it with
    default templates from graphiti_core.session_tracking.prompts if they don't exist.

    This function is idempotent - safe to call multiple times.
    """
    templates_dir = Path.home() / ".graphiti" / "auto-tracking" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in DEFAULT_TEMPLATES.items():
        template_path = templates_dir / filename
        if not template_path.exists():
            template_path.write_text(content, encoding="utf-8")
            logger.info(f"Created default template: {template_path}")
        else:
            logger.debug(f"Template already exists: {template_path}")


async def initialize_session_tracking() -> None:
    """Initialize session tracking system if enabled in configuration.

    This function:
    1. Checks if session tracking is enabled in unified_config
    2. Creates ClaudePathResolver for session file discovery
    3. Initializes SessionManager with indexing callback
    4. Creates ResilientSessionIndexer with retry queue (Story 19)
    5. Starts session manager to begin monitoring

    The session manager will:
    - Monitor Claude Code session files (.jsonl)
    - Detect new sessions and session updates
    - Track inactivity and trigger indexing on session close
    - Filter and index sessions into Graphiti knowledge graph
    - Handle LLM failures with graceful degradation (Story 19)
    """
    global session_manager, graphiti_client, resilient_indexer, status_aggregator

    try:
        # Check if session tracking is enabled
        if not unified_config.session_tracking.enabled:
            logger.info("Session tracking disabled in configuration")
            return

        # Check if Graphiti is initialized
        if graphiti_client is None:
            logger.warning("Session tracking enabled but Graphiti client not initialized. Skipping session tracking.")
            return

        logger.info("Initializing session tracking...")

        # Ensure default templates exist
        ensure_default_templates_exist()

        # Create path resolver
        watch_path = unified_config.session_tracking.watch_path
        path_resolver = ClaudePathResolver(claude_dir=watch_path) if watch_path else ClaudePathResolver()

        logger.info(f"Session tracking watch path: {path_resolver.watch_all_projects()}")

        # Get resilience configuration
        resilience_config = unified_config.session_tracking.resilience

        # Map string config to enum
        on_llm_unavailable_map = {
            "FAIL": OnLLMUnavailable.FAIL,
            "STORE_RAW": OnLLMUnavailable.STORE_RAW,
            "STORE_RAW_AND_RETRY": OnLLMUnavailable.STORE_RAW_AND_RETRY,
        }
        on_llm_unavailable = on_llm_unavailable_map.get(
            resilience_config.on_llm_unavailable,
            OnLLMUnavailable.STORE_RAW_AND_RETRY
        )

        # Determine retry queue path
        retry_queue_path = None
        if resilience_config.retry_queue.persist_to_disk:
            # Store retry queue in .graphiti directory
            retry_queue_path = Path.home() / ".graphiti" / "retry_queue.json"
            retry_queue_path.parent.mkdir(parents=True, exist_ok=True)

        # Create resilient indexer config (Story 19)
        resilient_config = ResilientIndexerConfig(
            on_llm_unavailable=on_llm_unavailable,
            retry_queue_path=retry_queue_path,
            max_retries=resilience_config.retry_queue.max_retries,
            retry_delays=resilience_config.retry_queue.retry_delays_seconds,
            max_queue_size=resilience_config.retry_queue.max_queue_size,
            auto_recovery_interval=60,  # Check every 60 seconds
        )

        # Create resilient session indexer
        resilient_indexer = ResilientSessionIndexer(
            graphiti=graphiti_client,
            config=resilient_config,
        )

        # Start resilient indexer (loads retry queue, starts processor)
        await resilient_indexer.start()
        logger.info(f"Resilient session indexer started (mode: {on_llm_unavailable.value})")

        # Create status aggregator
        status_aggregator = SessionTrackingStatusAggregator()
        status_aggregator.set_retry_queue(resilient_indexer.retry_queue)
        status_aggregator.mark_started()

        # Create filter
        filter_config = unified_config.session_tracking.filter
        session_filter = SessionFilter(
            filter_config=filter_config
        ) if filter_config else SessionFilter()

        # Define session closed callback with resilience
        def on_session_closed(session_id: str, file_path: Path, context) -> None:
            """Callback when session closes - filter and index to Graphiti with resilience."""
            try:
                # Check runtime state (per-session override)
                if session_id in runtime_session_tracking_state:
                    if not runtime_session_tracking_state[session_id]:
                        logger.info(f"Session {session_id} excluded by runtime override, skipping indexing")
                        return

                logger.info(f"Session closed: {session_id}, indexing to Graphiti...")

                # Filter conversation
                filtered_messages = session_filter.filter_conversation(context.messages)

                # Format filtered content
                filtered_content = "\n\n".join([
                    f"[{msg.role}]: {msg.content}" for msg in filtered_messages
                ])

                # Get project hash as group_id
                group_id = path_resolver.resolve_project_from_session_file(file_path) or "unknown"

                # Index to Graphiti using resilient indexer (handles degradation)
                import asyncio
                loop = asyncio.get_event_loop()
                loop.create_task(resilient_indexer.index_session(
                    session_id=session_id,
                    filtered_content=filtered_content,
                    group_id=group_id,
                    session_file=str(file_path),
                ))

                logger.info(f"Session {session_id} indexing initiated ({len(filtered_messages)} messages)")

            except Exception as e:
                logger.error(f"Error indexing session {session_id}: {e}", exc_info=True)
                # Session isolation: error in one session doesn't affect others (AC-19.3)

        # Create session manager
        session_manager = SessionManager(
            path_resolver=path_resolver,
            inactivity_timeout=unified_config.session_tracking.inactivity_timeout,
            keep_length_days=unified_config.session_tracking.keep_length_days,
            on_session_closed=on_session_closed
        )

        # Connect session manager to status aggregator
        status_aggregator.set_session_manager(session_manager)

        # Start session manager
        session_manager.start()

        # Start periodic inactivity checker
        global _inactivity_checker_task
        check_interval = unified_config.session_tracking.check_interval
        _inactivity_checker_task = asyncio.create_task(
            check_inactive_sessions_periodically(session_manager, check_interval)
        )

        logger.info(f"Session tracking initialized and started successfully (check_interval: {check_interval}s)")

    except Exception as e:
        logger.error(f"Error initializing session tracking: {e}", exc_info=True)
        logger.warning("Continuing without session tracking")


async def initialize_server() -> MCPConfig:
    """Parse CLI arguments and initialize the Graphiti server configuration."""
    global config

    # Ensure config and templates exist (auto-generate if missing)
    try:
        ensure_global_config_exists()
        ensure_default_templates_exist()
    except Exception as e:
        logger.error(f"Failed to auto-generate config/templates: {e}", exc_info=True)
        # Continue - user may have config in project directory

    parser = argparse.ArgumentParser(
        description='Run the Graphiti MCP server with optional LLM client'
    )
    parser.add_argument(
        '--group-id',
        help='Namespace for the graph. This is an arbitrary string used to organize related data. '
        'If not provided, a random UUID will be generated.',
    )
    parser.add_argument(
        '--transport',
        choices=['sse', 'stdio'],
        default='sse',
        help='Transport to use for communication with the client. (default: sse)',
    )
    parser.add_argument(
        '--model', help=f'Model name to use with the LLM client. (default: {DEFAULT_LLM_MODEL})'
    )
    parser.add_argument(
        '--small-model',
        help=f'Small model name to use with the LLM client. (default: {SMALL_LLM_MODEL})',
    )
    parser.add_argument(
        '--temperature',
        type=float,
        help='Temperature setting for the LLM (0.0-2.0). Lower values make output more deterministic. (default: 0.7)',
    )
    parser.add_argument('--destroy-graph', action='store_true', help='Destroy all Graphiti graphs')
    parser.add_argument(
        '--use-custom-entities',
        action='store_true',
        help='Enable entity extraction using the predefined ENTITY_TYPES',
    )
    parser.add_argument(
        '--host',
        default=os.environ.get('MCP_SERVER_HOST'),
        help='Host to bind the MCP server to (default: MCP_SERVER_HOST environment variable)',
    )

    args = parser.parse_args()

    # Build configuration from CLI arguments and environment variables
    config = GraphitiConfig.from_cli_and_env(args)

    # Log the group ID configuration
    if args.group_id:
        logger.info(f'Using provided group_id: {config.group_id}')
    else:
        logger.info(f'Generated random group_id: {config.group_id}')

    # Log entity extraction configuration
    if config.use_custom_entities:
        logger.info('Entity extraction enabled using predefined ENTITY_TYPES')
    else:
        logger.info('Entity extraction disabled (no custom entities will be used)')

    # Initialize Graphiti with automatic retry
    success = await initialize_graphiti_with_retry(max_retries=3)
    if not success:
        logger.error('Failed to initialize Graphiti after retries. Server may have limited functionality.')

    # Initialize session tracking if enabled
    await initialize_session_tracking()

    if args.host:
        logger.info(f'Setting MCP server host to: {args.host}')
        # Set MCP server host from CLI or env
        mcp.settings.host = args.host

    # Return MCP configuration
    return MCPConfig.from_cli(args)


async def run_mcp_server():
    """Run the MCP server in the current event loop."""
    # Initialize the server
    mcp_config = await initialize_server()

    # Start metrics logging task
    metrics_task = asyncio.create_task(log_metrics_periodically(interval_seconds=300))
    logger.info('Started periodic metrics logging task (5 minute interval)')

    try:
        # Run the server with stdio transport for MCP in the same event loop
        logger.info(f'Starting MCP server with transport: {mcp_config.transport}')
        if mcp_config.transport == 'stdio':
            await mcp.run_stdio_async()
        elif mcp_config.transport == 'sse':
            logger.info(
                f'Running MCP server with SSE transport on {mcp.settings.host}:{mcp.settings.port}'
            )
            await mcp.run_sse_async()
    finally:
        # Clean up metrics task on shutdown
        metrics_task.cancel()
        try:
            await metrics_task
        except asyncio.CancelledError:
            logger.info('Metrics logging task cancelled successfully')

        # Clean up session manager and inactivity checker on shutdown
        global session_manager, _inactivity_checker_task, resilient_indexer

        # Cancel inactivity checker task first
        if _inactivity_checker_task is not None:
            logger.info('Stopping session inactivity checker...')
            _inactivity_checker_task.cancel()
            try:
                await _inactivity_checker_task
            except asyncio.CancelledError:
                logger.info('Session inactivity checker cancelled successfully')

        # Stop session manager
        if session_manager is not None:
            try:
                logger.info('Stopping session manager...')
                session_manager.stop()
                logger.info('Session manager stopped successfully')
            except Exception as e:
                logger.error(f'Error stopping session manager: {e}', exc_info=True)

        # Stop resilient indexer (Story 19 - persists retry queue)
        if resilient_indexer is not None:
            try:
                logger.info('Stopping resilient indexer...')
                await resilient_indexer.stop()
                logger.info('Resilient indexer stopped successfully')
            except Exception as e:
                logger.error(f'Error stopping resilient indexer: {e}', exc_info=True)


def main():
    """Main function to run the Graphiti MCP server."""
    try:
        # Run everything in a single event loop
        asyncio.run(run_mcp_server())
    except Exception as e:
        logger.error(f'Error initializing Graphiti MCP server: {str(e)}')
        raise


if __name__ == '__main__':
    main()
