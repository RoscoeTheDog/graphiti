# Source-Based Filtering for Create/Update/Delete Operations

## Problem

Original design excluded all "update" operations from lazy-load to avoid git rollback noise. However:

**User Requirement**: Create/Update/Delete are valuable context (user actively working on files)
**Noise Issue**: Git rollbacks generate 47+ bulk updates (pollution)

## Solution: Source-Based Differentiation

Use `source` parameter to differentiate bulk operations from individual changes.

### Episode Source Types

```python
"filesystem_watch"  # Individual file operations ✅ INCLUDE
"git_bulk_update"   # Bulk git operations ❌ EXCLUDE
"git_metadata"      # Git summaries ✅ INCLUDE
"git_context"       # Conversation snapshots ✅ INCLUDE
"text"              # User memories ✅ INCLUDE
"json"              # Structured data ✅ INCLUDE
"message"           # Conversations ✅ INCLUDE
```

### Episode Operations (still tracked)

```python
"create"   # New file ✅ (valuable if source="filesystem_watch")
"update"   # Modified file ✅ (valuable if source="filesystem_watch")
"delete"   # Removed file ✅ (valuable if source="filesystem_watch")
"move"     # File moved ❌ (maintenance, always exclude)
"rename"   # File renamed ❌ (maintenance, always exclude)
```

## Filtering Logic

### Lazy-Load Query (INIT R8)

```python
search_memory_nodes(
    query="recent project context",
    group_ids=[GRAPHITI_GROUP_ID],
    exclude_sources=["git_bulk_update"],  # Bulk ops
    exclude_operations=["move", "rename"],  # Maintenance
    max_nodes=20
)
```

### What Gets Included

✅ **Individual File Operations** (`source="filesystem_watch"`)
- User creates new file: `auth.json`
- User updates existing file: `database.py`
- User deletes file: `old_config.json`

✅ **Git Context** (`source="git_metadata"` or `"git_context"`)
- Git rollback metadata
- Conversation reasoning

✅ **User Memories** (`source="text"/"json"/"message"`)
- Preferences, decisions, conventions

### What Gets Excluded

❌ **Bulk Git Operations** (`source="git_bulk_update"`)
- 47 files updated during `git reset --hard`
- Queryable via explicit search if needed

❌ **Maintenance Operations** (`operation="move"/"rename"`)
- File reorganization
- Directory restructuring

## Implementation

### Regular File Update
```python
# User edits database.py
add_memory(
    name="src/database.py",
    episode_body=read_file("src/database.py"),
    source="filesystem_watch",  # Individual operation
    metadata={
        "operation": "update",
        "origin_path": "/project/src/database.py"
    }
)
# ✅ Included in lazy-load
```

### Git Bulk Update
```python
# Git rollback affects 47 files
for file in changed_files:
    add_memory(
        name=file.path,
        episode_body=file.content,
        source="git_bulk_update",  # Bulk operation
        metadata={
            "operation": "update",
            "git_batch_id": "uuid-abc123"
        }
    )
# ❌ Excluded from lazy-load
```

### GitAwareWatcher Logic
```python
def on_file_change(self, event):
    current_time = time.time()

    # Check if within git operation window
    if (self.last_git_event and
        current_time - self.last_git_event < 5):
        # Git batch - use git_bulk_update source
        self.pending_batch.append({
            "path": event.src_path,
            "source": "git_bulk_update"  # Bulk marker
        })
    else:
        # Individual change - use filesystem_watch source
        add_memory(
            name=event.src_path,
            episode_body=read_file(event.src_path),
            source="filesystem_watch"  # Individual marker
        )
```

## Benefits

✅ **Preserves Valuable Context**
- Individual creates/updates/deletes visible in lazy-load
- Agent knows what files user actively worked on

✅ **Eliminates Noise**
- Bulk git operations filtered out (47 files)
- Maintenance operations filtered out (moves/renames)

✅ **Token Efficiency**
- 50-500 tokens (git metadata + context + individual changes)
- vs 50k tokens (all 47 git bulk updates)
- ~99% token savings

✅ **Queryable History**
- Bulk operations still in graph
- Explicit search: `search_memory_facts(query="last git rollback files")`

## Example: Agent Session

**User works on project**:
1. Creates `auth.json` (source="filesystem_watch", operation="create")
2. Updates `database.py` (source="filesystem_watch", operation="update")
3. Runs `git reset --hard` → 47 files change (source="git_bulk_update")

**Next session lazy-load sees**:
```
✅ "Created auth.json config"
✅ "Updated database.py schema"
✅ "Git rollback: 47 files at 15:30"
✅ "Context: Serverless incompatibility"
❌ NOT: 47 individual file contents
```

## Configuration

No user-facing config changes needed. This is automatic based on:
- Git operation detection (`.git/HEAD` monitoring)
- 5-second batch window after git operation
- Source assignment based on timing

## MCP Tool Enhancement

```python
# search_memory_nodes enhancement
def search_memory_nodes(
    query: str,
    group_ids: List[str],
    exclude_sources: List[str] = None,  # NEW
    exclude_operations: List[str] = None,  # NEW
    max_nodes: int = 10
) -> List[Node]:
    """
    Args:
        exclude_sources: Sources to filter out (e.g., ["git_bulk_update"])
        exclude_operations: Operations to filter out (e.g., ["move", "rename"])
    """
    # Filter logic here
    pass
```

## Next Steps

1. Implement `exclude_sources` parameter in `search_memory_nodes`
2. Update `GitAwareWatcher` to assign `source="git_bulk_update"`
3. Test with real git workflows
4. Update CLAUDE.md INIT R8 to use new filtering
