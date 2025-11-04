import os
import sys

# This code adds the project root directory to the Python path, allowing imports to work correctly when running tests.
# Without this file, you might encounter ModuleNotFoundError when trying to import modules from your project, especially when running tests.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

# Try to import existing fixtures, but don't fail if dependencies aren't available
try:
    from tests.helpers_test import graph_driver, mock_embedder
    __all__ = ['graph_driver', 'mock_embedder']
except ImportError:
    # Neo4j or other dependencies not available - skip those fixtures
    __all__ = []

# Additional fixtures for filter system tests
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_openai_provider():
    """Mock OpenAI provider for filter tests."""
    provider = AsyncMock()
    provider.is_available.return_value = True
    provider.complete.return_value = {
        "should_store": True,
        "category": "user-pref",
        "confidence": 0.9,
        "reason": "User preference detected"
    }
    provider.config = MagicMock()
    provider.config.name = "openai"
    provider.config.model = "gpt-4o-mini"
    return provider


@pytest.fixture
def mock_anthropic_provider():
    """Mock Anthropic provider for fallback tests."""
    provider = AsyncMock()
    provider.is_available.return_value = True
    provider.complete.return_value = {
        "should_store": False,
        "category": "skip",
        "confidence": 0.8,
        "reason": "Bug fix already in version control"
    }
    provider.config = MagicMock()
    provider.config.name = "anthropic"
    provider.config.model = "claude-3-5-haiku-20241022"
    return provider


@pytest.fixture
def failing_provider():
    """Mock provider that always fails (for fallback testing)."""
    provider = AsyncMock()
    provider.is_available.return_value = True
    provider.complete.side_effect = Exception("API Error: Rate limit exceeded")
    provider.config = MagicMock()
    provider.config.name = "failing-provider"
    return provider


@pytest.fixture
def mock_filter_config():
    """Mock filter configuration."""
    config = MagicMock()
    config.session = MagicMock()
    config.session.max_context_tokens = 5000
    config.get_sorted_providers.return_value = []
    return config
