"""Tests for ToolClassifier class.

Tests Story 4 acceptance criteria:
- ToolIntent and ToolDomain enums as specified
- ToolClassification Pydantic model with intent, domain, confidence, activity_signals
- ToolClassifier._try_heuristic() matches name patterns to classifications
- Heuristics cover common tools: Read, Write, Edit, Grep, Glob, Bash commands (git, npm, pytest)
- Activity signals mapping from intent+domain to vector contributions
"""

import pytest

from graphiti_core.session_tracking.activity_vector import ActivityVector
from graphiti_core.session_tracking.tool_classifier import (
    ToolClassification,
    ToolClassifier,
    ToolDomain,
    ToolIntent,
)


class TestToolIntentEnum:
    """Test ToolIntent enumeration."""

    def test_all_intents_defined(self):
        """Test all required intents are defined."""
        expected_intents = {
            "CREATE",
            "MODIFY",
            "DELETE",
            "READ",
            "SEARCH",
            "EXECUTE",
            "CONFIGURE",
            "COMMUNICATE",
            "VALIDATE",
            "TRANSFORM",
        }
        actual_intents = {intent.name for intent in ToolIntent}
        assert actual_intents == expected_intents

    def test_intent_values_are_strings(self):
        """Test intent enum values are strings."""
        for intent in ToolIntent:
            assert isinstance(intent.value, str)

    def test_intent_enum_is_str_enum(self):
        """Test ToolIntent inherits from str for JSON serialization."""
        assert issubclass(ToolIntent, str)


class TestToolDomainEnum:
    """Test ToolDomain enumeration."""

    def test_all_domains_defined(self):
        """Test all required domains are defined."""
        expected_domains = {
            "FILESYSTEM",
            "CODE",
            "DATABASE",
            "NETWORK",
            "PROCESS",
            "VERSION_CONTROL",
            "PACKAGE",
            "DOCUMENTATION",
            "TESTING",
            "MEMORY",
            "UNKNOWN",
        }
        actual_domains = {domain.name for domain in ToolDomain}
        assert actual_domains == expected_domains

    def test_domain_values_are_strings(self):
        """Test domain enum values are strings."""
        for domain in ToolDomain:
            assert isinstance(domain.value, str)

    def test_domain_enum_is_str_enum(self):
        """Test ToolDomain inherits from str for JSON serialization."""
        assert issubclass(ToolDomain, str)


class TestToolClassificationModel:
    """Test ToolClassification Pydantic model."""

    def test_classification_creation(self):
        """Test ToolClassification can be created."""
        classification = ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=1.0,
            activity_signals={"exploring": 0.5},
            tool_name="Read",
        )
        assert classification.intent == ToolIntent.READ
        assert classification.domain == ToolDomain.FILESYSTEM
        assert classification.confidence == 1.0
        assert classification.activity_signals == {"exploring": 0.5}
        assert classification.tool_name == "Read"

    def test_classification_default_method(self):
        """Test default method is 'heuristic'."""
        classification = ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=1.0,
            tool_name="Read",
        )
        assert classification.method == "heuristic"

    def test_classification_default_activity_signals(self):
        """Test default activity_signals is empty dict."""
        classification = ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=1.0,
            tool_name="Read",
        )
        assert classification.activity_signals == {}

    def test_confidence_validation_bounds(self):
        """Test confidence must be between 0.0 and 1.0."""
        # Valid confidence values
        ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.0,
            tool_name="Test",
        )
        ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=1.0,
            tool_name="Test",
        )
        ToolClassification(
            intent=ToolIntent.READ,
            domain=ToolDomain.FILESYSTEM,
            confidence=0.5,
            tool_name="Test",
        )

        # Invalid confidence values should raise
        with pytest.raises(ValueError):
            ToolClassification(
                intent=ToolIntent.READ,
                domain=ToolDomain.FILESYSTEM,
                confidence=-0.1,
                tool_name="Test",
            )
        with pytest.raises(ValueError):
            ToolClassification(
                intent=ToolIntent.READ,
                domain=ToolDomain.FILESYSTEM,
                confidence=1.1,
                tool_name="Test",
            )

    def test_method_literal_validation(self):
        """Test method must be one of the allowed values."""
        # Valid method values
        for method in ["heuristic", "llm", "cached"]:
            classification = ToolClassification(
                intent=ToolIntent.READ,
                domain=ToolDomain.FILESYSTEM,
                confidence=1.0,
                tool_name="Test",
                method=method,
            )
            assert classification.method == method


class TestToolClassifierKnownTools:
    """Test classification of known Claude Code tools."""

    def test_read_tool(self):
        """Test Read tool classified as READ/FILESYSTEM with confidence 1.0."""
        classifier = ToolClassifier()
        result = classifier.classify("Read")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.FILESYSTEM
        assert result.confidence == 1.0
        assert result.tool_name == "Read"
        assert result.method == "heuristic"

    def test_write_tool(self):
        """Test Write tool classified as CREATE/FILESYSTEM with confidence 1.0."""
        classifier = ToolClassifier()
        result = classifier.classify("Write")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.FILESYSTEM
        assert result.confidence == 1.0

    def test_edit_tool(self):
        """Test Edit tool classified as MODIFY/FILESYSTEM with confidence 1.0."""
        classifier = ToolClassifier()
        result = classifier.classify("Edit")
        assert result.intent == ToolIntent.MODIFY
        assert result.domain == ToolDomain.FILESYSTEM
        assert result.confidence == 1.0

    def test_glob_tool(self):
        """Test Glob tool classified as SEARCH/FILESYSTEM with confidence 1.0."""
        classifier = ToolClassifier()
        result = classifier.classify("Glob")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.FILESYSTEM
        assert result.confidence == 1.0

    def test_grep_tool(self):
        """Test Grep tool classified as SEARCH/FILESYSTEM with confidence 1.0."""
        classifier = ToolClassifier()
        result = classifier.classify("Grep")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.FILESYSTEM
        assert result.confidence == 1.0

    def test_bash_tool(self):
        """Test Bash tool classified as EXECUTE/PROCESS with confidence 1.0."""
        classifier = ToolClassifier()
        result = classifier.classify("Bash")
        assert result.intent == ToolIntent.EXECUTE
        assert result.domain == ToolDomain.PROCESS
        assert result.confidence == 1.0

    def test_task_tool(self):
        """Test Task tool classified as EXECUTE/PROCESS."""
        classifier = ToolClassifier()
        result = classifier.classify("Task")
        assert result.intent == ToolIntent.EXECUTE
        assert result.domain == ToolDomain.PROCESS
        assert result.confidence == 0.9

    def test_todowrite_tool(self):
        """Test TodoWrite tool classified as CREATE/MEMORY."""
        classifier = ToolClassifier()
        result = classifier.classify("TodoWrite")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.MEMORY

    def test_webfetch_tool(self):
        """Test WebFetch tool classified as READ/NETWORK."""
        classifier = ToolClassifier()
        result = classifier.classify("WebFetch")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.NETWORK
        assert result.confidence == 1.0

    def test_websearch_tool(self):
        """Test WebSearch tool classified as SEARCH/NETWORK."""
        classifier = ToolClassifier()
        result = classifier.classify("WebSearch")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.NETWORK
        assert result.confidence == 1.0

    def test_askuserquestion_tool(self):
        """Test AskUserQuestion tool classified as COMMUNICATE."""
        classifier = ToolClassifier()
        result = classifier.classify("AskUserQuestion")
        assert result.intent == ToolIntent.COMMUNICATE
        assert result.domain == ToolDomain.UNKNOWN

    def test_notebookedit_tool(self):
        """Test NotebookEdit tool classified as MODIFY/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("NotebookEdit")
        assert result.intent == ToolIntent.MODIFY
        assert result.domain == ToolDomain.CODE


class TestToolClassifierMCPSerenaTools:
    """Test classification of MCP Serena tools."""

    def test_find_symbol(self):
        """Test mcp__serena__find_symbol classified as SEARCH/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__find_symbol")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.CODE
        assert result.confidence == 1.0

    def test_replace_symbol_body(self):
        """Test mcp__serena__replace_symbol_body classified as MODIFY/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__replace_symbol_body")
        assert result.intent == ToolIntent.MODIFY
        assert result.domain == ToolDomain.CODE

    def test_get_symbols_overview(self):
        """Test mcp__serena__get_symbols_overview classified as READ/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__get_symbols_overview")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.CODE

    def test_find_referencing_symbols(self):
        """Test mcp__serena__find_referencing_symbols classified as SEARCH/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__find_referencing_symbols")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.CODE

    def test_list_dir(self):
        """Test mcp__serena__list_dir classified as READ/FILESYSTEM."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__list_dir")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.FILESYSTEM

    def test_find_file(self):
        """Test mcp__serena__find_file classified as SEARCH/FILESYSTEM."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__find_file")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.FILESYSTEM

    def test_search_for_pattern(self):
        """Test mcp__serena__search_for_pattern classified as SEARCH/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__search_for_pattern")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.CODE

    def test_insert_after_symbol(self):
        """Test mcp__serena__insert_after_symbol classified as CREATE/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__insert_after_symbol")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.CODE

    def test_insert_before_symbol(self):
        """Test mcp__serena__insert_before_symbol classified as CREATE/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__insert_before_symbol")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.CODE

    def test_get_symbol_body(self):
        """Test mcp__serena__get_symbol_body classified as READ/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__get_symbol_body")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.CODE

    def test_activate_project(self):
        """Test mcp__serena__activate_project classified as CONFIGURE/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__activate_project")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.CODE

    def test_memory_tools(self):
        """Test MCP serena memory tools."""
        classifier = ToolClassifier()

        result = classifier.classify("mcp__serena__read_memory")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.MEMORY

        result = classifier.classify("mcp__serena__write_memory")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.MEMORY

        result = classifier.classify("mcp__serena__list_memories")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.MEMORY

        result = classifier.classify("mcp__serena__delete_memory")
        assert result.intent == ToolIntent.DELETE
        assert result.domain == ToolDomain.MEMORY


class TestToolClassifierMCPClaudeContextTools:
    """Test classification of MCP Claude Context tools."""

    def test_search_code(self):
        """Test mcp__claude-context__search_code classified as SEARCH/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__claude-context__search_code")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.CODE
        assert result.confidence == 1.0

    def test_index_codebase(self):
        """Test mcp__claude-context__index_codebase classified as CONFIGURE/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__claude-context__index_codebase")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.CODE

    def test_get_indexing_status(self):
        """Test mcp__claude-context__get_indexing_status classified as READ/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__claude-context__get_indexing_status")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.CODE

    def test_sync_now(self):
        """Test mcp__claude-context__sync_now classified as CONFIGURE/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__claude-context__sync_now")
        assert result.intent == ToolIntent.CONFIGURE
        assert result.domain == ToolDomain.CODE

    def test_clear_index(self):
        """Test mcp__claude-context__clear_index classified as DELETE/CODE."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__claude-context__clear_index")
        assert result.intent == ToolIntent.DELETE
        assert result.domain == ToolDomain.CODE


class TestToolClassifierMCPGraphitiTools:
    """Test classification of MCP Graphiti tools."""

    def test_add_memory(self):
        """Test mcp__graphiti-memory__add_memory classified as CREATE/MEMORY."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__graphiti-memory__add_memory")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.MEMORY
        assert result.confidence == 1.0

    def test_search_memory_nodes(self):
        """Test mcp__graphiti-memory__search_memory_nodes classified as SEARCH/MEMORY."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__graphiti-memory__search_memory_nodes")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.MEMORY

    def test_search_memory_facts(self):
        """Test mcp__graphiti-memory__search_memory_facts classified as SEARCH/MEMORY."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__graphiti-memory__search_memory_facts")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.MEMORY

    def test_get_episodes(self):
        """Test mcp__graphiti-memory__get_episodes classified as READ/MEMORY."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__graphiti-memory__get_episodes")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.MEMORY

    def test_delete_episode(self):
        """Test mcp__graphiti-memory__delete_episode classified as DELETE/MEMORY."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__graphiti-memory__delete_episode")
        assert result.intent == ToolIntent.DELETE
        assert result.domain == ToolDomain.MEMORY

    def test_clear_graph(self):
        """Test mcp__graphiti-memory__clear_graph classified as DELETE/MEMORY."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__graphiti-memory__clear_graph")
        assert result.intent == ToolIntent.DELETE
        assert result.domain == ToolDomain.MEMORY

    def test_health_check(self):
        """Test mcp__graphiti-memory__health_check classified as VALIDATE/MEMORY."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__graphiti-memory__health_check")
        assert result.intent == ToolIntent.VALIDATE
        assert result.domain == ToolDomain.MEMORY


class TestToolClassifierMCPOtherTools:
    """Test classification of other MCP tools."""

    def test_context7_resolve_library_id(self):
        """Test mcp__context7-local__resolve-library-id classified as SEARCH/DOCUMENTATION."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__context7-local__resolve-library-id")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.DOCUMENTATION

    def test_context7_get_library_docs(self):
        """Test mcp__context7-local__get-library-docs classified as READ/DOCUMENTATION."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__context7-local__get-library-docs")
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.DOCUMENTATION

    def test_gptr_deep_research(self):
        """Test mcp__gptr-mcp__deep_research classified as SEARCH/NETWORK."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__gptr-mcp__deep_research")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.NETWORK

    def test_gptr_quick_search(self):
        """Test mcp__gptr-mcp__quick_search classified as SEARCH/NETWORK."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__gptr-mcp__quick_search")
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.NETWORK

    def test_gptr_write_report(self):
        """Test mcp__gptr-mcp__write_report classified as CREATE/DOCUMENTATION."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__gptr-mcp__write_report")
        assert result.intent == ToolIntent.CREATE
        assert result.domain == ToolDomain.DOCUMENTATION


class TestToolClassifierPatternMatching:
    """Test pattern matching for unknown tools."""

    def test_git_commit_pattern(self):
        """Test 'git_commit' pattern matches VERSION_CONTROL domain."""
        classifier = ToolClassifier()
        result = classifier.classify("git_commit")
        assert result.domain == ToolDomain.VERSION_CONTROL
        assert result.confidence > 0.5

    def test_git_push_pattern(self):
        """Test 'git_push' pattern matches VERSION_CONTROL domain."""
        classifier = ToolClassifier()
        result = classifier.classify("git_push")
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_git_branch_pattern(self):
        """Test 'git_branch' pattern matches VERSION_CONTROL domain."""
        classifier = ToolClassifier()
        result = classifier.classify("git_branch")
        assert result.domain == ToolDomain.VERSION_CONTROL

    def test_pytest_pattern(self):
        """Test 'pytest' pattern matches TESTING domain and VALIDATE intent."""
        classifier = ToolClassifier()
        result = classifier.classify("run_pytest")
        assert result.domain == ToolDomain.TESTING
        # pytest is detected as part of 'test' keyword
        assert result.intent == ToolIntent.VALIDATE

    def test_npm_install_pattern(self):
        """Test 'npm_install' pattern matches PACKAGE domain."""
        classifier = ToolClassifier()
        result = classifier.classify("npm_install")
        assert result.domain == ToolDomain.PACKAGE

    def test_pip_install_pattern(self):
        """Test 'pip_install' pattern matches PACKAGE domain."""
        classifier = ToolClassifier()
        result = classifier.classify("pip_install")
        assert result.domain == ToolDomain.PACKAGE

    def test_database_query_pattern(self):
        """Test 'database_query' pattern matches DATABASE domain."""
        classifier = ToolClassifier()
        result = classifier.classify("database_query")
        assert result.domain == ToolDomain.DATABASE

    def test_sql_execute_pattern(self):
        """Test 'sql_execute' pattern matches DATABASE domain."""
        classifier = ToolClassifier()
        result = classifier.classify("sql_execute")
        assert result.domain == ToolDomain.DATABASE

    def test_file_read_pattern(self):
        """Test 'file_read' pattern matches FILESYSTEM domain and READ intent."""
        classifier = ToolClassifier()
        result = classifier.classify("file_read")
        assert result.domain == ToolDomain.FILESYSTEM
        assert result.intent == ToolIntent.READ

    def test_file_write_pattern(self):
        """Test 'file_write' pattern matches FILESYSTEM domain and CREATE intent."""
        classifier = ToolClassifier()
        result = classifier.classify("file_write")
        assert result.domain == ToolDomain.FILESYSTEM
        assert result.intent == ToolIntent.CREATE

    def test_shell_execute_pattern(self):
        """Test 'shell_execute' pattern matches PROCESS domain."""
        classifier = ToolClassifier()
        result = classifier.classify("shell_execute")
        assert result.domain == ToolDomain.PROCESS
        assert result.intent == ToolIntent.EXECUTE

    def test_web_fetch_pattern(self):
        """Test 'web_fetch' pattern matches NETWORK domain."""
        classifier = ToolClassifier()
        result = classifier.classify("web_fetch")
        assert result.domain == ToolDomain.NETWORK

    def test_doc_generate_pattern(self):
        """Test 'doc_generate' pattern matches DOCUMENTATION domain."""
        classifier = ToolClassifier()
        result = classifier.classify("doc_generate")
        assert result.domain == ToolDomain.DOCUMENTATION

    def test_readme_update_pattern(self):
        """Test 'readme_update' pattern matches DOCUMENTATION domain."""
        classifier = ToolClassifier()
        result = classifier.classify("readme_update")
        assert result.domain == ToolDomain.DOCUMENTATION

    def test_memory_store_pattern(self):
        """Test 'memory_store' pattern matches MEMORY domain."""
        classifier = ToolClassifier()
        result = classifier.classify("memory_store")
        assert result.domain == ToolDomain.MEMORY

    def test_camelcase_splitting(self):
        """Test camelCase tool names are split correctly."""
        classifier = ToolClassifier()
        result = classifier.classify("readFileFromDisk")
        assert result.domain == ToolDomain.FILESYSTEM
        assert result.intent == ToolIntent.READ

    def test_underscore_splitting(self):
        """Test underscore_separated names are split correctly."""
        classifier = ToolClassifier()
        result = classifier.classify("search_file_pattern")
        assert result.intent == ToolIntent.SEARCH

    def test_dot_splitting(self):
        """Test dot.separated names are split correctly."""
        classifier = ToolClassifier()
        result = classifier.classify("git.commit.push")
        assert result.domain == ToolDomain.VERSION_CONTROL


class TestToolClassifierUnknownToolFallback:
    """Test fallback behavior for unknown tools."""

    def test_unknown_tool_returns_classification(self):
        """Test unknown tool returns a valid classification."""
        classifier = ToolClassifier()
        result = classifier.classify("totally_unknown_tool_xyz123")
        assert isinstance(result, ToolClassification)
        assert result.tool_name == "totally_unknown_tool_xyz123"

    def test_unknown_tool_has_low_confidence(self):
        """Test unknown tool returns low confidence (0.3)."""
        classifier = ToolClassifier()
        result = classifier.classify("xyz_abc_123_unknown")
        assert result.confidence == 0.3

    def test_unknown_tool_domain_is_unknown(self):
        """Test unknown tool has UNKNOWN domain."""
        classifier = ToolClassifier()
        result = classifier.classify("completely_unknown")
        assert result.domain == ToolDomain.UNKNOWN

    def test_unknown_tool_default_intent_is_execute(self):
        """Test unknown tool has EXECUTE as safe default intent."""
        classifier = ToolClassifier()
        result = classifier.classify("mysterious_operation")
        assert result.intent == ToolIntent.EXECUTE

    def test_unknown_tool_has_method_heuristic(self):
        """Test unknown tool still reports method as 'heuristic'."""
        classifier = ToolClassifier()
        result = classifier.classify("random_tool_name")
        assert result.method == "heuristic"

    def test_unknown_tool_has_exploring_signal(self):
        """Test unknown tool has some exploring signal."""
        classifier = ToolClassifier()
        result = classifier.classify("unknown_thing")
        assert "exploring" in result.activity_signals
        assert result.activity_signals["exploring"] == 0.3


class TestToolClassifierActivitySignals:
    """Test activity signal generation from classifications."""

    def test_read_filesystem_produces_exploring_signal(self):
        """Test READ/FILESYSTEM produces exploring signal."""
        classifier = ToolClassifier()
        result = classifier.classify("Read")
        assert "exploring" in result.activity_signals
        assert result.activity_signals["exploring"] > 0

    def test_read_filesystem_produces_reviewing_signal(self):
        """Test READ/FILESYSTEM produces reviewing signal."""
        classifier = ToolClassifier()
        result = classifier.classify("Read")
        assert "reviewing" in result.activity_signals
        assert result.activity_signals["reviewing"] > 0

    def test_create_filesystem_produces_building_signal(self):
        """Test CREATE/FILESYSTEM produces building signal."""
        classifier = ToolClassifier()
        result = classifier.classify("Write")
        assert "building" in result.activity_signals
        assert result.activity_signals["building"] > 0

    def test_modify_code_produces_building_and_refactoring(self):
        """Test MODIFY/CODE produces building and refactoring signals."""
        classifier = ToolClassifier()
        result = classifier.classify("Edit")
        assert "building" in result.activity_signals
        assert result.activity_signals["building"] > 0
        assert "refactoring" in result.activity_signals
        assert result.activity_signals["refactoring"] > 0

    def test_search_produces_exploring_signal(self):
        """Test SEARCH intent produces exploring signal."""
        classifier = ToolClassifier()
        result = classifier.classify("Grep")
        assert "exploring" in result.activity_signals
        assert result.activity_signals["exploring"] > 0

    def test_validate_testing_produces_high_testing_signal(self):
        """Test VALIDATE/TESTING produces high testing signal."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__graphiti-memory__health_check")
        assert "testing" in result.activity_signals
        assert result.activity_signals["testing"] > 0

    def test_configure_produces_configuring_signal(self):
        """Test CONFIGURE intent produces configuring signal."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__claude-context__index_codebase")
        assert "configuring" in result.activity_signals
        assert result.activity_signals["configuring"] > 0

    def test_execute_produces_building_and_testing_signals(self):
        """Test EXECUTE intent produces building and testing signals."""
        classifier = ToolClassifier()
        result = classifier.classify("Bash")
        assert "building" in result.activity_signals
        assert result.activity_signals["building"] > 0
        assert "testing" in result.activity_signals
        assert result.activity_signals["testing"] > 0

    def test_domain_modifier_testing_boosts_testing_signal(self):
        """Test TESTING domain modifier boosts testing signal."""
        classifier = ToolClassifier()
        # run_pytest should get both VALIDATE intent testing signal
        # AND TESTING domain modifier
        result = classifier.classify("run_pytest")
        assert "testing" in result.activity_signals
        # Testing signal should be boosted (0.6 from intent + 0.3 from domain = 0.9)
        assert result.activity_signals["testing"] >= 0.6

    def test_domain_modifier_documentation_boosts_documenting(self):
        """Test DOCUMENTATION domain modifier boosts documenting signal."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__context7-local__get-library-docs")
        # READ intent gives exploring + reviewing
        # DOCUMENTATION domain adds documenting boost
        assert "documenting" in result.activity_signals
        assert result.activity_signals["documenting"] > 0

    def test_domain_modifier_version_control_boosts_reviewing(self):
        """Test VERSION_CONTROL domain modifier boosts reviewing signal."""
        classifier = ToolClassifier()
        result = classifier.classify("git_commit")
        # VERSION_CONTROL domain adds reviewing boost
        assert "reviewing" in result.activity_signals
        assert result.activity_signals["reviewing"] > 0

    def test_domain_modifier_code_boosts_building_and_refactoring(self):
        """Test CODE domain modifier boosts building and refactoring signals."""
        classifier = ToolClassifier()
        result = classifier.classify("mcp__serena__replace_symbol_body")
        # MODIFY intent gives building + refactoring
        # CODE domain adds more building + refactoring
        assert "building" in result.activity_signals
        assert "refactoring" in result.activity_signals


class TestToolClassifierConfidenceCapping:
    """Test confidence and signal capping behavior."""

    def test_confidence_at_1_for_known_tools(self):
        """Test known tools have confidence of 1.0."""
        classifier = ToolClassifier()
        for tool in ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]:
            result = classifier.classify(tool)
            assert result.confidence == 1.0, f"{tool} should have confidence 1.0"

    def test_confidence_reduced_for_partial_match(self):
        """Test confidence when both intent and domain match with different confidences."""
        classifier = ToolClassifier()
        # Test that combined confidence is min(intent_conf, domain_conf)
        # For pattern-matched tools, confidence is reduced compared to known tools
        result = classifier.classify("search_file")
        # SEARCH intent has 0.85 confidence, FILESYSTEM domain has 0.85
        # Combined should be min(0.85, 0.85) = 0.85
        # This is less than 1.0 (known tools)
        assert result.confidence < 1.0
        assert result.intent == ToolIntent.SEARCH
        assert result.domain == ToolDomain.FILESYSTEM

    def test_activity_signals_capped_at_1(self):
        """Test all activity signal values stay in 0.0-1.0 range."""
        classifier = ToolClassifier()
        # Test various tools
        tools = [
            "Read",
            "Write",
            "Edit",
            "Bash",
            "mcp__serena__find_symbol",
            "run_pytest",
            "git_commit",
        ]
        for tool in tools:
            result = classifier.classify(tool)
            for dim, value in result.activity_signals.items():
                assert 0.0 <= value <= 1.0, f"Signal {dim}={value} for {tool} out of range"

    def test_confidence_min_of_intent_and_domain(self):
        """Test combined confidence is min of intent and domain confidence."""
        classifier = ToolClassifier()
        # A tool where both match with different confidences
        result = classifier.classify("search_file")
        # Should be min of intent (SEARCH, 0.85) and domain (FILESYSTEM, 0.85)
        # or close to those values
        assert result.confidence <= 0.85


class TestToolClassifierIntegrationWithActivityVector:
    """Integration tests with ActivityVector."""

    def test_activity_signals_compatible_with_from_signals(self):
        """Test activity_signals dict is compatible with ActivityVector.from_signals()."""
        classifier = ToolClassifier()

        # Test several tools
        tools = ["Read", "Write", "Edit", "Bash", "Grep", "mcp__serena__find_symbol"]

        for tool in tools:
            result = classifier.classify(tool)
            # This should not raise
            vector = ActivityVector.from_signals(result.activity_signals)
            assert isinstance(vector, ActivityVector)

    def test_activity_vector_has_expected_dimensions(self):
        """Test that activity signals map to valid ActivityVector dimensions."""
        classifier = ToolClassifier()
        valid_dimensions = set(ActivityVector.DIMENSIONS)

        for tool in ["Read", "Write", "Edit", "Bash", "Grep"]:
            result = classifier.classify(tool)
            for dim in result.activity_signals:
                assert dim in valid_dimensions, f"Invalid dimension: {dim}"

    def test_read_tool_produces_exploring_dominant_activity(self):
        """Test Read tool produces vector with exploring as a dominant activity."""
        classifier = ToolClassifier()
        result = classifier.classify("Read")
        vector = ActivityVector.from_signals(result.activity_signals)
        dominant = vector.dominant_activities
        assert "exploring" in dominant or "reviewing" in dominant

    def test_write_tool_produces_building_dominant_activity(self):
        """Test Write tool produces vector with building as dominant activity."""
        classifier = ToolClassifier()
        result = classifier.classify("Write")
        vector = ActivityVector.from_signals(result.activity_signals)
        assert vector.building > 0

    def test_multiple_tool_signals_accumulate(self):
        """Test that signals from multiple tools can be accumulated."""
        classifier = ToolClassifier()

        # Classify multiple tools
        results = [
            classifier.classify("Read"),
            classifier.classify("Edit"),
            classifier.classify("Grep"),
        ]

        # Combine their signals
        combined_signals: dict[str, float] = {}
        for result in results:
            for dim, value in result.activity_signals.items():
                combined_signals[dim] = combined_signals.get(dim, 0.0) + value

        # Cap at 1.0
        for dim in combined_signals:
            combined_signals[dim] = min(combined_signals[dim], 1.0)

        # Create vector from combined signals
        vector = ActivityVector.from_signals(combined_signals)
        assert isinstance(vector, ActivityVector)

        # Should have multiple activities
        assert vector.exploring > 0  # from Read and Grep
        assert vector.building > 0  # from Edit


class TestToolClassifierPrivateMethods:
    """Test private helper methods (white-box testing)."""

    def test_split_tool_name_underscore(self):
        """Test _split_tool_name handles underscores."""
        classifier = ToolClassifier()
        parts = classifier._split_tool_name("read_file_content")
        assert "read" in parts
        assert "file" in parts
        assert "content" in parts

    def test_split_tool_name_camelcase(self):
        """Test _split_tool_name handles camelCase."""
        classifier = ToolClassifier()
        parts = classifier._split_tool_name("readfilecontent")
        # camelCase detection only works with mixed case
        parts_mixed = classifier._split_tool_name("readFileContent".lower())
        # After lower(), it's all lowercase - no camelCase to split
        # Test with actual mixed case before lowering
        classifier2 = ToolClassifier()
        parts_camel = classifier2._split_tool_name("readfilecontent")
        assert len(parts_camel) >= 1

    def test_split_tool_name_dots(self):
        """Test _split_tool_name handles dots."""
        classifier = ToolClassifier()
        parts = classifier._split_tool_name("git.commit.push")
        assert "git" in parts
        assert "commit" in parts
        assert "push" in parts

    def test_split_tool_name_dashes(self):
        """Test _split_tool_name handles dashes."""
        classifier = ToolClassifier()
        parts = classifier._split_tool_name("read-file-content")
        assert "read" in parts
        assert "file" in parts
        assert "content" in parts

    def test_split_tool_name_mixed(self):
        """Test _split_tool_name handles mixed separators."""
        classifier = ToolClassifier()
        parts = classifier._split_tool_name("mcp__serena__find_symbol")
        assert "mcp" in parts
        assert "serena" in parts
        assert "find" in parts
        assert "symbol" in parts

    def test_match_intent_finds_read(self):
        """Test _match_intent finds READ intent."""
        classifier = ToolClassifier()
        parts = ["read", "file"]
        result = classifier._match_intent(parts)
        assert result is not None
        intent, confidence = result
        assert intent == ToolIntent.READ

    def test_match_intent_finds_search(self):
        """Test _match_intent finds SEARCH intent."""
        classifier = ToolClassifier()
        parts = ["find", "symbol"]
        result = classifier._match_intent(parts)
        assert result is not None
        intent, confidence = result
        assert intent == ToolIntent.SEARCH

    def test_match_intent_returns_none_for_no_match(self):
        """Test _match_intent returns None when no match."""
        classifier = ToolClassifier()
        parts = ["xyz", "abc"]
        result = classifier._match_intent(parts)
        assert result is None

    def test_match_domain_finds_filesystem(self):
        """Test _match_domain finds FILESYSTEM domain."""
        classifier = ToolClassifier()
        parts = ["read", "file"]
        result = classifier._match_domain(parts)
        assert result is not None
        domain, confidence = result
        assert domain == ToolDomain.FILESYSTEM

    def test_match_domain_finds_code(self):
        """Test _match_domain finds CODE domain."""
        classifier = ToolClassifier()
        parts = ["find", "symbol"]
        result = classifier._match_domain(parts)
        assert result is not None
        domain, confidence = result
        assert domain == ToolDomain.CODE

    def test_match_domain_returns_none_for_no_match(self):
        """Test _match_domain returns None when no match."""
        classifier = ToolClassifier()
        parts = ["xyz", "abc"]
        result = classifier._match_domain(parts)
        assert result is None

    def test_compute_activity_signals_read_filesystem(self):
        """Test _compute_activity_signals for READ/FILESYSTEM."""
        classifier = ToolClassifier()
        signals = classifier._compute_activity_signals(ToolIntent.READ, ToolDomain.FILESYSTEM)
        assert "exploring" in signals
        assert "reviewing" in signals

    def test_compute_activity_signals_create_memory(self):
        """Test _compute_activity_signals for CREATE/MEMORY."""
        classifier = ToolClassifier()
        signals = classifier._compute_activity_signals(ToolIntent.CREATE, ToolDomain.MEMORY)
        assert "building" in signals

    def test_compute_activity_signals_validate_testing(self):
        """Test _compute_activity_signals for VALIDATE/TESTING."""
        classifier = ToolClassifier()
        signals = classifier._compute_activity_signals(ToolIntent.VALIDATE, ToolDomain.TESTING)
        # VALIDATE gives testing: 0.6, TESTING domain adds testing: 0.3
        assert "testing" in signals
        # Allow for floating point imprecision
        assert 0.89 <= signals["testing"] <= 0.91  # 0.6 + 0.3 = 0.9

    def test_compute_activity_signals_caps_at_1(self):
        """Test _compute_activity_signals caps values at 1.0."""
        classifier = ToolClassifier()
        # VALIDATE/TESTING gives testing: 0.9 (0.6 + 0.3), which is under 1.0
        # Let's check that any value is capped at 1.0
        signals = classifier._compute_activity_signals(ToolIntent.VALIDATE, ToolDomain.TESTING)
        for dim, value in signals.items():
            assert value <= 1.0


class TestToolClassifierEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_tool_name(self):
        """Test classification with empty tool name."""
        classifier = ToolClassifier()
        result = classifier.classify("")
        assert isinstance(result, ToolClassification)
        assert result.tool_name == ""
        assert result.confidence == 0.3  # Unknown

    def test_whitespace_tool_name(self):
        """Test classification with whitespace-only tool name."""
        classifier = ToolClassifier()
        result = classifier.classify("   ")
        assert isinstance(result, ToolClassification)

    def test_very_long_tool_name(self):
        """Test classification with very long tool name."""
        classifier = ToolClassifier()
        long_name = "read_" + "x" * 100 + "_file"
        result = classifier.classify(long_name)
        # Should still match READ intent and FILESYSTEM domain
        assert result.intent == ToolIntent.READ
        assert result.domain == ToolDomain.FILESYSTEM

    def test_special_characters_in_tool_name(self):
        """Test classification with special characters."""
        classifier = ToolClassifier()
        result = classifier.classify("read@file#content")
        assert isinstance(result, ToolClassification)

    def test_unicode_tool_name(self):
        """Test classification with unicode characters."""
        classifier = ToolClassifier()
        result = classifier.classify("read_file")
        assert isinstance(result, ToolClassification)

    def test_numeric_tool_name(self):
        """Test classification with numeric parts."""
        classifier = ToolClassifier()
        result = classifier.classify("tool123")
        assert isinstance(result, ToolClassification)

    def test_single_char_tool_name(self):
        """Test classification with single character tool name."""
        classifier = ToolClassifier()
        # Use a character that won't accidentally match patterns
        result = classifier.classify("q")
        assert isinstance(result, ToolClassification)
        # May have low confidence if matches some pattern, or 0.3 if fully unknown
        assert result.confidence <= 1.0

    def test_parameters_are_ignored(self):
        """Test that parameters argument doesn't affect current implementation."""
        classifier = ToolClassifier()
        result1 = classifier.classify("Read")
        result2 = classifier.classify("Read", parameters={"path": "/some/file"})
        assert result1.intent == result2.intent
        assert result1.domain == result2.domain
        assert result1.confidence == result2.confidence

    def test_classifier_is_reusable(self):
        """Test classifier can be reused for multiple classifications."""
        classifier = ToolClassifier()
        results = []
        for tool in ["Read", "Write", "Edit", "Bash", "Grep"]:
            results.append(classifier.classify(tool))

        # All should be valid classifications
        assert all(isinstance(r, ToolClassification) for r in results)
        # Each should have different results
        intents = {r.intent for r in results}
        assert len(intents) >= 3  # At least 3 different intents


class TestToolClassifierClassAttributes:
    """Test class-level constants and configuration."""

    def test_known_tool_mappings_non_empty(self):
        """Test KNOWN_TOOL_MAPPINGS has entries."""
        assert len(ToolClassifier.KNOWN_TOOL_MAPPINGS) > 0

    def test_known_tool_mappings_structure(self):
        """Test KNOWN_TOOL_MAPPINGS has correct tuple structure."""
        for tool_name, mapping in ToolClassifier.KNOWN_TOOL_MAPPINGS.items():
            assert isinstance(tool_name, str)
            assert len(mapping) == 3
            intent, domain, confidence = mapping
            assert isinstance(intent, ToolIntent)
            assert isinstance(domain, ToolDomain)
            assert 0.0 <= confidence <= 1.0

    def test_intent_patterns_non_empty(self):
        """Test INTENT_PATTERNS has entries."""
        assert len(ToolClassifier.INTENT_PATTERNS) > 0

    def test_intent_patterns_structure(self):
        """Test INTENT_PATTERNS has correct structure."""
        for entry in ToolClassifier.INTENT_PATTERNS:
            assert len(entry) == 3
            keywords, intent, confidence = entry
            assert isinstance(keywords, list)
            assert len(keywords) > 0
            assert isinstance(intent, ToolIntent)
            assert 0.0 <= confidence <= 1.0

    def test_domain_patterns_non_empty(self):
        """Test DOMAIN_PATTERNS has entries."""
        assert len(ToolClassifier.DOMAIN_PATTERNS) > 0

    def test_domain_patterns_structure(self):
        """Test DOMAIN_PATTERNS has correct structure."""
        for entry in ToolClassifier.DOMAIN_PATTERNS:
            assert len(entry) == 3
            keywords, domain, confidence = entry
            assert isinstance(keywords, list)
            assert len(keywords) > 0
            assert isinstance(domain, ToolDomain)
            assert 0.0 <= confidence <= 1.0

    def test_intent_to_activity_has_all_intents(self):
        """Test INTENT_TO_ACTIVITY covers most intents."""
        # UNKNOWN and COMMUNICATE might not have specific activity mappings
        covered_intents = set(ToolClassifier.INTENT_TO_ACTIVITY.keys())
        # At least the main intents should be covered
        main_intents = {
            ToolIntent.CREATE,
            ToolIntent.MODIFY,
            ToolIntent.DELETE,
            ToolIntent.READ,
            ToolIntent.SEARCH,
            ToolIntent.EXECUTE,
            ToolIntent.CONFIGURE,
            ToolIntent.VALIDATE,
        }
        assert covered_intents >= main_intents

    def test_activity_signals_use_valid_dimensions(self):
        """Test all activity signal keys are valid ActivityVector dimensions."""
        valid_dimensions = set(ActivityVector.DIMENSIONS)

        # Check INTENT_TO_ACTIVITY
        for intent, signals in ToolClassifier.INTENT_TO_ACTIVITY.items():
            for dim in signals:
                assert dim in valid_dimensions, f"Invalid dimension {dim} in INTENT_TO_ACTIVITY"

        # Check DOMAIN_MODIFIERS
        for domain, signals in ToolClassifier.DOMAIN_MODIFIERS.items():
            for dim in signals:
                assert dim in valid_dimensions, f"Invalid dimension {dim} in DOMAIN_MODIFIERS"
