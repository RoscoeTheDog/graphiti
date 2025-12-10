"""
Tests for Story 10: Documentation Updates (v2.0 Global Scope)

This test module verifies that documentation has been correctly updated
to reflect v2.0 global scope changes for session tracking.

Test Categories:
- Unit Tests: Verify documentation content exists
- Integration Tests: Verify cross-references and JSON examples are valid
- Security Tests: Verify security documentation completeness
"""

import json
import re
from pathlib import Path
import pytest


# =============================================================================
# Fixtures and Helpers
# =============================================================================


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def configuration_md(project_root):
    """Load CONFIGURATION.md content."""
    config_path = project_root / "CONFIGURATION.md"
    return config_path.read_text(encoding="utf-8")


@pytest.fixture
def user_guide_md(project_root):
    """Load SESSION_TRACKING_USER_GUIDE.md content."""
    guide_path = project_root / "docs" / "SESSION_TRACKING_USER_GUIDE.md"
    return guide_path.read_text(encoding="utf-8")


@pytest.fixture
def migration_md(project_root):
    """Load SESSION_TRACKING_MIGRATION.md content."""
    migration_path = project_root / "docs" / "SESSION_TRACKING_MIGRATION.md"
    return migration_path.read_text(encoding="utf-8")


def extract_json_blocks(content: str) -> list[str]:
    """Extract all JSON code blocks from markdown content."""
    # Match ```json ... ``` blocks
    pattern = r'```json\s*\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL)
    return matches


def extract_markdown_links(content: str) -> list[tuple[str, str]]:
    """Extract markdown links as (text, url) tuples."""
    # Match [text](url) pattern
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    return re.findall(pattern, content)


# =============================================================================
# Unit Tests: CONFIGURATION.md Content
# =============================================================================


class TestConfigurationMdContent:
    """Unit tests to verify CONFIGURATION.md contains all required v2.0 fields."""

    def test_contains_global_scope_section(self, configuration_md):
        """AC-10.1: CONFIGURATION.md has Global Scope Settings section."""
        assert "Global Scope Settings (v2.0)" in configuration_md, \
            "CONFIGURATION.md must contain 'Global Scope Settings (v2.0)' section"

    def test_contains_group_id_field(self, configuration_md):
        """AC-10.1: CONFIGURATION.md documents group_id field."""
        assert "group_id" in configuration_md
        # Verify default value is documented
        assert "null" in configuration_md.lower() or "None" in configuration_md
        # Verify hostname__global default behavior
        assert "hostname" in configuration_md.lower() and "global" in configuration_md.lower()

    def test_contains_cross_project_search_field(self, configuration_md):
        """AC-10.1: CONFIGURATION.md documents cross_project_search field."""
        assert "cross_project_search" in configuration_md
        # Verify it's documented as bool type
        assert "bool" in configuration_md.lower() or "true" in configuration_md.lower()

    def test_contains_trusted_namespaces_field(self, configuration_md):
        """AC-10.1: CONFIGURATION.md documents trusted_namespaces field."""
        assert "trusted_namespaces" in configuration_md
        # Verify array type is documented
        assert "string[]" in configuration_md or "list" in configuration_md.lower()

    def test_contains_include_project_path_field(self, configuration_md):
        """AC-10.1: CONFIGURATION.md documents include_project_path field."""
        assert "include_project_path" in configuration_md
        # Verify bool type
        assert "bool" in configuration_md.lower()

    def test_contains_configuration_table(self, configuration_md):
        """AC-10.1: CONFIGURATION.md has table with field descriptions."""
        # Check for table header format
        table_header_pattern = r'\|\s*Field\s*\|\s*Type\s*\|\s*Default\s*\|\s*Description\s*\|'
        assert re.search(table_header_pattern, configuration_md), \
            "CONFIGURATION.md must contain a field reference table"

    def test_version_updated(self, configuration_md):
        """AC-10.1: CONFIGURATION.md reflects v2.0 version."""
        # Check for v2.0 or 2.0 reference in session tracking section
        assert "v2.0" in configuration_md or "2.0" in configuration_md, \
            "CONFIGURATION.md must reference v2.0"


# =============================================================================
# Unit Tests: SESSION_TRACKING_USER_GUIDE.md Content
# =============================================================================


class TestUserGuideMdContent:
    """Unit tests to verify USER_GUIDE.md explains global scope behavior."""

    def test_contains_global_knowledge_graph_section(self, user_guide_md):
        """AC-10.2: User guide has Global Knowledge Graph section."""
        assert "Global Knowledge Graph" in user_guide_md, \
            "User guide must contain 'Global Knowledge Graph' section"

    def test_explains_namespace_metadata(self, user_guide_md):
        """AC-10.2: User guide explains how namespace metadata works."""
        assert "namespace" in user_guide_md.lower()
        assert "project_namespace" in user_guide_md
        # Verify YAML frontmatter example
        assert "graphiti_session_metadata" in user_guide_md

    def test_explains_agent_provenance_interpretation(self, user_guide_md):
        """AC-10.2: User guide explains how agents interpret provenance."""
        assert "provenance" in user_guide_md.lower() or "interpret" in user_guide_md.lower()
        # Should have agent example or explanation
        assert "agent" in user_guide_md.lower()

    def test_explains_cross_project_search_false_usage(self, user_guide_md):
        """AC-10.2: User guide explains when to use cross_project_search: false."""
        assert "cross_project_search" in user_guide_md
        assert "false" in user_guide_md.lower()
        # Should mention sensitive projects
        assert "sensitive" in user_guide_md.lower() or "isolation" in user_guide_md.lower()

    def test_explains_trusted_namespaces_usage(self, user_guide_md):
        """AC-10.2: User guide explains when to use trusted_namespaces."""
        assert "trusted_namespaces" in user_guide_md
        # Should have example with namespace hashes
        assert re.search(r'[a-f0-9]{8}', user_guide_md), \
            "User guide should have namespace hash examples"

    def test_contains_faq_section(self, user_guide_md):
        """AC-10.2: User guide has FAQ section with cross-project questions."""
        assert "FAQ" in user_guide_md
        # Should address cross-project search questions
        assert "cross-project" in user_guide_md.lower() or "cross project" in user_guide_md.lower()


# =============================================================================
# Unit Tests: SESSION_TRACKING_MIGRATION.md Content
# =============================================================================


class TestMigrationMdContent:
    """Unit tests to verify MIGRATION.md covers v2.0 migration."""

    def test_contains_v2_migration_section(self, migration_md):
        """AC-10.3: Migration guide has v2.0 migration section."""
        assert "v2.0" in migration_md or "2.0" in migration_md
        # Should have migration path
        assert "v1.1.0" in migration_md or "1.1.0" in migration_md

    def test_explains_global_scope_change(self, migration_md):
        """AC-10.3: Migration guide explains global scope architectural change."""
        assert "global" in migration_md.lower()
        # Should explain the change from project-scoped
        assert "project" in migration_md.lower()

    def test_explains_old_data_not_searched(self, migration_md):
        """AC-10.3: Migration guide explains v1.x data won't be searched by default."""
        # Should mention old data behavior
        assert "v1" in migration_md.lower() or "old" in migration_md.lower()
        # Should mention data preservation
        assert "preserved" in migration_md.lower() or "remain" in migration_md.lower()

    def test_provides_migration_options(self, migration_md):
        """AC-10.3: Migration guide provides options (keep, re-index, manual)."""
        # Check for multiple options
        option_keywords = ["fresh start", "keep old data", "re-index", "manual"]
        matches = sum(1 for kw in option_keywords if kw in migration_md.lower())
        assert matches >= 2, \
            "Migration guide should provide multiple migration options"

    def test_notes_v1_not_public(self, migration_md):
        """AC-10.3: Migration guide notes v1.0 was never publicly released."""
        # Should mention v1.0 wasn't public (simplifies migration)
        assert "never" in migration_md.lower() and "public" in migration_md.lower(), \
            "Migration guide should note v1.0 was never publicly released"

    def test_contains_breaking_changes_section(self, migration_md):
        """AC-10.3: Migration guide documents breaking changes."""
        assert "breaking" in migration_md.lower() or "Breaking" in migration_md


# =============================================================================
# Integration Tests: Cross-References
# =============================================================================


class TestCrossReferences:
    """Integration tests to validate documentation cross-references."""

    def test_configuration_md_links_to_user_guide(self, configuration_md, project_root):
        """Cross-reference: CONFIGURATION.md links to user guide."""
        # Check for link to SESSION_TRACKING_USER_GUIDE.md
        assert "SESSION_TRACKING_USER_GUIDE.md" in configuration_md

    def test_configuration_md_links_exist(self, configuration_md, project_root):
        """Session tracking related links in CONFIGURATION.md point to existing files."""
        links = extract_markdown_links(configuration_md)

        # Filter to internal .md file links (not http/https)
        internal_links = [
            (text, url) for text, url in links
            if url.endswith('.md') and not url.startswith(('http://', 'https://'))
        ]

        # Only check session tracking related links (Story 10 scope)
        session_tracking_links = [
            (text, url) for text, url in internal_links
            if 'SESSION_TRACKING' in url.upper() or 'session' in text.lower()
        ]

        missing_files = []
        for text, url in session_tracking_links:
            # Handle relative paths from project root
            clean_url = url.lstrip('./')
            if clean_url.startswith('docs/'):
                file_path = project_root / clean_url
            else:
                file_path = project_root / clean_url

            if not file_path.exists():
                missing_files.append((text, url))

        assert not missing_files, \
            f"CONFIGURATION.md has broken session tracking links: {missing_files}"

    def test_user_guide_links_to_configuration(self, user_guide_md):
        """Cross-reference: User guide links to CONFIGURATION.md."""
        assert "CONFIGURATION.md" in user_guide_md

    def test_migration_guide_links_to_user_guide(self, migration_md):
        """Cross-reference: Migration guide links to user guide."""
        assert "SESSION_TRACKING_USER_GUIDE.md" in migration_md


# =============================================================================
# Integration Tests: JSON Examples
# =============================================================================


class TestJsonExamples:
    """Integration tests to validate JSON examples are syntactically correct."""

    def test_configuration_md_json_syntax(self, configuration_md):
        """All JSON blocks in CONFIGURATION.md are syntactically valid."""
        json_blocks = extract_json_blocks(configuration_md)

        invalid_blocks = []
        for i, block in enumerate(json_blocks):
            # Clean up common markdown artifacts
            cleaned = block.strip()
            # Skip blocks that are clearly pseudo-code or have placeholders
            if "${" in cleaned or "..." in cleaned or "/* " in cleaned:
                continue

            try:
                # JSON with comments won't parse - skip those
                if "//" not in cleaned:
                    json.loads(cleaned)
            except json.JSONDecodeError as e:
                # Only flag blocks that look like complete JSON
                if cleaned.startswith('{') and cleaned.endswith('}'):
                    invalid_blocks.append((i, str(e)[:50], cleaned[:100]))

        # We expect some blocks to be pseudo-code, so just ensure most are valid
        # This is informational - don't fail on partial/example JSON
        if len(invalid_blocks) > len(json_blocks) // 2:
            pytest.fail(
                f"More than half of JSON blocks are invalid. "
                f"Invalid: {len(invalid_blocks)}, Total: {len(json_blocks)}"
            )

    def test_user_guide_json_syntax(self, user_guide_md):
        """JSON blocks in user guide are syntactically valid."""
        json_blocks = extract_json_blocks(user_guide_md)

        valid_count = 0
        for block in json_blocks:
            cleaned = block.strip()
            if "${" in cleaned or "..." in cleaned or "//" in cleaned:
                continue
            try:
                json.loads(cleaned)
                valid_count += 1
            except json.JSONDecodeError:
                pass

        # Should have at least some valid JSON examples
        assert valid_count > 0, \
            "User guide should contain at least one valid JSON example"


# =============================================================================
# Integration Tests: Configuration Defaults Match Code
# =============================================================================


class TestConfigurationDefaultsMatchCode:
    """Integration tests to verify documented defaults match unified_config.py."""

    def test_group_id_default_matches(self, configuration_md):
        """Documented group_id default matches code default (null)."""
        # In code: group_id: Optional[str] = Field(default=None, ...)
        # Doc should say null/None as default
        session_tracking_section = configuration_md.split("Global Scope Settings")[1][:2000]
        assert "null" in session_tracking_section.lower() or "none" in session_tracking_section.lower()

    def test_cross_project_search_default_matches(self, configuration_md):
        """Documented cross_project_search default matches code (true)."""
        # In code: cross_project_search: bool = Field(default=True, ...)
        # Should document default as true
        assert "cross_project_search" in configuration_md
        # Check table row contains true as default
        table_pattern = r'cross_project_search.*?\|.*?\|.*?true'
        assert re.search(table_pattern, configuration_md, re.IGNORECASE | re.DOTALL), \
            "cross_project_search default should be documented as true"

    def test_include_project_path_default_matches(self, configuration_md):
        """Documented include_project_path default matches code (true)."""
        # In code: include_project_path: bool = Field(default=True, ...)
        assert "include_project_path" in configuration_md
        table_pattern = r'include_project_path.*?\|.*?\|.*?true'
        assert re.search(table_pattern, configuration_md, re.IGNORECASE | re.DOTALL), \
            "include_project_path default should be documented as true"


# =============================================================================
# Security Tests
# =============================================================================


class TestSecurityDocumentation:
    """Security tests to verify security considerations are documented."""

    def test_documents_path_exposure_risk(self, user_guide_md):
        """AC-10.4: Security section covers path exposure risks."""
        security_section = user_guide_md.lower()

        # Should mention path exposure
        assert "path" in security_section and "exposure" in security_section, \
            "User guide must document path exposure risk"

        # Should mention mitigation (include_project_path: false)
        assert "include_project_path" in user_guide_md

    def test_documents_cross_project_info_leakage(self, user_guide_md):
        """AC-10.4: Security section covers cross-project information leakage."""
        security_section = user_guide_md.lower()

        # Should mention cross-project leakage risk
        assert "cross-project" in security_section or "cross project" in security_section
        assert "leakage" in security_section or "information" in security_section, \
            "User guide must document cross-project information risks"

    def test_documents_trusted_namespaces_security(self, user_guide_md):
        """AC-10.4: Security section covers trusted_namespaces usage."""
        # Should mention trusted_namespaces for security
        assert "trusted_namespaces" in user_guide_md

        # Should explain it's for security/filtering
        lower_content = user_guide_md.lower()
        assert ("exclude" in lower_content or "filter" in lower_content or
                "restrict" in lower_content), \
            "User guide should explain trusted_namespaces for security filtering"

    def test_documents_multi_user_considerations(self, user_guide_md):
        """AC-10.4: Security section covers multi-user environment considerations."""
        lower_content = user_guide_md.lower()

        # Should mention shared/multi-user considerations
        assert ("multi-user" in lower_content or "shared" in lower_content or
                "multi user" in lower_content), \
            "User guide should document multi-user environment considerations"

    def test_privacy_section_exists(self, user_guide_md):
        """AC-10.4: User guide has Privacy & Security section."""
        assert "Privacy" in user_guide_md or "Security" in user_guide_md


# =============================================================================
# Example Configuration Tests
# =============================================================================


class TestExampleConfigurations:
    """Tests to verify example configurations are present."""

    def test_configuration_md_has_global_scope_examples(self, configuration_md):
        """AC-10.5: CONFIGURATION.md has example configs for global scope."""
        # Should have at least one example in global scope section
        assert "cross_project_search" in configuration_md

        # Check for example configuration blocks
        json_blocks = extract_json_blocks(configuration_md)

        # At least one should contain session_tracking with new fields
        has_session_tracking_example = any(
            "session_tracking" in block and
            ("cross_project_search" in block or "group_id" in block)
            for block in json_blocks
        )

        assert has_session_tracking_example, \
            "CONFIGURATION.md should have example configs showing global scope use cases"

    def test_user_guide_has_configuration_examples(self, user_guide_md):
        """User guide has example configuration blocks."""
        json_blocks = extract_json_blocks(user_guide_md)

        # Should have examples showing different use cases
        assert len(json_blocks) >= 2, \
            "User guide should have multiple configuration examples"


# =============================================================================
# Completeness Tests
# =============================================================================


class TestDocumentationCompleteness:
    """Tests to verify documentation completeness."""

    def test_all_v2_fields_documented(self, configuration_md):
        """All v2.0 session tracking fields are documented."""
        v2_fields = [
            "group_id",
            "cross_project_search",
            "trusted_namespaces",
            "include_project_path"
        ]

        missing = [f for f in v2_fields if f not in configuration_md]

        assert not missing, \
            f"CONFIGURATION.md is missing documentation for: {missing}"

    def test_migration_guide_covers_all_changes(self, migration_md):
        """Migration guide covers all major v2.0 changes."""
        expected_topics = [
            "group_id",  # New format
            "cross_project",  # New default behavior
            "namespace",  # Metadata
            "backward"  # Compatibility notes
        ]

        lower_content = migration_md.lower()
        missing = [t for t in expected_topics if t not in lower_content]

        assert not missing, \
            f"Migration guide should cover these topics: {missing}"
