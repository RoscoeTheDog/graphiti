"""
Tests for memory filter system (filter_manager, session_manager, llm_provider).
Coverage target: >80% of filter system components
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_server.filter_manager import FilterManager
from mcp_server.session_manager import SessionManager, Session
from mcp_server.llm_provider import LLMProvider, create_provider


# =============================================================================
# FILTER MANAGER TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_filter_disabled_stores_everything(mock_filter_config):
    """Test that when filtering is disabled, everything is stored."""
    # Create session manager with no providers (filtering disabled)
    session_mgr = SessionManager(mock_filter_config)
    filter_mgr = FilterManager(session_mgr)

    assert filter_mgr.enabled == False

    result = await filter_mgr.should_store(
        event_description="Some event",
        context="Some context"
    )

    assert result['should_store'] == True
    assert result['category'] == 'filter_disabled'


@pytest.mark.asyncio
async def test_env_quirk_detection(mock_openai_provider, mock_filter_config):
    """Test that env quirks are correctly detected and marked for storage."""
    # Setup provider to return env-quirk decision
    mock_openai_provider.complete.return_value = {
        "should_store": True,
        "category": "env-quirk",
        "confidence": 0.95,
        "reason": "OS-specific timeout configuration"
    }

    # Create session manager with mocked provider
    session_mgr = MagicMock()
    session = MagicMock()
    session.provider = mock_openai_provider
    session.session_id = "test-session"
    session.query_count = 0
    session.context_tokens = 0
    session_mgr.get_or_create_session.return_value = session

    filter_mgr = FilterManager(session_mgr)
    filter_mgr.enabled = True  # Enable filtering

    result = await filter_mgr.should_store(
        event_description="Neo4j timeout fixed by setting NEO4J_TIMEOUT=60 in .env",
        context="Edited .env (gitignored file)"
    )

    assert result['should_store'] == True
    assert result['category'] == 'env-quirk'
    assert result.get('confidence', 0) >= 0.9
    mock_openai_provider.complete.assert_called_once()


@pytest.mark.asyncio
async def test_bug_fix_detection(mock_openai_provider, mock_filter_config):
    """Test that bug fixes in code are detected and marked to skip."""
    # Setup provider to return skip decision
    mock_openai_provider.complete.return_value = {
        "should_store": False,
        "category": "bug-in-code",
        "confidence": 0.92,
        "reason": "Bug fix now in version control"
    }

    session_mgr = MagicMock()
    session = MagicMock()
    session.provider = mock_openai_provider
    session.session_id = "test-session"
    session.query_count = 0
    session.context_tokens = 0
    session_mgr.get_or_create_session.return_value = session

    filter_mgr = FilterManager(session_mgr)
    filter_mgr.enabled = True

    result = await filter_mgr.should_store(
        event_description="Fixed infinite loop in parseData()",
        context="Edited src/parser.py, committed to git"
    )

    assert result['should_store'] == False
    assert result['category'] == 'bug-in-code'


@pytest.mark.asyncio
async def test_graceful_degradation_on_error(mock_filter_config):
    """Test that system degrades gracefully when filter fails."""
    session_mgr = MagicMock()
    session_mgr.get_or_create_session.side_effect = RuntimeError("No providers available")

    filter_mgr = FilterManager(session_mgr)
    filter_mgr.enabled = True

    # Should default to storing when filter fails
    result = await filter_mgr.should_store("test", "test")

    assert result['should_store'] == True  # Safe default
    assert result['category'] == 'filter_error'


# =============================================================================
# SESSION MANAGER TESTS
# =============================================================================

def test_session_manager_initialization(mock_filter_config):
    """Test SessionManager initializes with no providers when none available."""
    session_mgr = SessionManager(mock_filter_config)

    assert len(session_mgr.providers) == 0
    assert len(session_mgr.sessions) == 0


def test_session_manager_with_providers(mock_openai_provider, mock_filter_config):
    """Test SessionManager initialization with available providers."""
    # Mock the config to return a provider config
    provider_config = MagicMock()
    provider_config.name = "openai"
    provider_config.model = "gpt-4o-mini"
    mock_filter_config.get_sorted_providers.return_value = [provider_config]

    # Patch create_provider to return our mock
    with patch('mcp_server.session_manager.create_provider', return_value=mock_openai_provider):
        session_mgr = SessionManager(mock_filter_config)

        assert len(session_mgr.providers) == 1
        assert session_mgr.providers[0] == mock_openai_provider


def test_session_creation_and_retrieval(mock_openai_provider, mock_filter_config):
    """Test creating and retrieving sessions."""
    # Setup
    provider_config = MagicMock()
    provider_config.name = "openai"
    provider_config.model = "gpt-4o-mini"
    mock_filter_config.get_sorted_providers.return_value = [provider_config]

    with patch('mcp_server.session_manager.create_provider', return_value=mock_openai_provider):
        session_mgr = SessionManager(mock_filter_config)

        # Create new session (auto-generated ID)
        session1 = session_mgr.get_or_create_session()
        assert session1 is not None
        assert session1.session_id in session_mgr.sessions

        # Retrieve existing session
        session1_again = session_mgr.get_or_create_session(session1.session_id)
        assert session1_again.session_id == session1.session_id

        # Create another session with explicit ID
        session2 = session_mgr.get_or_create_session("custom-session-id")
        assert session2.session_id == "custom-session-id"
        assert len(session_mgr.sessions) == 2


def test_session_context_cleanup(mock_openai_provider, mock_filter_config):
    """Test session context resets when threshold is exceeded."""
    provider_config = MagicMock()
    provider_config.name = "openai"
    mock_filter_config.get_sorted_providers.return_value = [provider_config]
    mock_filter_config.session.max_context_tokens = 100

    with patch('mcp_server.session_manager.create_provider', return_value=mock_openai_provider):
        session_mgr = SessionManager(mock_filter_config)

        # Create session and simulate high token usage
        session = session_mgr.get_or_create_session("test-session")
        session.context_tokens = 150  # Exceed threshold

        # Next retrieval should reset context
        session_again = session_mgr.get_or_create_session("test-session")
        assert session_again.context_tokens == 0
        assert session_again.query_count == 0


def test_session_cleanup(mock_openai_provider, mock_filter_config):
    """Test session cleanup removes sessions."""
    provider_config = MagicMock()
    provider_config.name = "openai"
    mock_filter_config.get_sorted_providers.return_value = [provider_config]

    with patch('mcp_server.session_manager.create_provider', return_value=mock_openai_provider):
        session_mgr = SessionManager(mock_filter_config)

        # Create session
        session = session_mgr.get_or_create_session("test-session")
        assert "test-session" in session_mgr.sessions

        # Cleanup
        session_mgr.cleanup_session("test-session")
        assert "test-session" not in session_mgr.sessions


# =============================================================================
# SESSION CLASS TESTS
# =============================================================================

def test_session_should_cleanup():
    """Test Session.should_cleanup logic."""
    provider = MagicMock()
    session = Session("test-id", provider)

    # Below threshold
    session.context_tokens = 100
    assert session.should_cleanup(200) == False

    # Above threshold
    session.context_tokens = 300
    assert session.should_cleanup(200) == True


def test_session_reset_context():
    """Test Session.reset_context resets counters."""
    provider = MagicMock()
    session = Session("test-id", provider)

    session.context_tokens = 1000
    session.query_count = 50

    session.reset_context()

    assert session.context_tokens == 0
    assert session.query_count == 0


# Run with: pytest tests/test_filter_system.py -v --cov=mcp_server.filter_manager --cov=mcp_server.session_manager
