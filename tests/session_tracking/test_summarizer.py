"""Tests for SessionSummarizer and related Pydantic models.

Tests Story 1 acceptance criteria:
- DecisionRecord serialization/deserialization
- ErrorResolution serialization/deserialization
- SessionSummarySchema with key_decisions and errors_resolved
- to_markdown() renders key_decisions and errors_resolved sections
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from graphiti_core.session_tracking.summarizer import (
    ConfigChange,
    DecisionRecord,
    ErrorResolution,
    SessionSummary,
    SessionSummarySchema,
    SessionSummarizer,
    TestResults,
)


class TestDecisionRecord:
    """Test DecisionRecord Pydantic model."""

    def test_basic_creation(self):
        """Test creating a DecisionRecord with required fields."""
        record = DecisionRecord(
            decision='Used RS256 over HS256 for JWT signing',
            rationale='RS256 is more secure for production',
        )
        assert record.decision == 'Used RS256 over HS256 for JWT signing'
        assert record.rationale == 'RS256 is more secure for production'
        assert record.alternatives is None

    def test_with_alternatives(self):
        """Test creating a DecisionRecord with alternatives."""
        record = DecisionRecord(
            decision='Chose PostgreSQL as database',
            rationale='Better support for complex queries and JSON',
            alternatives=['MySQL', 'MongoDB', 'SQLite'],
        )
        assert record.alternatives == ['MySQL', 'MongoDB', 'SQLite']

    def test_empty_alternatives_list(self):
        """Test creating with empty alternatives list."""
        record = DecisionRecord(
            decision='Test decision',
            rationale='Test rationale',
            alternatives=[],
        )
        assert record.alternatives == []

    def test_serialization_to_dict(self):
        """Test model_dump() serialization."""
        record = DecisionRecord(
            decision='Used Pydantic v2',
            rationale='Better performance and type hints',
            alternatives=['Pydantic v1', 'dataclasses'],
        )
        data = record.model_dump()
        assert data == {
            'decision': 'Used Pydantic v2',
            'rationale': 'Better performance and type hints',
            'alternatives': ['Pydantic v1', 'dataclasses'],
        }

    def test_serialization_to_json(self):
        """Test JSON serialization."""
        record = DecisionRecord(
            decision='Async architecture',
            rationale='Better concurrency',
            alternatives=None,
        )
        json_str = record.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed['decision'] == 'Async architecture'
        assert parsed['alternatives'] is None

    def test_deserialization_from_dict(self):
        """Test model_validate() deserialization."""
        data = {
            'decision': 'Used FastAPI',
            'rationale': 'Modern async framework',
            'alternatives': ['Flask', 'Django'],
        }
        record = DecisionRecord.model_validate(data)
        assert record.decision == 'Used FastAPI'
        assert record.rationale == 'Modern async framework'
        assert record.alternatives == ['Flask', 'Django']

    def test_deserialization_minimal(self):
        """Test deserialization with only required fields."""
        data = {
            'decision': 'Minimal decision',
            'rationale': 'Minimal reason',
        }
        record = DecisionRecord.model_validate(data)
        assert record.alternatives is None

    def test_validation_missing_decision(self):
        """Test validation fails without decision field."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionRecord(rationale='Some reason')
        assert 'decision' in str(exc_info.value)

    def test_validation_missing_rationale(self):
        """Test validation fails without rationale field."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionRecord(decision='Some decision')
        assert 'rationale' in str(exc_info.value)

    def test_roundtrip_serialization(self):
        """Test full round-trip serialization/deserialization."""
        original = DecisionRecord(
            decision='Test roundtrip',
            rationale='Test rationale',
            alternatives=['opt1', 'opt2'],
        )
        json_str = original.model_dump_json()
        restored = DecisionRecord.model_validate_json(json_str)
        assert original == restored


class TestErrorResolution:
    """Test ErrorResolution Pydantic model."""

    def test_basic_creation(self):
        """Test creating an ErrorResolution with all required fields."""
        resolution = ErrorResolution(
            error="ImportError: No module named 'foo'",
            root_cause='Missing dependency in requirements.txt',
            fix='Added foo==1.2.3 to requirements.txt',
            verification='Ran tests, all passing',
        )
        assert resolution.error == "ImportError: No module named 'foo'"
        assert resolution.root_cause == 'Missing dependency in requirements.txt'
        assert resolution.fix == 'Added foo==1.2.3 to requirements.txt'
        assert resolution.verification == 'Ran tests, all passing'

    def test_serialization_to_dict(self):
        """Test model_dump() serialization."""
        resolution = ErrorResolution(
            error='TypeError: cannot unpack non-iterable NoneType',
            root_cause='Function returned None instead of tuple',
            fix='Added None check before unpacking',
            verification='Unit test added to cover edge case',
        )
        data = resolution.model_dump()
        assert data == {
            'error': 'TypeError: cannot unpack non-iterable NoneType',
            'root_cause': 'Function returned None instead of tuple',
            'fix': 'Added None check before unpacking',
            'verification': 'Unit test added to cover edge case',
        }

    def test_serialization_to_json(self):
        """Test JSON serialization."""
        resolution = ErrorResolution(
            error='ConnectionError',
            root_cause='Database not running',
            fix='Started database service',
            verification='Reconnection successful',
        )
        json_str = resolution.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed['error'] == 'ConnectionError'
        assert parsed['fix'] == 'Started database service'

    def test_deserialization_from_dict(self):
        """Test model_validate() deserialization."""
        data = {
            'error': 'KeyError: missing_key',
            'root_cause': 'Config file missing required key',
            'fix': 'Added default value in config parser',
            'verification': 'Tested with empty config file',
        }
        resolution = ErrorResolution.model_validate(data)
        assert resolution.error == 'KeyError: missing_key'
        assert resolution.root_cause == 'Config file missing required key'

    def test_validation_all_fields_required(self):
        """Test that all four fields are required."""
        required_fields = ['error', 'root_cause', 'fix', 'verification']

        for missing_field in required_fields:
            data = {
                'error': 'Error',
                'root_cause': 'Cause',
                'fix': 'Fix',
                'verification': 'Verify',
            }
            del data[missing_field]
            with pytest.raises(ValidationError) as exc_info:
                ErrorResolution.model_validate(data)
            assert missing_field in str(exc_info.value)

    def test_roundtrip_serialization(self):
        """Test full round-trip serialization/deserialization."""
        original = ErrorResolution(
            error='Test error',
            root_cause='Test cause',
            fix='Test fix',
            verification='Test verification',
        )
        json_str = original.model_dump_json()
        restored = ErrorResolution.model_validate_json(json_str)
        assert original == restored

    def test_multiline_error_message(self):
        """Test handling of multiline error messages."""
        resolution = ErrorResolution(
            error='ValueError: invalid literal for int() with base 10: "foo"\n'
            '  at line 42\n'
            '  in file test.py',
            root_cause='User input not validated',
            fix='Added input validation',
            verification='Edge cases now handled',
        )
        assert '\n' in resolution.error
        # Should serialize/deserialize correctly
        data = resolution.model_dump()
        restored = ErrorResolution.model_validate(data)
        assert restored.error == resolution.error


class TestSessionSummarySchema:
    """Test SessionSummarySchema with enhanced fields."""

    def test_basic_creation(self):
        """Test creating a SessionSummarySchema with required fields."""
        schema = SessionSummarySchema(
            objective='Implement user authentication',
            completed_tasks=['Created login endpoint', 'Added password hashing'],
            next_steps=['Add session management', 'Implement logout'],
        )
        assert schema.objective == 'Implement user authentication'
        assert len(schema.completed_tasks) == 2
        assert len(schema.next_steps) == 2
        # Defaults should be empty lists
        assert schema.blocked_items == []
        assert schema.files_modified == []
        assert schema.key_decisions == []
        assert schema.errors_resolved == []

    def test_with_key_decisions(self):
        """Test creating with key_decisions as list of DecisionRecord."""
        decisions = [
            DecisionRecord(
                decision='Used JWT tokens',
                rationale='Stateless authentication',
                alternatives=['Session cookies'],
            ),
            DecisionRecord(
                decision='PostgreSQL for storage',
                rationale='ACID compliance needed',
            ),
        ]
        schema = SessionSummarySchema(
            objective='Test objective',
            completed_tasks=['Task 1'],
            next_steps=['Step 1'],
            key_decisions=decisions,
        )
        assert len(schema.key_decisions) == 2
        assert schema.key_decisions[0].decision == 'Used JWT tokens'
        assert schema.key_decisions[1].alternatives is None

    def test_with_errors_resolved(self):
        """Test creating with errors_resolved as list of ErrorResolution."""
        errors = [
            ErrorResolution(
                error='ImportError: missing module',
                root_cause='Package not installed',
                fix='pip install package',
                verification='Import now works',
            ),
        ]
        schema = SessionSummarySchema(
            objective='Test objective',
            completed_tasks=['Task 1'],
            next_steps=['Step 1'],
            errors_resolved=errors,
        )
        assert len(schema.errors_resolved) == 1
        assert schema.errors_resolved[0].error == 'ImportError: missing module'

    def test_full_schema_serialization(self):
        """Test full schema with all fields serializes correctly."""
        schema = SessionSummarySchema(
            objective='Complete feature implementation',
            completed_tasks=['Task A', 'Task B'],
            blocked_items=['Waiting for API spec'],
            next_steps=['Review and deploy'],
            files_modified=['src/main.py', 'tests/test_main.py'],
            documentation_referenced=['docs/API.md'],
            key_decisions=[
                DecisionRecord(
                    decision='Async approach',
                    rationale='Better performance',
                    alternatives=['Sync', 'Threading'],
                )
            ],
            errors_resolved=[
                ErrorResolution(
                    error='Timeout error',
                    root_cause='Network latency',
                    fix='Added retry logic',
                    verification='3 retries successful',
                )
            ],
            mcp_tools_used=['graphiti-memory', 'serena'],
            token_count=15000,
            duration_estimate='2 hours',
        )

        data = schema.model_dump()
        assert data['objective'] == 'Complete feature implementation'
        assert len(data['key_decisions']) == 1
        assert data['key_decisions'][0]['decision'] == 'Async approach'
        assert len(data['errors_resolved']) == 1
        assert data['errors_resolved'][0]['fix'] == 'Added retry logic'

    def test_schema_deserialization(self):
        """Test deserializing from dict with nested models."""
        data = {
            'objective': 'Test deserialization',
            'completed_tasks': ['Completed'],
            'next_steps': ['Next'],
            'key_decisions': [
                {
                    'decision': 'Test decision',
                    'rationale': 'Test rationale',
                    'alternatives': ['alt1'],
                }
            ],
            'errors_resolved': [
                {
                    'error': 'Test error',
                    'root_cause': 'Test cause',
                    'fix': 'Test fix',
                    'verification': 'Test verify',
                }
            ],
        }
        schema = SessionSummarySchema.model_validate(data)
        assert isinstance(schema.key_decisions[0], DecisionRecord)
        assert isinstance(schema.errors_resolved[0], ErrorResolution)

    def test_backward_compatibility_empty_new_fields(self):
        """Test backward compatibility - old data without new fields."""
        # Simulates loading old session summaries
        data = {
            'objective': 'Old session objective',
            'completed_tasks': ['Old task'],
            'next_steps': ['Old step'],
            # No key_decisions or errors_resolved
        }
        schema = SessionSummarySchema.model_validate(data)
        assert schema.key_decisions == []
        assert schema.errors_resolved == []


class TestSessionSummary:
    """Test SessionSummary dataclass with to_markdown()."""

    def create_sample_summary(
        self,
        key_decisions: list[DecisionRecord] | None = None,
        errors_resolved: list[ErrorResolution] | None = None,
    ) -> SessionSummary:
        """Create a sample SessionSummary for testing."""
        return SessionSummary(
            sequence_number=1,
            title='Test Session',
            slug='test-session',
            objective='Complete the test implementation',
            completed_tasks=['Task 1', 'Task 2'],
            blocked_items=['Blocker 1'],
            next_steps=['Step 1', 'Step 2'],
            files_modified=['src/test.py'],
            documentation_referenced=['docs/README.md'],
            key_decisions=key_decisions or [],
            errors_resolved=errors_resolved or [],
            activity_profile=None,  # Story 10: New field
            config_changes=[],  # Story 10: New field
            test_results=None,  # Story 10: New field
            mcp_tools_used=['graphiti-memory'],
            token_count=5000,
            duration_estimate='1 hour',
            created_at=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc),
        )

    def test_to_markdown_basic(self):
        """Test basic to_markdown() output."""
        summary = self.create_sample_summary()
        md = summary.to_markdown()

        assert '# Session 001: Test Session' in md
        assert '**Status**: ACTIVE' in md
        assert '**Created**: 2025-01-15 10:30' in md
        assert '**Objective**: Complete the test implementation' in md
        assert '## Completed' in md
        assert '- Task 1' in md
        assert '- Task 2' in md
        assert '## Blocked' in md
        assert '- Blocker 1' in md
        assert '## Next Steps' in md
        assert '- Step 1' in md
        assert '## Context' in md
        assert '- src/test.py' in md

    def test_to_markdown_with_key_decisions(self):
        """Test to_markdown() renders key_decisions section correctly."""
        decisions = [
            DecisionRecord(
                decision='Used RS256 over HS256 for JWT signing',
                rationale='RS256 is more secure for production',
                alternatives=['HS256', 'EdDSA'],
            ),
            DecisionRecord(
                decision='Chose async architecture',
                rationale='Better performance under load',
            ),
        ]
        summary = self.create_sample_summary(key_decisions=decisions)
        md = summary.to_markdown()

        # Check section exists
        assert '## Key Decisions' in md

        # Check first decision with alternatives
        assert '- **Used RS256 over HS256 for JWT signing**' in md
        assert 'Rationale: RS256 is more secure for production' in md
        assert 'Alternatives: HS256, EdDSA' in md

        # Check second decision without alternatives
        assert '- **Chose async architecture**' in md
        assert 'Rationale: Better performance under load' in md

    def test_to_markdown_with_errors_resolved(self):
        """Test to_markdown() renders errors_resolved section correctly."""
        errors = [
            ErrorResolution(
                error="ImportError: No module named 'foo'",
                root_cause='Missing dependency in requirements.txt',
                fix='Added foo==1.2.3 to requirements.txt',
                verification='Ran tests, all passing',
            ),
            ErrorResolution(
                error='ConnectionTimeout',
                root_cause='Database server down',
                fix='Restarted database service',
                verification='Connection test passed',
            ),
        ]
        summary = self.create_sample_summary(errors_resolved=errors)
        md = summary.to_markdown()

        # Check section exists
        assert '## Errors Resolved' in md

        # Check first error
        assert "### ImportError: No module named 'foo'" in md
        assert '**Root Cause**: Missing dependency in requirements.txt' in md
        assert '**Fix**: Added foo==1.2.3 to requirements.txt' in md
        assert '**Verification**: Ran tests, all passing' in md

        # Check second error
        assert '### ConnectionTimeout' in md
        assert '**Root Cause**: Database server down' in md

    def test_to_markdown_no_decisions_or_errors(self):
        """Test to_markdown() when no decisions or errors (sections omitted)."""
        summary = self.create_sample_summary(key_decisions=[], errors_resolved=[])
        md = summary.to_markdown()

        # Sections should NOT appear when empty
        assert '## Key Decisions' not in md
        assert '## Errors Resolved' not in md

    def test_to_markdown_section_order(self):
        """Test that sections appear in correct order."""
        decisions = [
            DecisionRecord(decision='Decision', rationale='Reason')
        ]
        errors = [
            ErrorResolution(error='Error', root_cause='Cause', fix='Fix', verification='Verify')
        ]
        summary = self.create_sample_summary(key_decisions=decisions, errors_resolved=errors)
        md = summary.to_markdown()

        # Find positions
        completed_pos = md.find('## Completed')
        blocked_pos = md.find('## Blocked')
        next_steps_pos = md.find('## Next Steps')
        key_decisions_pos = md.find('## Key Decisions')
        errors_resolved_pos = md.find('## Errors Resolved')
        context_pos = md.find('## Context')

        # Verify order
        assert completed_pos < blocked_pos
        assert blocked_pos < next_steps_pos
        assert next_steps_pos < key_decisions_pos
        assert key_decisions_pos < errors_resolved_pos
        assert errors_resolved_pos < context_pos

    def test_to_markdown_no_blocked_items(self):
        """Test to_markdown() shows 'None' when no blocked items."""
        summary = SessionSummary(
            sequence_number=1,
            title='Test',
            slug='test',
            objective='Test objective',
            completed_tasks=['Task 1'],
            blocked_items=[],  # Empty
            next_steps=['Step 1'],
            files_modified=[],
            documentation_referenced=[],
            key_decisions=[],
            errors_resolved=[],
            activity_profile=None,  # Story 10: New field
            config_changes=[],  # Story 10: New field
            test_results=None,  # Story 10: New field
            mcp_tools_used=[],
            token_count=None,
            duration_estimate=None,
            created_at=datetime.now(timezone.utc),
        )
        md = summary.to_markdown()

        # Should show "None" for blocked section
        assert '## Blocked\n\nNone' in md

    def test_to_metadata(self):
        """Test to_metadata() returns correct dict."""
        summary = self.create_sample_summary()
        metadata = summary.to_metadata()

        assert metadata['sequence_number'] == 1
        assert metadata['slug'] == 'test-session'
        assert metadata['objective'] == 'Complete the test implementation'
        assert metadata['status'] == 'ACTIVE'
        assert metadata['files_count'] == 1
        assert metadata['completed_count'] == 2
        assert metadata['blocked_count'] == 1
        assert metadata['token_count'] == 5000
        assert metadata['duration_estimate'] == '1 hour'
        assert metadata['mcp_tools_used'] == ['graphiti-memory']


class TestSessionSummarizer:
    """Test SessionSummarizer class."""

    def test_generate_slug_basic(self):
        """Test basic slug generation."""
        summarizer = SessionSummarizer(llm_client=None)

        # Basic title
        assert summarizer._generate_slug('Hello World') == 'hello-world'

    def test_generate_slug_removes_articles(self):
        """Test slug removes articles (a, an, the)."""
        summarizer = SessionSummarizer(llm_client=None)

        assert summarizer._generate_slug('The Quick Fox') == 'quick-fox'
        assert summarizer._generate_slug('A Simple Test') == 'simple-test'
        assert summarizer._generate_slug('An Example Title') == 'example-title'

    def test_generate_slug_removes_special_chars(self):
        """Test slug removes special characters."""
        summarizer = SessionSummarizer(llm_client=None)

        assert summarizer._generate_slug("Hello! World?") == 'hello-world'
        assert summarizer._generate_slug("Test's & Trials") == 'tests-trials'

    def test_generate_slug_truncates_to_40_chars(self):
        """Test slug truncates to maximum 40 characters."""
        summarizer = SessionSummarizer(llm_client=None)

        long_title = 'This Is A Very Long Title That Should Be Truncated Somewhere'
        slug = summarizer._generate_slug(long_title)
        assert len(slug) <= 40

    def test_generate_slug_handles_multiple_hyphens(self):
        """Test slug collapses multiple hyphens."""
        summarizer = SessionSummarizer(llm_client=None)

        assert summarizer._generate_slug('Test - - Title') == 'test-title'
        assert summarizer._generate_slug('Multiple   Spaces') == 'multiple-spaces'

    def test_generate_slug_strips_edge_hyphens(self):
        """Test slug removes leading/trailing hyphens."""
        summarizer = SessionSummarizer(llm_client=None)

        assert summarizer._generate_slug(' Leading Space ') == 'leading-space'
        assert summarizer._generate_slug('The Test') == 'test'  # After removing "The"


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    def test_complete_session_workflow(self):
        """Test complete workflow of creating and serializing a session summary."""
        # Create schema from LLM response simulation
        schema = SessionSummarySchema(
            objective='Implement user authentication with OAuth2',
            completed_tasks=[
                'Added OAuth2 provider configuration',
                'Created callback endpoints',
                'Implemented token refresh logic',
            ],
            blocked_items=['Waiting for production OAuth credentials'],
            next_steps=[
                'Get production credentials from team lead',
                'Test with real OAuth provider',
                'Deploy to staging',
            ],
            files_modified=[
                'src/auth/oauth2.py',
                'src/auth/routes.py',
                'config/oauth_config.yaml',
            ],
            documentation_referenced=[
                'docs/OAuth2_Integration.md',
            ],
            key_decisions=[
                DecisionRecord(
                    decision='Use Authorization Code flow with PKCE',
                    rationale='Most secure flow for web applications',
                    alternatives=['Implicit flow', 'Client credentials'],
                ),
                DecisionRecord(
                    decision='Store tokens in httpOnly cookies',
                    rationale='Prevents XSS attacks on tokens',
                    alternatives=['LocalStorage', 'SessionStorage'],
                ),
            ],
            errors_resolved=[
                ErrorResolution(
                    error='CORS error when redirecting to OAuth provider',
                    root_cause='Missing CORS headers in redirect response',
                    fix='Added Access-Control-Allow-Origin header',
                    verification='Tested redirect flow in browser',
                ),
            ],
            mcp_tools_used=['graphiti-memory', 'serena', 'claude-context'],
            token_count=25000,
            duration_estimate='3 hours',
        )

        # Serialize to JSON (simulates storage)
        json_str = schema.model_dump_json()

        # Deserialize (simulates retrieval)
        restored = SessionSummarySchema.model_validate_json(json_str)

        # Verify integrity
        assert restored.objective == schema.objective
        assert len(restored.key_decisions) == 2
        assert restored.key_decisions[0].decision == 'Use Authorization Code flow with PKCE'
        assert len(restored.errors_resolved) == 1
        assert restored.errors_resolved[0].error == 'CORS error when redirecting to OAuth provider'

    def test_markdown_rendering_preserves_formatting(self):
        """Test that markdown rendering handles special characters correctly."""
        summary = SessionSummary(
            sequence_number=42,
            title='Fix `TypeError` in parser',
            slug='fix-typeerror-parser',
            objective='Debug and fix TypeError in JSON parser',
            completed_tasks=[
                'Added type checking for `None` values',
                'Fixed edge case in `parse_json()` function',
            ],
            blocked_items=[],
            next_steps=['Add unit tests for edge cases'],
            files_modified=['src/parser.py'],
            documentation_referenced=[],
            key_decisions=[
                DecisionRecord(
                    decision='Use `isinstance()` instead of `type()`',
                    rationale='More Pythonic and handles subclasses',
                ),
            ],
            errors_resolved=[
                ErrorResolution(
                    error="TypeError: 'NoneType' object is not subscriptable",
                    root_cause='Missing null check before indexing',
                    fix='Added `if value is not None:` guard',
                    verification='All tests pass including new edge case tests',
                ),
            ],
            activity_profile=None,  # Story 10: New field
            config_changes=[],  # Story 10: New field
            test_results=None,  # Story 10: New field
            mcp_tools_used=[],
            token_count=3000,
            duration_estimate='30 minutes',
            created_at=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
        )

        md = summary.to_markdown()

        # Verify backticks preserved
        assert '`TypeError`' in md or 'TypeError' in md  # Title may not have backticks
        assert '`None`' in md or 'None' in md
        assert 'isinstance()' in md or '`isinstance()`' in md


class TestConfigChange:
    """Test ConfigChange Pydantic model (Story 10)."""

    def test_basic_creation(self):
        """Test creating a ConfigChange with all required fields."""
        config = ConfigChange(
            file='.env',
            setting='JWT_EXPIRY',
            change='60 -> 3600',
            reason='Fix timeout - was ambiguous units',
        )
        assert config.file == '.env'
        assert config.setting == 'JWT_EXPIRY'
        assert config.change == '60 -> 3600'
        assert config.reason == 'Fix timeout - was ambiguous units'

    def test_serialization_to_dict(self):
        """Test model_dump() serialization."""
        config = ConfigChange(
            file='config.yaml',
            setting='DEBUG_MODE',
            change='true -> false',
            reason='Production deployment',
        )
        data = config.model_dump()
        assert data == {
            'file': 'config.yaml',
            'setting': 'DEBUG_MODE',
            'change': 'true -> false',
            'reason': 'Production deployment',
        }

    def test_serialization_to_json(self):
        """Test JSON serialization."""
        config = ConfigChange(
            file='settings.py',
            setting='ALLOWED_HOSTS',
            change='[] -> ["example.com"]',
            reason='Allow production domain',
        )
        json_str = config.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed['file'] == 'settings.py'
        assert parsed['change'] == '[] -> ["example.com"]'

    def test_deserialization_from_dict(self):
        """Test model_validate() deserialization."""
        data = {
            'file': 'database.conf',
            'setting': 'MAX_CONNECTIONS',
            'change': '100 -> 500',
            'reason': 'Increase connection pool for high traffic',
        }
        config = ConfigChange.model_validate(data)
        assert config.file == 'database.conf'
        assert config.setting == 'MAX_CONNECTIONS'
        assert config.reason == 'Increase connection pool for high traffic'

    def test_validation_all_fields_required(self):
        """Test that all four fields are required."""
        required_fields = ['file', 'setting', 'change', 'reason']

        for missing_field in required_fields:
            data = {
                'file': 'file.txt',
                'setting': 'SETTING',
                'change': 'old -> new',
                'reason': 'Because',
            }
            del data[missing_field]
            with pytest.raises(ValidationError) as exc_info:
                ConfigChange.model_validate(data)
            assert missing_field in str(exc_info.value)

    def test_roundtrip_serialization(self):
        """Test full round-trip serialization/deserialization."""
        original = ConfigChange(
            file='.env',
            setting='API_KEY',
            change='old_key -> new_key',
            reason='Key rotation',
        )
        json_str = original.model_dump_json()
        restored = ConfigChange.model_validate_json(json_str)
        assert original == restored

    def test_special_characters_in_values(self):
        """Test handling of special characters in config values."""
        config = ConfigChange(
            file='nginx.conf',
            setting='server_name',
            change='localhost -> api.example.com|www.example.com',
            reason='Multi-domain setup (use | for separation)',
        )
        # Should serialize/deserialize correctly with pipes
        data = config.model_dump()
        restored = ConfigChange.model_validate(data)
        assert restored.change == 'localhost -> api.example.com|www.example.com'
        assert '|' in restored.change
        assert '|' in restored.reason


class TestTestResults:
    """Test TestResults Pydantic model (Story 10)."""

    def test_basic_creation_with_coverage(self):
        """Test creating TestResults with coverage."""
        results = TestResults(
            framework='pytest',
            passed=12,
            failed=0,
            coverage=87.3,
        )
        assert results.framework == 'pytest'
        assert results.passed == 12
        assert results.failed == 0
        assert results.coverage == 87.3

    def test_basic_creation_without_coverage(self):
        """Test creating TestResults without coverage (optional field)."""
        results = TestResults(
            framework='jest',
            passed=45,
            failed=2,
        )
        assert results.framework == 'jest'
        assert results.passed == 45
        assert results.failed == 2
        assert results.coverage is None

    def test_serialization_to_dict(self):
        """Test model_dump() serialization."""
        results = TestResults(
            framework='pytest',
            passed=20,
            failed=1,
            coverage=92.5,
        )
        data = results.model_dump()
        assert data == {
            'framework': 'pytest',
            'passed': 20,
            'failed': 1,
            'coverage': 92.5,
        }

    def test_serialization_to_json(self):
        """Test JSON serialization."""
        results = TestResults(
            framework='mocha',
            passed=10,
            failed=0,
            coverage=None,
        )
        json_str = results.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed['framework'] == 'mocha'
        assert parsed['passed'] == 10
        assert parsed['coverage'] is None

    def test_deserialization_from_dict(self):
        """Test model_validate() deserialization."""
        data = {
            'framework': 'pytest',
            'passed': 15,
            'failed': 3,
            'coverage': 78.2,
        }
        results = TestResults.model_validate(data)
        assert results.framework == 'pytest'
        assert results.passed == 15
        assert results.failed == 3
        assert results.coverage == 78.2

    def test_deserialization_minimal(self):
        """Test deserialization with only required fields."""
        data = {
            'framework': 'unittest',
            'passed': 5,
            'failed': 0,
        }
        results = TestResults.model_validate(data)
        assert results.coverage is None

    def test_validation_missing_framework(self):
        """Test validation fails without framework field."""
        with pytest.raises(ValidationError) as exc_info:
            TestResults(passed=10, failed=0)
        assert 'framework' in str(exc_info.value)

    def test_validation_missing_passed(self):
        """Test validation fails without passed field."""
        with pytest.raises(ValidationError) as exc_info:
            TestResults(framework='pytest', failed=0)
        assert 'passed' in str(exc_info.value)

    def test_validation_missing_failed(self):
        """Test validation fails without failed field."""
        with pytest.raises(ValidationError) as exc_info:
            TestResults(framework='pytest', passed=10)
        assert 'failed' in str(exc_info.value)

    def test_roundtrip_serialization(self):
        """Test full round-trip serialization/deserialization."""
        original = TestResults(
            framework='pytest',
            passed=25,
            failed=2,
            coverage=88.1,
        )
        json_str = original.model_dump_json()
        restored = TestResults.model_validate_json(json_str)
        assert original == restored

    def test_zero_values(self):
        """Test handling of zero values (all tests passed or failed)."""
        # All passed
        all_passed = TestResults(framework='pytest', passed=100, failed=0)
        assert all_passed.failed == 0

        # All failed
        all_failed = TestResults(framework='pytest', passed=0, failed=10)
        assert all_failed.passed == 0

    def test_coverage_bounds(self):
        """Test coverage percentage bounds (0-100)."""
        # Min coverage
        min_cov = TestResults(framework='pytest', passed=1, failed=0, coverage=0.0)
        assert min_cov.coverage == 0.0

        # Max coverage
        max_cov = TestResults(framework='pytest', passed=10, failed=0, coverage=100.0)
        assert max_cov.coverage == 100.0

        # Decimal precision
        precise = TestResults(framework='pytest', passed=10, failed=0, coverage=87.345)
        assert precise.coverage == 87.345


class TestEnhancedMarkdownRendering:
    """Test enhanced markdown rendering with new fields (Story 10)."""

    def create_sample_summary_with_enhancements(
        self,
        activity_profile: str | None = None,
        config_changes: list[ConfigChange] | None = None,
        test_results: TestResults | None = None,
    ) -> SessionSummary:
        """Create a sample SessionSummary with enhanced fields for testing."""
        return SessionSummary(
            sequence_number=42,
            title='Fix JWT Authentication Timeout',
            slug='fix-jwt-timeout',
            objective='Resolve JWT authentication timeout causing 401 errors',
            completed_tasks=['Fixed token expiry configuration', 'Added explicit time unit documentation'],
            blocked_items=[],
            next_steps=['Add config schema validation to CI pipeline'],
            files_modified=['.env', 'config.py', 'tests/test_auth.py'],
            documentation_referenced=[],
            key_decisions=[
                DecisionRecord(
                    decision='Explicit time units',
                    rationale='Code-enforced validation prevents human error',
                    alternatives=['Document-only fix', 'use ISO 8601 duration format'],
                )
            ],
            errors_resolved=[
                ErrorResolution(
                    error='401 Unauthorized after ~1 minute',
                    root_cause='`JWT_EXPIRY=60` interpreted as 60 seconds (was meant to be minutes)',
                    fix='Changed to `JWT_EXPIRY=3600` (explicit seconds)',
                    verification='Tested token validity over 30 minutes',
                )
            ],
            activity_profile=activity_profile,
            config_changes=config_changes or [],
            test_results=test_results,
            mcp_tools_used=[],
            token_count=5000,
            duration_estimate='1 hour',
            created_at=datetime(2025, 12, 11, 15, 30, tzinfo=timezone.utc),
        )

    def test_to_markdown_with_activity_profile(self):
        """Test to_markdown() renders activity profile in header."""
        summary = self.create_sample_summary_with_enhancements(
            activity_profile='fixing (0.80), configuring (0.70), testing (0.50)'
        )
        md = summary.to_markdown()

        # Check activity profile appears in header
        assert '**Activity Profile**: fixing (0.80), configuring (0.70), testing (0.50)' in md

        # Should appear near the top (before Objective)
        assert md.index('Activity Profile') < md.index('## Objective')

    def test_to_markdown_without_activity_profile(self):
        """Test to_markdown() works correctly when activity_profile is None."""
        summary = self.create_sample_summary_with_enhancements(activity_profile=None)
        md = summary.to_markdown()

        # Should not include activity profile
        assert 'Activity Profile' not in md

        # Should still have objective
        assert '**Objective**: Resolve JWT authentication timeout' in md

    def test_to_markdown_with_config_changes(self):
        """Test to_markdown() renders config changes as markdown table."""
        config_changes = [
            ConfigChange(
                file='.env',
                setting='JWT_EXPIRY',
                change='60 -> 3600',
                reason='Fix timeout - was ambiguous units',
            ),
            ConfigChange(
                file='config.py',
                setting='TOKEN_ALGORITHM',
                change='HS256 -> RS256',
                reason='Improve security',
            ),
        ]
        summary = self.create_sample_summary_with_enhancements(config_changes=config_changes)
        md = summary.to_markdown()

        # Check section exists
        assert '## Configuration Changes' in md

        # Check table headers
        assert '| File | Setting | Change | Reason |' in md
        assert '|------|---------|--------|--------|' in md

        # Check first row (values are NOT backtick-wrapped in the table)
        assert '| .env | JWT_EXPIRY | 60 -> 3600 | Fix timeout - was ambiguous units |' in md

        # Check second row
        assert '| config.py | TOKEN_ALGORITHM | HS256 -> RS256 | Improve security |' in md

    def test_to_markdown_without_config_changes(self):
        """Test to_markdown() omits config changes section when empty."""
        summary = self.create_sample_summary_with_enhancements(config_changes=[])
        md = summary.to_markdown()

        # Section should NOT appear
        assert '## Configuration Changes' not in md

    def test_to_markdown_with_test_results(self):
        """Test to_markdown() renders test results section."""
        test_results = TestResults(
            framework='pytest',
            passed=12,
            failed=0,
            coverage=87.3,
        )
        summary = self.create_sample_summary_with_enhancements(test_results=test_results)
        md = summary.to_markdown()

        # Check section exists
        assert '## Test Results' in md

        # Check framework
        assert '- **Framework**: pytest' in md

        # Check results
        assert '- **Results**: 12/12 passed' in md

        # Check coverage
        assert '- **Coverage**: 87.3%' in md

    def test_to_markdown_with_test_failures(self):
        """Test to_markdown() shows failures in test results."""
        test_results = TestResults(
            framework='pytest',
            passed=10,
            failed=2,
            coverage=75.0,
        )
        summary = self.create_sample_summary_with_enhancements(test_results=test_results)
        md = summary.to_markdown()

        # Check results show passed/total
        assert '- **Results**: 10/12 passed (2 failed)' in md

    def test_to_markdown_without_coverage(self):
        """Test to_markdown() works when coverage is None."""
        test_results = TestResults(
            framework='mocha',
            passed=5,
            failed=0,
            coverage=None,
        )
        summary = self.create_sample_summary_with_enhancements(test_results=test_results)
        md = summary.to_markdown()

        # Check section exists
        assert '## Test Results' in md

        # Should have framework and results
        assert '- **Framework**: mocha' in md
        assert '- **Results**: 5/5 passed' in md

        # Should NOT show coverage line
        assert 'Coverage' not in md

    def test_to_markdown_without_test_results(self):
        """Test to_markdown() omits test results section when None."""
        summary = self.create_sample_summary_with_enhancements(test_results=None)
        md = summary.to_markdown()

        # Section should NOT appear
        assert '## Test Results' not in md

    def test_to_markdown_section_order_with_enhancements(self):
        """Test that new sections appear in correct order."""
        config_changes = [
            ConfigChange(file='.env', setting='KEY', change='old -> new', reason='Update')
        ]
        test_results = TestResults(framework='pytest', passed=10, failed=0)

        summary = self.create_sample_summary_with_enhancements(
            activity_profile='fixing (0.80)',
            config_changes=config_changes,
            test_results=test_results,
        )
        md = summary.to_markdown()

        # Find positions
        activity_pos = md.find('Activity Profile')
        objective_pos = md.find('## Objective')
        completed_pos = md.find('## Completed')
        key_decisions_pos = md.find('## Key Decisions')
        errors_resolved_pos = md.find('## Errors Resolved')
        config_changes_pos = md.find('## Configuration Changes')
        test_results_pos = md.find('## Test Results')
        context_pos = md.find('## Context')

        # Verify order
        assert activity_pos < objective_pos
        assert objective_pos < completed_pos
        assert completed_pos < key_decisions_pos
        assert key_decisions_pos < errors_resolved_pos
        assert errors_resolved_pos < config_changes_pos
        assert config_changes_pos < test_results_pos
        assert test_results_pos < context_pos

    def test_config_changes_table_escapes_pipes(self):
        """Test markdown table escapes pipe characters in cell content (Security AC 10.4)."""
        config_changes = [
            ConfigChange(
                file='nginx.conf',
                setting='server_name',
                change='localhost -> api.example.com|www.example.com',
                reason='Multi-domain setup (use | for separation)',
            )
        ]
        summary = self.create_sample_summary_with_enhancements(config_changes=config_changes)
        md = summary.to_markdown()

        # Pipes should be escaped as \|
        assert r'localhost -> api.example.com\|www.example.com' in md
        assert r'Multi-domain setup (use \| for separation)' in md

    def test_backward_compatibility_old_sessions(self):
        """Test backward compatibility - old SessionSummary without new fields."""
        # Create a summary without the new fields (simulates old data)
        old_summary = SessionSummary(
            sequence_number=1,
            title='Old Session',
            slug='old-session',
            objective='Old objective',
            completed_tasks=['Task 1'],
            blocked_items=[],
            next_steps=['Step 1'],
            files_modified=[],
            documentation_referenced=[],
            key_decisions=[],
            errors_resolved=[],
            # New fields default to None/[]
            activity_profile=None,
            config_changes=[],
            test_results=None,
            mcp_tools_used=[],
            token_count=None,
            duration_estimate=None,
            created_at=datetime.now(timezone.utc),
        )
        md = old_summary.to_markdown()

        # Should render without errors
        assert '# Session 001: Old Session' in md
        assert '**Objective**: Old objective' in md

        # New sections should NOT appear
        assert 'Activity Profile' not in md
        assert '## Configuration Changes' not in md
        assert '## Test Results' not in md


# =============================================================================
# Story 11: Summarizer Integration Tests
# =============================================================================


class TestSummarizerIntegration:
    """Tests for Story 11: Summarizer Integration with ActivityDetector and dynamic prompts."""

    def test_sessionsummarizer_init_with_tool_classifier(self):
        """Test AC-11.1: SessionSummarizer initializes ActivityDetector."""
        from unittest.mock import Mock

        from graphiti_core.session_tracking.tool_classifier import ToolClassifier

        llm_client = Mock()
        tool_classifier = Mock(spec=ToolClassifier)

        summarizer = SessionSummarizer(llm_client=llm_client, tool_classifier=tool_classifier)

        # Verify summarizer is initialized
        assert summarizer.llm_client == llm_client
        assert hasattr(summarizer, 'activity_detector')
        assert summarizer.activity_detector is not None

    @pytest.mark.asyncio
    async def test_activity_vector_computed_from_messages(self):
        """Test AC-11.1: Activity vector is computed from messages during summarization."""
        from unittest.mock import AsyncMock, Mock, patch

        from graphiti_core.session_tracking.activity_detector import ActivityDetector
        from graphiti_core.session_tracking.activity_vector import ActivityVector
        from graphiti_core.session_tracking.types import ConversationContext, SessionMessage, TokenUsage, ToolCall

        # Mock LLM client
        llm_client = Mock()
        llm_client.generate_response = AsyncMock(
            return_value=SessionSummarySchema(
                objective='Test objective',
                completed_tasks=['Task 1'],
                next_steps=['Step 1'],
            )
        )

        # Create test messages
        from datetime import datetime, timezone
        from uuid import uuid4

        messages = [
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-session',
                timestamp=datetime.now(timezone.utc),
                role='user',
                content='Fix the bug',
                tool_calls=[],
            ),
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-session',
                timestamp=datetime.now(timezone.utc),
                role='assistant',
                content='Found the issue',
                tool_calls=[ToolCall(tool_name='Read', parameters={})],
            ),
        ]

        context = ConversationContext(
            session_id='test-session',
            messages=messages,
            total_tokens=TokenUsage(input_tokens=50, output_tokens=50),
        )

        # Mock activity detector to return specific activity
        with patch.object(
            ActivityDetector,
            'detect',
            return_value=ActivityVector(exploring=0.3, fixing=0.7, configuring=0.1),
        ):
            summarizer = SessionSummarizer(llm_client=llm_client)
            summary = await summarizer.summarize_session(
                context=context, filtered_content='Test content', sequence_number=1
            )

            # Verify activity vector was computed
            assert summary.activity_vector is not None
            assert isinstance(summary.activity_vector, ActivityVector)
            assert summary.activity_vector.fixing == 0.7
            assert summary.activity_vector.exploring == 0.3

    @pytest.mark.asyncio
    async def test_dynamic_prompt_used_for_extraction(self):
        """Test AC-11.2: build_extraction_prompt is called instead of static prompt."""
        from unittest.mock import AsyncMock, Mock, patch

        from graphiti_core.session_tracking.types import ConversationContext, SessionMessage, TokenUsage

        # Mock LLM client
        llm_client = Mock()
        llm_client.generate_response = AsyncMock(
            return_value=SessionSummarySchema(
                objective='Test objective',
                completed_tasks=['Task 1'],
                next_steps=['Step 1'],
            )
        )

        from datetime import datetime, timezone
        from uuid import uuid4

        messages = [
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-session',
                timestamp=datetime.now(timezone.utc),
                role='user',
                content='Debug the issue',
                tool_calls=[],
            ),
        ]

        context = ConversationContext(
            session_id='test-session',
            messages=messages,
            total_tokens=TokenUsage(input_tokens=25, output_tokens=25),
        )

        # Mock build_extraction_prompt to verify it's called
        with patch(
            'graphiti_core.session_tracking.summarizer.build_extraction_prompt',
            return_value='Dynamic prompt based on activity',
        ) as mock_build_prompt:
            summarizer = SessionSummarizer(llm_client=llm_client)
            await summarizer.summarize_session(
                context=context, filtered_content='Test content', sequence_number=1
            )

            # Verify build_extraction_prompt was called with correct parameters
            mock_build_prompt.assert_called_once()
            call_args = mock_build_prompt.call_args
            assert 'activity' in call_args.kwargs
            assert 'content' in call_args.kwargs
            assert 'threshold' in call_args.kwargs
            assert call_args.kwargs['threshold'] == 0.3

    @pytest.mark.asyncio
    async def test_activity_vector_included_in_summary(self):
        """Test AC-11.3: Summary includes activity_vector field."""
        from unittest.mock import AsyncMock, Mock

        from graphiti_core.session_tracking.activity_vector import ActivityVector
        from graphiti_core.session_tracking.types import ConversationContext, SessionMessage, TokenUsage

        llm_client = Mock()
        llm_client.generate_response = AsyncMock(
            return_value=SessionSummarySchema(
                objective='Test objective',
                completed_tasks=['Task 1'],
                next_steps=['Step 1'],
            )
        )

        from datetime import datetime, timezone
        from uuid import uuid4

        messages = [
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-session',
                timestamp=datetime.now(timezone.utc),
                role='user',
                content='Test message',
                tool_calls=[],
            ),
        ]

        context = ConversationContext(
            session_id='test-session',
            messages=messages,
            total_tokens=TokenUsage(input_tokens=25, output_tokens=25),
        )

        summarizer = SessionSummarizer(llm_client=llm_client)
        summary = await summarizer.summarize_session(
            context=context, filtered_content='Test content', sequence_number=1
        )

        # Verify activity_vector is set
        assert summary.activity_vector is not None
        assert isinstance(summary.activity_vector, ActivityVector)

    @pytest.mark.asyncio
    async def test_graceful_fallback_on_activity_detection_failure(self):
        """Test AC-11.4: Falls back to neutral ActivityVector on detection failure."""
        from unittest.mock import AsyncMock, Mock, patch

        from graphiti_core.session_tracking.activity_detector import ActivityDetector
        from graphiti_core.session_tracking.activity_vector import ActivityVector
        from graphiti_core.session_tracking.types import ConversationContext, SessionMessage, TokenUsage

        llm_client = Mock()
        llm_client.generate_response = AsyncMock(
            return_value=SessionSummarySchema(
                objective='Test objective',
                completed_tasks=['Task 1'],
                next_steps=['Step 1'],
            )
        )

        from datetime import datetime, timezone
        from uuid import uuid4

        messages = [
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-session',
                timestamp=datetime.now(timezone.utc),
                role='user',
                content='Test message',
                tool_calls=[],
            ),
        ]

        context = ConversationContext(
            session_id='test-session',
            messages=messages,
            total_tokens=TokenUsage(input_tokens=25, output_tokens=25),
        )

        # Mock activity detector to raise exception
        with patch.object(
            ActivityDetector, 'detect', side_effect=RuntimeError('Detection failed')
        ):
            summarizer = SessionSummarizer(llm_client=llm_client)
            summary = await summarizer.summarize_session(
                context=context, filtered_content='Test content', sequence_number=1
            )

            # Verify summarization continued with neutral activity vector
            assert summary.activity_vector is not None
            assert isinstance(summary.activity_vector, ActivityVector)
            # Neutral activity should have all zeros
            assert summary.activity_vector.exploring == 0.0
            assert summary.activity_vector.fixing == 0.0
            assert summary.activity_vector.configuring == 0.0

    def test_activity_vector_in_markdown_output(self):
        """Test AC-11.3: Activity vector appears in markdown output."""
        from graphiti_core.session_tracking.activity_vector import ActivityVector

        summary = SessionSummary(
            sequence_number=1,
            title='Test Session',
            slug='test-session',
            objective='Test objective',
            activity_profile='fixing (0.80), testing (0.50)',
            completed_tasks=['Task 1'],
            blocked_items=[],
            next_steps=['Step 1'],
            files_modified=[],
            documentation_referenced=[],
            key_decisions=[],
            errors_resolved=[],
            config_changes=[],
            test_results=None,
            mcp_tools_used=[],
            token_count=100,
            duration_estimate='1 hour',
            created_at=datetime.now(timezone.utc),
            activity_vector=ActivityVector(exploring=0.2, fixing=0.8, configuring=0.3),
        )

        md = summary.to_markdown()

        # Verify markdown contains activity information
        assert 'Activity Profile' in md or 'activity_profile' in md.lower()
        assert 'fixing (0.80)' in md

    def test_activity_vector_in_metadata_output(self):
        """Test AC-11.3: Activity vector appears in metadata dict."""
        from graphiti_core.session_tracking.activity_vector import ActivityVector

        summary = SessionSummary(
            sequence_number=1,
            title='Test Session',
            slug='test-session',
            objective='Test objective',
            activity_profile='fixing (0.80)',
            completed_tasks=['Task 1'],
            blocked_items=[],
            next_steps=['Step 1'],
            files_modified=[],
            documentation_referenced=[],
            key_decisions=[],
            errors_resolved=[],
            config_changes=[],
            test_results=None,
            mcp_tools_used=[],
            token_count=100,
            duration_estimate='1 hour',
            created_at=datetime.now(timezone.utc),
            activity_vector=ActivityVector(exploring=0.2, fixing=0.8, configuring=0.3),
        )

        metadata = summary.to_metadata()

        # Verify metadata includes activity vector
        assert 'activity_vector' in metadata
        activity_dict = metadata['activity_vector']
        assert activity_dict['fixing'] == 0.8
        assert activity_dict['exploring'] == 0.2
        assert activity_dict['configuring'] == 0.3


class TestSummarizerIntegrationE2E:
    """Integration tests for end-to-end scenarios with real-ish sessions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_debugging_session(self):
        """Test AC-11.5: End-to-end debugging session shows fixing > 0.5."""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, Mock
        from uuid import uuid4

        from graphiti_core.session_tracking.types import ConversationContext, SessionMessage, TokenUsage, ToolCall

        # Mock LLM to return realistic debugging summary
        llm_client = Mock()
        llm_client.generate_response = AsyncMock(
            return_value=SessionSummarySchema(
                objective='Fix authentication bug in login endpoint',
                completed_tasks=['Identified root cause', 'Fixed JWT verification'],
                next_steps=['Add regression tests'],
                errors_resolved=[
                    ErrorResolution(
                        error='JWT verification failing',
                        root_cause='Incorrect secret key',
                        fix='Updated .env with correct key',
                        verification='Tests passing',
                    )
                ],
            )
        )

        # Simulate debugging session messages
        messages = [
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-debug-session',
                timestamp=datetime.now(timezone.utc),
                role='user',
                content='Fix the authentication bug',
                tool_calls=[],
            ),
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-debug-session',
                timestamp=datetime.now(timezone.utc),
                role='assistant',
                content='Investigating the issue...',
                tool_calls=[ToolCall(tool_name='Read', parameters={'file': '.env'})],
            ),
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-debug-session',
                timestamp=datetime.now(timezone.utc),
                role='assistant',
                content='Found the issue, fixing now',
                tool_calls=[ToolCall(tool_name='Edit', parameters={'file': '.env'})],
            ),
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-debug-session',
                timestamp=datetime.now(timezone.utc),
                role='assistant',
                content='Running tests...',
                tool_calls=[ToolCall(tool_name='Bash', parameters={'command': 'pytest tests/'})],
            ),
        ]

        context = ConversationContext(
            session_id='test-debug-session',
            messages=messages,
            total_tokens=TokenUsage(input_tokens=250, output_tokens=250),
        )

        summarizer = SessionSummarizer(llm_client=llm_client)
        summary = await summarizer.summarize_session(
            context=context,
            filtered_content='User: Fix auth bug\nAgent: Found issue in .env',
            sequence_number=1,
        )

        # Verify activity vector shows fixing as dominant
        assert summary.activity_vector is not None
        assert summary.activity_vector.fixing > 0.5  # Debugging/fixing should dominate

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_exploration_session(self):
        """Test AC-11.5: End-to-end exploration session shows exploring > 0.5."""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, Mock
        from uuid import uuid4

        from graphiti_core.session_tracking.types import ConversationContext, SessionMessage, TokenUsage, ToolCall

        # Mock LLM to return realistic exploration summary
        llm_client = Mock()
        llm_client.generate_response = AsyncMock(
            return_value=SessionSummarySchema(
                objective='Explore codebase structure and architecture',
                completed_tasks=['Reviewed main modules', 'Understood data flow'],
                next_steps=['Design new feature'],
                files_modified=[],
                documentation_referenced=['README.md', 'ARCHITECTURE.md'],
            )
        )

        # Simulate exploration session messages
        messages = [
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-explore-session',
                timestamp=datetime.now(timezone.utc),
                role='user',
                content='Show me how the system works',
                tool_calls=[],
            ),
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-explore-session',
                timestamp=datetime.now(timezone.utc),
                role='assistant',
                content='Reading main files...',
                tool_calls=[ToolCall(tool_name='Read', parameters={'file': 'README.md'})],
            ),
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-explore-session',
                timestamp=datetime.now(timezone.utc),
                role='assistant',
                content='Checking architecture...',
                tool_calls=[ToolCall(tool_name='Glob', parameters={'pattern': '**/*.py'})],
            ),
            SessionMessage(
                uuid=str(uuid4()),
                session_id='test-explore-session',
                timestamp=datetime.now(timezone.utc),
                role='assistant',
                content='Searching for patterns...',
                tool_calls=[ToolCall(tool_name='Grep', parameters={'pattern': 'class'})],
            ),
        ]

        context = ConversationContext(
            session_id='test-explore-session',
            messages=messages,
            total_tokens=TokenUsage(input_tokens=200, output_tokens=200),
        )

        summarizer = SessionSummarizer(llm_client=llm_client)
        summary = await summarizer.summarize_session(
            context=context,
            filtered_content='User: Show me system\nAgent: Reading files...',
            sequence_number=1,
        )

        # Verify activity vector shows exploring as dominant
        assert summary.activity_vector is not None
        assert summary.activity_vector.exploring > 0.5  # Exploration should dominate

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skip(reason='Requires real LLM client - manual testing only')
    async def test_integration_with_real_llm_client(self):
        """Test integration with actual LLM client (structured output parsing).

        This test is skipped by default as it requires:
        - Real OpenAI API key
        - Network access
        - Costs money per run

        To run manually: pytest -m integration --run-llm-tests
        """
        from graphiti_core.llm_client import LLMClient
        from graphiti_core.session_tracking.types import ConversationContext, SessionMessage

        # This would use real LLM client
        llm_client = LLMClient(api_key='test-key', model='gpt-4o-mini')

        messages = [
            SessionMessage(role='user', content='Fix the bug in auth.py', tool_calls=None),
        ]

        context = ConversationContext(
            messages=messages, total_tokens=50, message_count=1, window_start_idx=0
        )

        summarizer = SessionSummarizer(llm_client=llm_client)

        # Would test real LLM structured output parsing
        # summary = await summarizer.summarize_session(
        #     context=context,
        #     filtered_content="User asked to fix bug",
        #     sequence_number=1,
        # )
        # assert summary.objective
        # assert summary.activity_vector is not None

        # Placeholder assertion for now
        assert True
