# INDEX.md Template Schema

**Created**: 2025-11-09 01:22
**Sprint**: Graphiti Filesystem Export
**Purpose**: Canonical schema for standardized INDEX.md files across `.claude/` subdirectories

## Overview

This document defines the standardized template for INDEX.md files used throughout the `.claude/` directory structure. The schema is designed to:
- Provide consistent file tracking across all categories
- Enable quick discovery without full file reads
- Support automatic generation and updates
- Facilitate LLM-assisted migration of existing files

## Schema Definition

### Header Section

```markdown
# {Category} Index

**Last Updated**: {YYYY-MM-DD HH:mm}
**File Count**: {N}
**Total Size**: {X.XX MB}

{Optional: Category description - 1-2 sentences}
```

### Files Table Section

```markdown
## Files

| File | Created | Modified | Size | Description |
|------|---------|----------|------|-------------|
| {filename} | {YYYY-MM-DD} | {YYYY-MM-DD} | {X KB} | {Brief description} |
| ... | ... | ... | ... | ... |
```

**Table Columns**:
- **File**: Filename only (not full path), sorted alphabetically
- **Created**: Date only (YYYY-MM-DD format)
- **Modified**: Date of last modification (YYYY-MM-DD format)
- **Size**: Human-readable (KB, MB), 2 decimal places for MB
- **Description**: Brief summary (max 80 chars), extracted from file metadata or first line

### Archive Section (Optional)

```markdown
## Archives

Archived files are preserved in `archive/{YYYY-MM-DD-HHmm}/` subdirectories.

| Archive Date | Files | Reason | Restore Command |
|--------------|-------|--------|-----------------|
| {YYYY-MM-DD-HHmm} | {N} | {Brief reason} | See `archive/{timestamp}/INDEX.md` |
| ... | ... | ... | ... |
```

### Subdirectories Section (Optional)

```markdown
## Subdirectories

| Directory | Purpose | File Count |
|-----------|---------|------------|
| {dirname}/ | {Brief purpose} | {N} |
| ... | ... | ... |
```

## Category-Specific Examples

### Example 1: Handoff Index

```markdown
# Handoff Index

**Last Updated**: 2025-11-09 01:30
**File Count**: 3
**Total Size**: 45.67 KB

Agent handoff documents for session transitions and context transfer.

## Files

| File | Created | Modified | Size | Description |
|------|---------|----------|------|-------------|
| 2025-11-08-auth-review-handoff.md | 2025-11-08 | 2025-11-08 | 12.34 KB | Authentication system review - completed, ready for next agent |
| 2025-11-09-db-migration-handoff.md | 2025-11-09 | 2025-11-09 | 18.92 KB | Database migration planning - in progress, blocked on schema approval |
| 2025-11-09-export-feature-handoff.md | 2025-11-09 | 2025-11-09 | 14.41 KB | Filesystem export implementation - unassigned |

## Archives

Archived files are preserved in `archive/{YYYY-MM-DD-HHmm}/` subdirectories.

| Archive Date | Files | Reason | Restore Command |
|--------------|-------|--------|-----------------|
| 2025-11-05-1430 | 5 | Sprint completion - MCP resilience features | See `archive/2025-11-05-1430/INDEX.md` |
```

### Example 2: Research Index

```markdown
# Research Index

**Last Updated**: 2025-11-09 01:30
**File Count**: 2
**Total Size**: 128.45 KB

Research findings, investigations, and analysis documents.

## Files

| File | Created | Modified | Size | Description |
|------|---------|----------|------|-------------|
| mcp-disconnect-analysis.md | 2025-11-04 | 2025-11-04 | 89.12 KB | Root cause analysis of MCP server connection failures |
| neo4j-performance-study.json | 2025-11-06 | 2025-11-06 | 39.33 KB | Neo4j query performance benchmarks and optimization recommendations |
```

### Example 3: Implementation Index

```markdown
# Implementation Index

**Last Updated**: 2025-11-09 01:30
**File Count**: 1
**Total Size**: 12.34 KB

Sprint tracking and implementation plans.

## Files

| File | Created | Modified | Size | Description |
|------|---------|----------|------|-------------|
| index.md | 2025-11-09 | 2025-11-09 | 12.34 KB | Active sprint: Graphiti Filesystem Export |

## Subdirectories

| Directory | Purpose | File Count |
|-----------|---------|------------|
| stories/ | Detailed story documentation and planning | 2 |
| archive/ | Completed sprints and historical records | 1 |

## Archives

Archived files are preserved in `archive/{YYYY-MM-DD-HHmm}/` subdirectories.

| Archive Date | Files | Reason | Restore Command |
|--------------|-------|--------|-----------------|
| 2025-11-09-0122 | 4 | New sprint started - archived MCP resilience sprint | See `archive/2025-11-09-0122/INDEX.md` |
```

### Example 4: Context Index

```markdown
# Context Index

**Last Updated**: 2025-11-09 01:30
**File Count**: 4
**Total Size**: 67.89 KB

Contextual discoveries, insights, and knowledge captured during development.

## Files

| File | Created | Modified | Size | Description |
|------|---------|----------|------|-------------|
| auth-flow-discovery.md | 2025-11-07 | 2025-11-07 | 15.23 KB | OAuth2 flow implementation details discovered during code review |
| db-schema-insights.md | 2025-11-08 | 2025-11-08 | 22.11 KB | Neo4j schema patterns and relationship modeling best practices |
| error-patterns.md | 2025-11-09 | 2025-11-09 | 18.34 KB | Common error patterns and resolution strategies |
| performance-tips.md | 2025-11-09 | 2025-11-09 | 12.21 KB | Performance optimization techniques for Graphiti operations |
```

## Field Specifications

### File Size Calculation

```python
def format_file_size(bytes: int) -> str:
    """Format file size in human-readable format."""
    kb = bytes / 1024
    if kb < 1024:
        return f"{kb:.2f} KB"
    mb = kb / 1024
    return f"{mb:.2f} MB"
```

### Description Extraction

**Priority order**:
1. **Metadata field**: If file has `description:` in frontmatter/header
2. **First heading**: Extract first H1 or H2 heading (strip markdown syntax)
3. **First line**: Use first non-empty line (max 80 chars)
4. **Fallback**: "No description available"

**Example extraction**:
```markdown
# Agent Handoff: Authentication Review

**Status**: Completed
**Description**: Security audit of OAuth2 implementation with recommendations

## Summary
...
```
→ Description: "Security audit of OAuth2 implementation with recommendations"

### Total Size Calculation

Sum of all file sizes in the directory (excluding subdirectories and INDEX.md itself).

## Migration Strategy

### Detecting Existing Format

```python
def detect_index_format(content: str) -> str:
    """Detect format of existing INDEX.md file."""
    if "| File | Created | Modified | Size | Description |" in content:
        return "standardized"  # Already in correct format
    elif "##" in content and "|" in content:
        return "partial_table"  # Has some structure, needs reformatting
    elif re.search(r"^\s*-\s+", content, re.MULTILINE):
        return "bullet_list"  # Bullet list format
    else:
        return "freeform"  # Unstructured content
```

### LLM-Assisted Migration

```python
async def migrate_index_file(
    file_path: str,
    llm_client: LLMClient,
    dry_run: bool = False
) -> dict:
    """Migrate existing INDEX.md to standardized schema."""

    # 1. Read existing content
    existing_content = read_file(file_path)
    existing_format = detect_index_format(existing_content)

    if existing_format == "standardized":
        return {"status": "skipped", "reason": "already_standardized"}

    # 2. Extract metadata from directory
    directory = os.path.dirname(file_path)
    files = list_files(directory, exclude=["INDEX.md"])
    file_metadata = [get_file_metadata(f) for f in files]

    # 3. LLM prompt for reformatting
    prompt = f"""
    Reformat this INDEX.md file to match the standardized schema.

    **Current content:**
    {existing_content}

    **File metadata to include:**
    {json.dumps(file_metadata, indent=2)}

    **Target schema:**
    {SCHEMA_TEMPLATE}

    **Instructions:**
    1. Preserve all information from the original content
    2. Extract descriptions from existing text where possible
    3. Use file metadata for Created, Modified, Size columns
    4. Maintain chronological or alphabetical order
    5. Return ONLY the reformatted markdown (no explanations)
    """

    reformatted = await llm_client.generate(prompt)

    # 4. Validate output
    if not validate_schema(reformatted):
        raise ValueError("LLM output does not match schema")

    # 5. Write (if not dry run)
    if not dry_run:
        write_file(file_path, reformatted)

    return {
        "status": "migrated",
        "original_format": existing_format,
        "file_path": file_path,
        "dry_run": dry_run,
        "preview": reformatted[:500] + "..." if dry_run else None
    }
```

## Validation Rules

### Required Elements

- [x] Header with category name
- [x] Last Updated timestamp
- [x] File Count (must match actual count)
- [x] Files table with all 5 columns
- [x] At least one file entry (unless directory is empty)

### Optional Elements

- [ ] Total Size (recommended for large directories)
- [ ] Category description (recommended for clarity)
- [ ] Archives section (only if archives exist)
- [ ] Subdirectories section (only if subdirectories exist)

### Validation Function

```python
def validate_index_schema(content: str) -> tuple[bool, list[str]]:
    """Validate INDEX.md content against schema."""
    errors = []

    # Check header
    if not re.search(r"^# .+ Index$", content, re.MULTILINE):
        errors.append("Missing header: '# {Category} Index'")

    # Check Last Updated
    if "**Last Updated**:" not in content:
        errors.append("Missing 'Last Updated' field")

    # Check File Count
    if "**File Count**:" not in content:
        errors.append("Missing 'File Count' field")

    # Check table
    if "| File | Created | Modified | Size | Description |" not in content:
        errors.append("Missing or malformed files table")

    return (len(errors) == 0, errors)
```

## Usage in Auto-Generation

When `auto_index=true` in export configuration:

1. **After export operation**:
   - Read existing INDEX.md (if exists)
   - Extract current file list
   - Add new file entry
   - Recalculate File Count and Total Size
   - Update Last Updated timestamp
   - Write updated INDEX.md

2. **For new directories**:
   - Create INDEX.md with schema template
   - Populate with first file entry
   - Set File Count = 1
   - Calculate Total Size

3. **Batch updates**:
   - Process all new files
   - Single INDEX.md update at end (not per-file)
   - Sort table alphabetically or chronologically

## Benefits

**For Agents**:
- Quick discovery without full file reads (90% token savings)
- Consistent structure across all `.claude/` categories
- Automatic tracking (no manual updates when auto_index=true)

**For Humans**:
- Easy navigation in file explorer or IDE
- Git-tracked history of file additions/changes
- Clear audit trail of document evolution

**For MCP Server**:
- Simple schema to generate programmatically
- Offloads tracking burden from working agent
- Enables metadata queries without filesystem scans

## References

- EPHEMERAL-FS rules: `.claude/` organization schema (global CLAUDE.md)
- Export configuration: `graphiti.config.json` export section
- Migration tool: Story 5.1 implementation details
