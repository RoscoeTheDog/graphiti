# Filesystem Export - Context & Architecture

**Created**: 2025-11-09 01:22
**Sprint**: Graphiti Filesystem Export
**Status**: Planning Document

## Session Context

### Original Need

User requirement for `.claude/handoff/` directory with structured handoff documents:
- **Purpose**: Agent session transitions with human review capability
- **Workflow**: Git-tracked files that create audit trail across sessions
- **Problem**: Manual file creation has high token overhead (500-1000t per document)
- **Insight**: Graphiti already excels at structured memory storage and search

### Why Filesystem Export?

**Token Efficiency:**
- Manual approach: ~500-1000t (format facts, create structure, write file)
- Graphiti memory only: ~100t (search + store)
- **Graphiti + Export: ~150t** (search + template render + write)
  - 60-85% savings vs manual
  - Reusable templates eliminate repeated formatting
  - Single query retrieves structured data

**Workflow Benefits:**
- Git tracking provides audit trail
- Human review before next agent picks up
- Session continuity across context boundaries
- Structured handoff reduces information loss

**Future Integration:**
- Temporal orchestration server (planned)
- Checkpoints for workflow resumption
- External system integration (JSON/YAML exports)
- Hybrid workflows (graph + filesystem)

## Solution Overview

Extend Graphiti MCP server with export capabilities that:
1. Query memory graph (reuse existing search infrastructure)
2. Render results using templates (minimal token overhead)
3. Write to filesystem with dynamic path patterns
4. Auto-generate/update INDEX.md for discoverability
5. Integrate with git for version control

## Architecture

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│ MCP Client (Claude Code Agent)                         │
│ - Calls export_memory_to_file()                        │
│ - Provides query, path pattern, template name          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ MCP Server (graphiti_mcp_server.py)                    │
│ - @mcp.tool() export_memory_to_file()                  │
│ - Validates parameters                                  │
│ - Calls search_memory_facts() & search_memory_nodes()  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ MemoryExporter (graphiti_core/export.py)               │
│ - Orchestrates export workflow                         │
│ - Resolves path patterns with variables                │
│ - Renders templates with search results                │
│ - Writes files with security scanning                  │
│ - Updates INDEX.md (if enabled)                         │
└─────────┬────────────────────────────┬──────────────────┘
          │                            │
          ▼                            ▼
┌──────────────────────┐    ┌─────────────────────────────┐
│ TemplateEngine       │    │ Path Pattern Resolver       │
│ (templates.py)       │    │                             │
│ - Loads templates    │    │ - Builtin vars: {date},    │
│ - Renders with data  │    │   {timestamp}, {session_id} │
│ - Format routing     │    │ - Custom vars from caller   │
│ - Markdown/JSON/YAML │    │ - Security validation       │
└──────────┬───────────┘    └─────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│ Formatters (templates.py)                              │
│ - MarkdownFormatter (MVP)                              │
│ - JSONFormatter (Priority 2)                           │
│ - YAMLFormatter (Priority 2)                           │
│ - HTMLFormatter (Priority 2)                           │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. Agent Request
   └─> query="recent: auth changes"
   └─> output_path=".claude/handoff/{date}-auth-handoff.md"
   └─> template="handoff"

2. Graph Search
   └─> search_memory_facts(query, max_facts=50)
   └─> search_memory_nodes(query, max_nodes=20)
   └─> Returns: facts=List[FactResult], nodes=List[NodeResult]

3. Path Resolution
   └─> Extract variables: {date}="2025-11-09", {fact_count}=42, {node_count}=15
   └─> Substitute: ".claude/handoff/2025-11-09-auth-handoff.md"
   └─> Validate: No path traversal, within allowed directories

4. Template Rendering
   └─> Load template: "handoff" (markdown format)
   └─> Inject data: facts, nodes, metadata, builtin vars
   └─> Render: Full markdown document

5. Security Scan
   └─> Pattern match: api_key, secret, password, token
   └─> Action: Warn (log) or Halt (raise error)

6. File Write
   └─> Create directories: mkdir -p .claude/handoff/
   └─> Write file: .claude/handoff/2025-11-09-auth-handoff.md
   └─> Set permissions: 644 (rw-r--r--)

7. INDEX.md Update (if enabled)
   └─> Load: .claude/handoff/INDEX.md
   └─> Append: New entry with file metadata
   └─> Write: Updated INDEX.md

8. Git Integration (if enabled)
   └─> Stage: git add .claude/handoff/2025-11-09-auth-handoff.md
   └─> Optional commit: user-controlled

9. Return Response
   └─> {success: true, path: "...", fact_count: 42, node_count: 15}
```

## Key Design Decisions

### 1. Reuse Existing Infrastructure

**Decision**: Use existing `search_memory_facts()` and `search_memory_nodes()`
**Rationale**: No new graph queries needed, already optimized, consistent results
**Impact**: Minimal additional code, fast implementation

### 2. Simple Path Patterns

**Decision**: String interpolation for basic patterns, no complex templating language
**Rationale**: 80% of use cases covered by simple {variable} substitution
**Impact**: Low complexity, easy to understand, future extensible to Jinja2 if needed

### 3. MVP: Markdown Only

**Decision**: Phase 1 implements only MarkdownFormatter
**Rationale**: Primary use case is human-readable handoff documents
**Impact**: Fast MVP, can add JSON/YAML/HTML in Priority 2 without breaking changes

### 4. Config-Driven Templates

**Decision**: Store templates in graphiti.config.json with fallback to built-in defaults
**Rationale**: User customization without code changes, version controlled with project
**Impact**: Flexible, allows team-specific templates

### 5. Security by Default

**Decision**: Credential scanning enabled by default (warn mode)
**Rationale**: Prevent accidental secret leakage in git-tracked exports
**Impact**: Minimal performance overhead, prevents common security mistakes

### 6. INDEX.md Auto-Generation

**Decision**: Automatic INDEX.md creation/updates when auto_index=true
**Rationale**: Maintains discoverability, reduces manual tracking burden
**Impact**: Offloads token overhead from working agent to MCP server

## Challenges & Solutions

### Challenge 1: Migrating Existing INDEX.md Files

**Problem**: User has existing INDEX.md files in various formats across `.claude/` subdirectories
**Solution**: LLM-assisted migration tool
- Detect existing INDEX.md format (parse existing structure)
- Use Graphiti's llm_client to reformat to standardized template
- Preserve all information during migration
- Batch migration with dry-run preview
- Generate migration report

**Implementation**:
```python
async def migrate_index_files(base_path: str, dry_run: bool = False):
    """Migrate existing INDEX.md files to standardized template."""
    # 1. Find all INDEX.md files recursively
    # 2. For each file:
    #    - Read content
    #    - Send to LLM: "Reformat this INDEX.md to schema: {schema}"
    #    - Validate output matches schema
    #    - Write (if not dry_run)
    # 3. Generate report
```

### Challenge 2: Template Complexity vs Simplicity

**Problem**: Balance between simple string interpolation and flexible templating
**Solution**: Phased approach
- **MVP**: Simple {variable} substitution for 80% of use cases
- **Priority 2**: Optional Jinja2 support for advanced templates
- **Config**: Allow specifying template engine per template

### Challenge 3: CLAUDE.md Integration

**Problem**: Existing CLAUDE.md policies track INDEX.md manually, need to update post-MVP
**Solution**: Two-phase update
1. **During MVP**: Keep existing manual INDEX.md tracking
2. **Post-MVP**: Update CLAUDE.md to leverage auto_index feature
3. **Migration**: Run migration tool to standardize existing files
4. **Documentation**: Update cliff-notes with new export workflow patterns

**Proposed CLAUDE.md Changes** (post-MVP):
```markdown
## EPHEMERAL-FS (/.claude/ Organization)

**INDEX-TRACKING**: Automatic via Graphiti export (when auto_index=true)
- Manual updates only when auto_index=false
- Use export_memory_to_file() for handoff/context/research docs
- INDEX.md auto-generated with standardized schema

**ANTI-PATTERNS**:
❌ Manual INDEX.md updates when auto_index=true
✅ Use export_memory_to_file() for tracked documents
```

### Challenge 4: Token Overhead Reduction Strategy

**Problem**: How to truly offload token load from working agent to MCP server
**Solution**: Separation of concerns
- **Working Agent**: Focuses on task at hand, minimal file tracking
- **MCP Server**: Handles INDEX.md updates, file metadata, discoverability
- **Graphiti Memory**: Stores semantic relationships, not file contents
- **INDEX.md**: Provides quick reference without full file reads

**Workflow Comparison**:

| Task | Manual (Old) | Graphiti Export (New) | Token Savings |
|------|--------------|----------------------|---------------|
| Create handoff doc | Agent formats + writes | Agent calls export tool | 70-85% |
| Update INDEX.md | Agent reads + appends | MCP auto-updates | 90-95% |
| Find related docs | Agent searches files | Agent queries Graphiti | 60-80% |
| Session resume | Agent reads handoff | Agent queries memory + reads export | 40-60% |

## Timeline & Phases

### MVP Phase (Stories 1-3): 2-3 Days

**Deliverables**:
- Core MemoryExporter class with path resolution
- Built-in "handoff" template (markdown)
- export_memory_to_file MCP tool
- Security scanning for credentials
- Basic configuration in graphiti.config.json

**User Value**:
- Immediate handoff document generation
- Git-tracked workflow audit trail
- 60-85% token reduction vs manual

### Priority 2 Phase (Stories 4-6): 3-5 Days

**Deliverables**:
- JSON/YAML/HTML formatters
- INDEX.md auto-generation
- Template management tool
- Investigation and snapshot templates
- Comprehensive documentation

**User Value**:
- Machine-readable exports for external tools
- Automatic file tracking and discoverability
- Custom template support for team workflows
- Migration tool for existing INDEX.md files

### Priority 3 Phase (Future): 5-7 Days

**Deliverables** (not in current sprint):
- Batch export operations
- Automatic triggers (session end, errors, milestones)
- Git auto-commit with custom messages
- Counter-based sequential naming
- Temporal orchestration integration

**User Value**:
- Fully automated checkpoint creation
- Workflow resumption from filesystem state
- Zero-touch handoff documentation

## Success Metrics

**Technical**:
- [ ] Export operation completes in <1 second for typical queries
- [ ] Test coverage >80% for export module
- [ ] Zero credential leaks in test suite
- [ ] All path patterns resolve correctly

**User Experience**:
- [ ] Token overhead reduced by >60% vs manual file creation
- [ ] Single MCP call creates production-ready handoff document
- [ ] INDEX.md automatically maintained (no manual updates)
- [ ] Existing INDEX.md files successfully migrated

**Code Quality**:
- [ ] Clean separation of concerns (exporter, templates, formatters)
- [ ] Backward compatible with existing Graphiti functionality
- [ ] Well-documented with examples for all use cases
- [ ] Configuration validates on startup (Pydantic models)

## Integration Points

### Existing Graphiti Components

**Reused**:
- `search_memory_facts()` - Query relationship search
- `search_memory_nodes()` - Entity search
- `llm_client` - LLM access for INDEX.md migration
- `unified_config.py` - Configuration management
- Neo4j driver - No direct usage (through search APIs)

**Extended**:
- `graphiti.config.json` - Add export section
- `mcp_server/graphiti_mcp_server.py` - Add export tool
- `CONFIGURATION.md` - Document export options

**New**:
- `graphiti_core/export.py` - MemoryExporter class
- `graphiti_core/templates.py` - TemplateEngine and formatters
- `.claude/implementation/stories/` - Planning documents

### EPHEMERAL-FS Compliance

**Alignment**:
- R1: Export files go to `.claude/{category}/` (handoff, context, research)
- R2: INDEX.md updates after batch operations (auto_index feature)
- R3: Archives preserve structure (future: export old handoffs)
- R5: Categories auto-created and justified in INDEX.md
- R8: Git tracking enabled (exports are tracked, not gitignored)

**Enhancements**:
- Automatic INDEX.md generation (reduces manual burden)
- Standardized schema for consistency
- LLM-assisted migration for existing files

## Next Steps

1. **Sprint Initialization Complete** - Documented context and architecture
2. **User Confirmation** - Await approval to begin Story 1
3. **MVP Implementation** - Stories 1-3 (core export functionality)
4. **Priority 2 Implementation** - Stories 4-6 (multi-format, INDEX.md, templates)
5. **CLAUDE.md Update** - Post-MVP integration with global policies
6. **INDEX.md Migration** - Batch migrate existing files to standardized schema
