# Implementation Sprint: Graphiti Filesystem Export

**Created**: 2025-11-09 01:22
**Status**: active
**Sprint Goal**: Implement filesystem export capabilities for Graphiti memory graph with flexible path patterns, templates, and INDEX.md integration for agent handoff workflows and session continuity

## Stories

### Story 1: Core Export Infrastructure
**Status**: unassigned
**Description**: Implement the foundational MemoryExporter class and path pattern resolution system
**Acceptance Criteria**:
- [ ] Create `graphiti_core/export.py` with MemoryExporter class
- [ ] Implement path pattern variable substitution ({date}, {timestamp}, {session_id}, etc.)
- [ ] Add ExportConfig Pydantic model to unified_config.py
- [ ] Add path resolution with builtin variables (timestamp, date, fact_count, node_count)
- [ ] Support custom path_variables parameter
- [ ] Add export section to graphiti.config.json schema

### Story 1.1: Export Configuration Schema
**Status**: unassigned
**Parent**: Story 1
**Description**: Define export configuration in unified config system
**Acceptance Criteria**:
- [ ] Add ExportConfig class to mcp_server/unified_config.py
- [ ] Fields: enabled, default_base_path, auto_index, git_tracking, security_scan
- [ ] Add path_patterns dict for named patterns
- [ ] Add templates dict for template configurations
- [ ] Validate configuration on startup

### Story 1.2: Path Pattern Resolution
**Status**: unassigned
**Parent**: Story 1
**Description**: Implement dynamic path pattern variable substitution
**Acceptance Criteria**:
- [ ] Resolve builtin variables: {date}, {timestamp}, {time}, {session_id}, {group_id}, {query_hash}, {fact_count}, {node_count}
- [ ] Support custom variables via path_variables parameter
- [ ] Handle nested directory creation (mkdir -p behavior)
- [ ] Validate paths for security (no path traversal attacks)
- [ ] Generate session_id if not provided (uuid4)

### Story 2: Template System (MVP - Markdown Only)
**Status**: unassigned
**Description**: Implement template rendering system with built-in "handoff" template in markdown format
**Acceptance Criteria**:
- [ ] Create graphiti_core/templates.py with TemplateEngine class
- [ ] Implement MarkdownFormatter class
- [ ] Create built-in "handoff" template (see design doc)
- [ ] Render facts and nodes as markdown sections
- [ ] Support metadata injection into templates
- [ ] Handle empty results gracefully

### Story 2.1: Handoff Template Implementation
**Status**: unassigned
**Parent**: Story 2
**Description**: Create production-ready handoff template for agent session transitions
**Acceptance Criteria**:
- [ ] Template includes: Session Context, Key Entities, Critical Relationships, Next Steps sections
- [ ] Format entities with name, type, summary, and attributes
- [ ] Format facts with source-relationship-target pattern
- [ ] Include review checklist at bottom
- [ ] Support custom metadata fields

### Story 3: MCP Tool Integration (export_memory_to_file)
**Status**: unassigned
**Description**: Add export_memory_to_file MCP tool to graphiti_mcp_server.py
**Acceptance Criteria**:
- [ ] Add @mcp.tool() decorated export_memory_to_file function
- [ ] Parameters: query, output_path, template, format, group_ids, max_facts, max_nodes, metadata, path_variables
- [ ] Execute search_memory_facts() and search_memory_nodes() internally
- [ ] Call MemoryExporter.export_to_file() with search results
- [ ] Return structured response with path, fact_count, node_count, success status
- [ ] Handle errors gracefully with informative messages

### Story 3.1: Security Scanning
**Status**: unassigned
**Parent**: Story 3
**Description**: Implement credential detection before writing files
**Acceptance Criteria**:
- [ ] Pattern matching for: api_key, secret, password, token, bearer, auth_token
- [ ] Scan rendered content before file write
- [ ] Warn on detection with list of matched patterns
- [ ] Suggest obfuscation techniques
- [ ] Config option to enforce (halt) vs warn (continue)

### Story 4: Priority 2 - Multi-Format Support
**Status**: unassigned
**Description**: Extend template system to support JSON, YAML, and HTML output formats
**Acceptance Criteria**:
- [ ] Implement JSONFormatter class in templates.py
- [ ] Implement YAMLFormatter class in templates.py
- [ ] Implement HTMLFormatter class in templates.py
- [ ] Add format parameter validation (markdown, json, yaml, html)
- [ ] Update TemplateEngine to route to correct formatter
- [ ] Create built-in templates for each format (investigation, snapshot)

### Story 4.1: JSON/YAML Formatters
**Status**: unassigned
**Parent**: Story 4
**Description**: Implement structured data export formatters
**Acceptance Criteria**:
- [ ] JSONFormatter: serialize facts/nodes to JSON with proper structure
- [ ] YAMLFormatter: serialize to YAML with human-readable formatting
- [ ] Include metadata fields in output
- [ ] Handle datetime serialization
- [ ] Validate output with json.loads() / yaml.safe_load()

### Story 4.2: Investigation Template
**Status**: unassigned
**Parent**: Story 4
**Description**: Create JSON-formatted investigation template for debugging
**Acceptance Criteria**:
- [ ] Structure: investigation.timestamp, query, context, findings, metrics
- [ ] Include entities_as_json and facts_as_json
- [ ] Calculate metrics: fact_count, node_count, avg_confidence
- [ ] Suitable for machine parsing and analysis tools

### Story 5: INDEX.md Auto-Generation
**Status**: unassigned
**Description**: Implement automatic INDEX.md creation and updates in export directories
**Acceptance Criteria**:
- [ ] Create or update INDEX.md after each export operation
- [ ] Track: file name, created timestamp, modified timestamp, size, description
- [ ] Group files by category/subdirectory
- [ ] Generate table format matching EPHEMERAL-FS schema
- [ ] Append new entries (don't overwrite existing)
- [ ] Extract description from file metadata or first line

### Story 5.1: INDEX.md Template Migration Strategy
**Status**: unassigned
**Parent**: Story 5
**Description**: Design and implement strategy to migrate existing INDEX.md files to standardized template
**Acceptance Criteria**:
- [ ] Create migration tool/function to detect existing INDEX.md format
- [ ] Leverage LLM (via Graphiti's llm_client) to parse and reformat existing content
- [ ] Preserve all existing information during migration
- [ ] Apply standardized EPHEMERAL-FS schema template
- [ ] Support batch migration across multiple .claude/ subdirectories
- [ ] Generate migration report (files processed, success/failure)
- [ ] Add --dry-run mode to preview changes

### Story 5.2: Standardized INDEX.md Template
**Status**: unassigned
**Parent**: Story 5
**Description**: Define and document the canonical INDEX.md template for EPHEMERAL-FS
**Acceptance Criteria**:
- [ ] Document template schema in .claude/implementation/stories/index-template-schema.md
- [ ] Include table format with columns: File, Created, Modified, Size, Description
- [ ] Add archive summary section template
- [ ] Define metadata header format (category, last_updated, file_count)
- [ ] Provide examples for different categories (handoff, research, context)

### Story 6: Template Management Tool
**Status**: unassigned
**Description**: Add manage_export_templates MCP tool for template CRUD operations
**Acceptance Criteria**:
- [ ] Add @mcp.tool() decorated manage_export_templates function
- [ ] Actions: list, get, create, update, delete
- [ ] Store custom templates in graphiti.config.json or separate template files
- [ ] List action returns all available templates with metadata
- [ ] Get action returns full template definition
- [ ] Create/update validates template structure
- [ ] Delete requires confirmation

### Story 7: Documentation & Examples
**Status**: unassigned
**Description**: Comprehensive documentation for filesystem export features
**Acceptance Criteria**:
- [ ] Add "Filesystem Export" section to CONFIGURATION.md
- [ ] Document all export config options with examples
- [ ] Update CLAUDE.md with export_memory_to_file tool description
- [ ] Create .claude/implementation/stories/export-examples.md with use cases
- [ ] Add troubleshooting section for common export issues
- [ ] Document template customization guide

### Story 8: Testing & Validation
**Status**: unassigned
**Description**: Create comprehensive test suite for export functionality
**Acceptance Criteria**:
- [ ] Unit tests for path pattern resolution (10+ test cases)
- [ ] Unit tests for template rendering (markdown, json, yaml)
- [ ] Integration tests for export_memory_to_file tool
- [ ] Tests for security scanning (credential detection)
- [ ] Tests for INDEX.md generation
- [ ] Mock filesystem operations (use tempfile)
- [ ] Test error handling (invalid paths, missing templates, search failures)
- [ ] Achieve >80% coverage for export module

## Progress Log

### 2025-11-09 01:22 - Sprint Started
- Archived previous sprint (MCP Server Resilience) to archive/2025-11-09-0122/
- Created new sprint structure
- Defined 8 main stories + 6 sub-stories = 14 total stories
- Focus on filesystem export to enable agent handoff workflows

### 2025-11-09 01:22 - Session Context Documented
**Need**: Agent handoff documents tracked in git with human review capability, reducing token overhead vs manual file creation
**Solution**: Extend Graphiti with filesystem export using flexible path patterns and templates
**Architecture**: MemoryExporter class → search graph → render template → write file → update INDEX.md
**Challenges**:
  - Migrating existing INDEX.md files to standardized template (use LLM-assisted migration)
  - Balancing simplicity (MVP) vs flexibility (Priority 2 formats)
  - Security scanning for credentials before export
**Timeline**:
  - MVP (Stories 1-3): 2-3 days (core export, markdown handoff template, MCP tool)
  - Priority 2 (Stories 4-6): 3-5 days (multi-format, INDEX.md, template management)
  - Total: 5-8 days for full implementation

## Sprint Summary
{To be filled upon completion}
