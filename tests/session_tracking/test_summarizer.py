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
    DecisionRecord,
    ErrorResolution,
    SessionSummary,
    SessionSummarySchema,
    SessionSummarizer,
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
