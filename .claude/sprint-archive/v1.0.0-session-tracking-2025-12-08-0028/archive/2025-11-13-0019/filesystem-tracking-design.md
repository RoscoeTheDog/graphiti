# Filesystem Tracking Architecture Design

## Overview
Server-side automatic memory management for tracking project files and syncing to Graphiti knowledge graph.

## Requirements Summary

### Configuration
- **Storage**: `~/.graphiti/tracking-config.json` (global defaults + per-project)
- **Hierarchy**: Global defaults → Project overrides
- **No local pollution**: All configs in `~/.graphiti/`

### File Tracking
- **Patterns**: Glob patterns with include/exclude support
- **Limits**: File size limits, binary handling
- **Update Strategy**: Configurable per pattern (replace/version/archive)

### Change Detection
- **Primary**: Watchdog library (filesystem events)
- **Fallback**: 2-second polling interval
- **Debounce**: 2-second delay after last change
- **Special Handling**: File moves, renames, deletions (archived)

### Git Rollback Handling

**Problem**: `git checkout` triggers mass file changes - watchdog sees modifications but lacks git context.

**Critical UX Issue**: Context preservation during rollbacks
- Agent implements feature → realizes architecture is flawed → rolls back
- **Lost Context**: WHY the rollback happened (valuable for future decisions)
- **Confusion**: Agent either sees invalid work OR doesn't know work was abandoned

**Solution - Contextual Git Operation Tracking**:

#### Three-Tier Approach

**Tier 1: Git Metadata Episode** (ALWAYS included in lazy-load)
```python
# Lightweight summary with git context
add_memory(
    name=f"git-metadata-{batch_id}",
    episode_body="""
Git Operation Summary:
- Type: reset --hard
- From: abc123 (HEAD~5)
- To: def456 (current)
- Files affected: 47
- Branch: feature/new-architecture
- Timestamp: 2025-11-12T15:30:00Z

Context hint: Check recent conversation history for rollback reasoning
""",
    source="git_metadata",
    metadata={
        "operation": "git_metadata",  # INCLUDED in lazy-load
        "git_batch_id": batch_id,
        "commit_from": "abc123",
        "commit_to": "def456",
        "files_count": 47
    }
)
```

**Tier 2: Conversation Context Snapshot** (before rollback)
```python
# Capture WHY rollback is happening from recent conversation
# This is added WHEN git operation detected, using last N messages
add_memory(
    name=f"git-context-{batch_id}",
    episode_body="""
Conversation leading to rollback:
[Last 5 agent/user exchanges before git operation]

Agent: "I've implemented the new caching layer using Redis..."
User: "Actually this won't work with our serverless architecture"
Agent: "You're right, I should rollback and use a different approach"
User: "git reset --hard HEAD~5"
""",
    source="git_context",
    metadata={
        "operation": "git_context",  # INCLUDED in lazy-load
        "git_batch_id": batch_id,
        "captured_messages": 5
    }
)
```

**Tier 3: File State Changes** (EXCLUDED from lazy-load, queryable)
```python
# Individual file updates (47 episodes)
# Marked as bulk operations via source="git_bulk_update"
for file in changed_files:
    add_memory(
        name=file.path,
        episode_body=file.content,
        source="git_bulk_update",  # Differentiates from regular updates
        metadata={
            "operation": "update",  # Still an update operation
            "git_batch_id": batch_id,  # Links to Tier 1 metadata
            "origin_path": file.absolute_path
        }
    )
```

**Key Distinction**:
- Regular file update: `source="filesystem_watch"`, no `git_batch_id` → **INCLUDED** ✅
- Git batch update: `source="git_bulk_update"`, has `git_batch_id` → **EXCLUDED** ❌

#### Lazy-Load Query Strategy

**Default Query** (session initialization):
```python
search_memory_nodes(
    query="recent project context and decisions",
    group_ids=[GRAPHITI_GROUP_ID],
    exclude_operations=["move", "rename"],  # Maintenance only
    exclude_sources=["git_bulk_update"],  # Bulk git operations
    max_nodes=20
)

# Returns:
# ✅ Git metadata episodes (Tier 1)
# ✅ Git context snapshots (Tier 2)
# ✅ User-created memories
# ✅ Individual file creates/updates/deletes (valuable context)
# ❌ Bulk git operation file updates (Tier 3)
# ❌ File moves/renames (maintenance)
```

**Result**: Agent sees:
- "Git rollback happened at 15:30 (47 files)" (Tier 1)
- "Reason: Serverless architecture incompatibility" (Tier 2)
- "User created new config file auth.json" (individual create) ✅
- "User updated database.py with new schema" (individual update) ✅
- Current file states (from filesystem)
- NO clutter from 47 bulk git operation updates ❌

#### Implementation Enhancement

```python
class GitAwareWatcher:
    def __init__(self, conversation_buffer=None):
        self.git_head_watcher = None
        self.git_operation_window = 5
        self.pending_batch = []
        self.last_git_event = None
        self.conversation_buffer = conversation_buffer  # NEW: Recent messages

    def on_git_head_change(self, event):
        """Triggered when .git/HEAD changes"""
        self.last_git_event = time.time()
        self.git_batch_id = str(uuid.uuid4())

        # NEW: Capture git metadata
        git_info = self.get_git_operation_info()
        self.create_git_metadata_episode(git_info)

        # NEW: Capture conversation context (if available)
        if self.conversation_buffer:
            self.create_context_snapshot()

    def get_git_operation_info(self) -> dict:
        """Extract git operation details"""
        return {
            "operation_type": self.detect_git_operation(),  # reset, checkout, rebase
            "commit_from": self.get_previous_commit(),
            "commit_to": self.get_current_commit(),
            "branch": self.get_current_branch(),
            "timestamp": datetime.utcnow().isoformat()
        }

    def create_git_metadata_episode(self, git_info: dict):
        """Create Tier 1 metadata episode"""
        add_memory(
            name=f"git-metadata-{self.git_batch_id}",
            episode_body=self.format_git_summary(git_info),
            source="git_metadata",
            metadata={
                "operation": "git_metadata",  # Included in lazy-load
                "git_batch_id": self.git_batch_id,
                **git_info
            }
        )

    def create_context_snapshot(self):
        """Create Tier 2 conversation context"""
        recent_messages = self.conversation_buffer.get_last_n(5)
        add_memory(
            name=f"git-context-{self.git_batch_id}",
            episode_body=self.format_conversation(recent_messages),
            source="git_context",
            metadata={
                "operation": "git_context",  # Included in lazy-load
                "git_batch_id": self.git_batch_id
            }
        )
```

#### Conversation Buffer Integration

**MCP Server Enhancement**:
```python
class GraphitiMCPServer:
    def __init__(self):
        self.conversation_buffer = deque(maxlen=10)  # Last 10 messages
        self.filesystem_tracker = FilesystemTrackingManager(
            conversation_buffer=self.conversation_buffer
        )

    async def handle_tool_call(self, tool_name: str, args: dict):
        """Intercept tool calls to capture conversation context"""
        # Track messages for git context capture
        if tool_name == "add_memory":
            self.conversation_buffer.append({
                "timestamp": datetime.utcnow(),
                "type": "user_message",
                "content": args.get("episode_body", "")[:500]  # Truncate
            })

        # Execute tool
        result = await super().handle_tool_call(tool_name, args)
        return result
```

#### Query Filter Implementation

**Enhanced Episode Sources**:
```python
# Source types for filtering
"filesystem_watch"  # Regular file operations (create/update/delete) ✅
"git_bulk_update"   # Bulk git operations (47 files during rollback) ❌
"git_metadata"      # Git operation summary ✅
"git_context"       # Conversation snapshot ✅
"text"              # User-created memories ✅
"json"              # Structured data ✅
"message"           # Conversation format ✅
```

**Enhanced Episode Operations**:
```python
# Operation types (still valuable for specific queries)
"create"   # New file added ✅
"update"   # File modified ✅
"delete"   # File removed ✅
"move"     # File moved (maintenance) ❌
"rename"   # File renamed (maintenance) ❌
```

**Lazy-Load Logic**:
```python
# In INIT R8 or lazy-load queries
EXCLUDE_SOURCES = ["git_bulk_update"]  # Bulk operations only
EXCLUDE_OPERATIONS = ["move", "rename"]  # Maintenance only

search_memory_nodes(
    query="recent project state",
    group_ids=[GRAPHITI_GROUP_ID],
    exclude_sources=EXCLUDE_SOURCES,
    exclude_operations=EXCLUDE_OPERATIONS,
    max_nodes=20
)

# Returns:
# ✅ Regular creates/updates/deletes (source="filesystem_watch")
# ✅ Git metadata/context (source="git_metadata"/"git_context")
# ✅ User memories (source="text"/"json"/"message")
# ❌ Bulk git updates (source="git_bulk_update")
# ❌ Moves/renames (operation="move"/"rename")
```

### Episode Metadata Structure
```python
{
    "name": "project/path/to/file.md",
    "episode_body": "<file content>",
    "source": "filesystem_watch",  # or "git_metadata" or "git_context"
    "source_description": "Auto-tracked from filesystem",
    "group_id": "${GRAPHITI_GROUP_ID}",
    "metadata": {
        "origin_path": "/absolute/path/to/file.md",  # absolute path
        "file_size": 1024,
        "modified_time": "2025-11-12T10:30:00Z",
        "content_hash": "sha256:abc123...",
        "operation": "create" | "update" | "delete" | "move" | "rename",
        "git_batch_id": "uuid-if-part-of-batch",  # optional - marks bulk git operations
        "previous_path": "/old/path"  # for moves/renames
    }
}
```

**Key Change**: `git_batch_id` is the discriminator, NOT operation type.

**Operation Types**:
- `create` = New file added (valuable) ✅
- `update` = File modified (valuable) ✅
- `delete` = File removed (valuable for context) ✅
- `move` = File moved (maintenance) ❌
- `rename` = File renamed (maintenance) ❌

**Git Batch Detection**:
- `git_batch_id` present = Part of bulk git operation (exclude)
- `git_batch_id` absent = Individual file change (include)

### Query Filtering Strategy

**Key Insight**: Differentiate by **git_batch_id** (bulk ops) vs **operation type** (maintenance).

**Lazy-Load Initialization** (search_memory_nodes):
```python
# Include: create, update, delete (valuable context)
# Exclude: move, rename (maintenance), git_batch_id (bulk operations)

search_memory_nodes(
    query="recent project context",
    group_ids=[GRAPHITI_GROUP_ID],
    exclude_operations=["move", "rename"],  # Maintenance only
    exclude_git_batches=True,  # Bulk git operations
    max_nodes=20
)

# Returns:
# ✅ Individual file creates (user added new file)
# ✅ Individual file updates (user edited file)
# ✅ Individual file deletes (user removed file)
# ✅ Git metadata episodes (WHAT/WHY rollback)
# ✅ Git context episodes (conversation reasoning)
# ❌ File moves/renames (maintenance noise)
# ❌ Bulk updates from git operations (47 files)
```

**Implementation Options**:

**Option A: Metadata Filtering** (requires Graphiti enhancement)
```python
search_memory_nodes(
    query="recent sessions",
    group_ids=[GRAPHITI_GROUP_ID],
    exclude_metadata={
        "operation": ["move", "rename"],  # Maintenance
        "git_batch_id": {"exists": True}  # Bulk operations
    },
    max_nodes=20
)
```

**Option B: Source-Based Filtering** (simpler, works now)
```python
# Different sources for different purposes
search_memory_nodes(
    query="recent sessions",
    group_ids=[GRAPHITI_GROUP_ID],
    include_sources=["filesystem_watch", "git_metadata", "git_context", "text", "json", "message"],
    exclude_sources=["git_bulk_update"],  # New source type for bulk ops
    max_nodes=20
)

# Git batch file updates use source="git_bulk_update"
# Regular file updates use source="filesystem_watch"
```

**Recommended: Hybrid Approach**
```python
# Use source + operation filtering
search_memory_nodes(
    query="recent sessions",
    group_ids=[GRAPHITI_GROUP_ID],
    filters={
        "exclude": {
            "operation": ["move", "rename"],
            "source": ["git_bulk_update"]
        }
    },
    max_nodes=20
)
```

**Explicit Queries** (when needed):
```python
# Query git batch operations explicitly
search_memory_facts(
    query="files changed in last git rollback",
    group_ids=[GRAPHITI_GROUP_ID],
    filters={"source": "git_bulk_update"}
)

# Query maintenance operations
search_memory_facts(
    query="file moves and renames in last 24 hours",
    group_ids=[GRAPHITI_GROUP_ID],
    filters={"operation": ["move", "rename"]}
)
```

### Git Operation Detection Logic

**Problem with Time Windows**: User edits immediately after git operation get misclassified.

**Solution: Git-Intrinsic Detection** - Compare file content hash to git-tracked state.

```python
class GitAwareWatcher:
    def __init__(self, conversation_buffer=None):
        self.git_head_watcher = None
        self.pending_git_hashes = {}  # Expected file states from git
        self.git_batch_id = None
        self.conversation_buffer = conversation_buffer

    def on_git_head_change(self, event):
        """Triggered when .git/HEAD changes (checkout/reset/rebase)"""
        self.git_batch_id = str(uuid.uuid4())

        # Capture expected file states from git
        self.pending_git_hashes = self.get_git_tracked_file_hashes()

        # Create metadata + context episodes
        git_info = self.get_git_operation_info()
        self.create_git_metadata_episode(git_info)
        if self.conversation_buffer:
            self.create_context_snapshot()

    def get_git_tracked_file_hashes(self) -> dict:
        """Get content hashes of all git-tracked files at current HEAD"""
        result = subprocess.run(
            ["git", "ls-files", "-s"],
            capture_output=True,
            text=True,
            cwd=self.project_root
        )

        hashes = {}
        for line in result.stdout.splitlines():
            # Format: "100644 <hash> 0	<filepath>"
            parts = line.split()
            if len(parts) >= 4:
                git_hash = parts[1]
                filepath = " ".join(parts[3:])  # Handle spaces in filename
                hashes[filepath] = git_hash

        return hashes

    def on_file_change(self, event):
        """Triggered on any file change"""
        filepath = self.get_relative_path(event.src_path)

        # Calculate current file hash (git-style)
        current_hash = self.compute_git_hash(event.src_path)

        # Check if this matches expected git state
        if filepath in self.pending_git_hashes:
            expected_hash = self.pending_git_hashes[filepath]

            if current_hash == expected_hash:
                # File matches git state = git operation
                self.add_git_bulk_episode(filepath, event.src_path)
                del self.pending_git_hashes[filepath]  # Mark as processed
                return
            else:
                # File doesn't match = user edit AFTER git operation
                del self.pending_git_hashes[filepath]  # Prevent misclassification

        # Not a git operation - handle as regular file change
        self.debounce_and_process(event, source="filesystem_watch")

    def compute_git_hash(self, filepath: str) -> str:
        """Compute git-style blob hash for file content"""
        with open(filepath, "rb") as f:
            data = f.read()

        # Git hash format: "blob <size>\0<content>"
        blob = f"blob {len(data)}\0".encode() + data
        return hashlib.sha1(blob).hexdigest()

    def add_git_bulk_episode(self, rel_path: str, abs_path: str):
        """Add episode for git bulk operation"""
        add_memory(
            name=rel_path,
            episode_body=read_file(abs_path),
            source="git_bulk_update",  # Marked as bulk
            metadata={
                "operation": self.detect_operation_type(abs_path),
                "git_batch_id": self.git_batch_id,
                "origin_path": abs_path
            }
        )

    def detect_operation_type(self, filepath: str) -> str:
        """Determine if create/update/delete based on file state"""
        if not os.path.exists(filepath):
            return "delete"
        elif filepath not in self.pending_git_hashes:
            return "create"
        else:
            return "update"

    def get_git_operation_info(self) -> dict:
        """Extract git operation details"""
        return {
            "operation_type": self.detect_git_operation(),
            "commit_from": self.get_previous_commit(),
            "commit_to": self.get_current_commit(),
            "branch": self.get_current_branch(),
            "timestamp": datetime.utcnow().isoformat(),
            "files_expected": len(self.pending_git_hashes)
        }

    def create_git_metadata_episode(self, git_info: dict):
        """Create Tier 1 metadata episode"""
        add_memory(
            name=f"git-metadata-{self.git_batch_id}",
            episode_body=self.format_git_summary(git_info),
            source="git_metadata",
            metadata={
                "git_batch_id": self.git_batch_id,
                **git_info
            }
        )

    def create_context_snapshot(self):
        """Create Tier 2 conversation context"""
        recent_messages = self.conversation_buffer.get_last_n(5)
        add_memory(
            name=f"git-context-{self.git_batch_id}",
            episode_body=self.format_conversation(recent_messages),
            source="git_context",
            metadata={
                "git_batch_id": self.git_batch_id
            }
        )
```

**How It Works**:
1. **Git HEAD Change** → Capture expected file states (`git ls-files -s`)
2. **File Change Event** → Compute current file hash
3. **Compare Hashes**:
   - Matches git state? → `source="git_bulk_update"` (git operation)
   - Doesn't match? → `source="filesystem_watch"` (user edit)
4. **Remove from pending** → Prevents future misclassification

**Example**:
```bash
git reset --hard HEAD~5  # Triggers on_git_head_change()
# pending_git_hashes = {
#   "database.py": "abc123...",
#   "auth.json": "def456...",
#   ...47 more files
# }

# Watchdog fires: database.py modified
# compute_git_hash("database.py") = "abc123..."
# Matches! → source="git_bulk_update" ✓

vim database.py  # User edits immediately after
# compute_git_hash("database.py") = "xyz789..." (changed!)
# Doesn't match! → source="filesystem_watch" ✓
```

### Deletion Archival Strategy
**Problem**: Deleted files should be archived (not removed from graph) but excluded from lazy-load.

**Solution**:
```python
def on_file_deleted(self, filepath):
    """Mark episode as deleted rather than removing"""
    # Find existing episode for this file
    episodes = get_episodes_by_path(filepath)
    
    if episodes:
        # Create deletion record
        add_memory(
            name=f"{filepath}",
            episode_body=f"File deleted: {filepath}",
            source="filesystem_watch",
            metadata={
                "origin_path": filepath,
                "operation": "delete",
                "deleted_at": datetime.utcnow().isoformat(),
                "previous_episode_uuid": episodes[0].uuid
            }
        )
        
        # Mark facts as invalid (Graphiti's temporal feature)
        # This keeps data in graph but marks it as superseded
```

## MCP Tool Interface

### New MCP Tools
```python
# Configure tracking for a project
configure_file_tracking(
    project_path: str,
    patterns: List[TrackingPattern],
    options: TrackingOptions
) -> ConfigurationResult

# List currently tracked files
list_tracked_files(
    project_path: str,
    include_status: bool = True  # show pending updates
) -> List[TrackedFile]

# Manual sync trigger
sync_tracked_files(
    project_path: str,
    force: bool = False  # re-index even if unchanged
) -> SyncResult

# Enable real-time watching
enable_realtime_sync(
    project_path: str
) -> StatusResult

# Disable real-time watching
disable_realtime_sync(
    project_path: str
) -> StatusResult

# Get tracking status
get_tracking_status(
    project_path: str
) -> TrackingStatus  # includes: enabled, files_watched, pending_updates, last_sync

# Pause/resume (temporary, doesn't modify config)
pause_tracking(project_path: str) -> StatusResult
resume_tracking(project_path: str) -> StatusResult
```

### Modified MCP Tools
```python
# Remove filepath parameter (conflicts with tracking)
add_memory(
    name: str,
    episode_body: str,
    group_id: Optional[str] = None,
    source: str = "text",
    source_description: str = "",
    uuid: Optional[str] = None
    # REMOVED: filepath parameter
) -> EpisodeResult
```

## Configuration Schema

### ~/.graphiti/tracking-config.json
```json
{
  "version": "1.0",
  "defaults": {
    "enabled": true,
    "debounce_seconds": 2,
    "max_file_size_mb": 5,
    "batch_size": 10,
    "git_operation_window_seconds": 5,
    "polling_interval_seconds": 2,
    "follow_symlinks": false,
    "resilience": {
      "queue_cache_path": "~/.graphiti/cache/pending-updates.json",
      "max_queue_size": 1000,
      "retry_failed_after_seconds": 300
    }
  },
  "projects": {
    "hostname__abc123": {
      "project_root": "/absolute/path/to/project",
      "enabled": true,
      "group_id": "hostname__abc123",
      "patterns": [
        {
          "include": ".claude/**/*.md",
          "exclude": [".claude/**/archive/**"],
          "update_strategy": "replace",
          "max_file_size_mb": 5
        },
        {
          "include": "src/**/*.py",
          "exclude": ["**/__pycache__/**", "**/tests/**"],
          "update_strategy": "version",
          "source_description": "Python source code"
        }
      ],
      "ignore_patterns": [
        "**/.git/**",
        "**/*.tmp",
        "**/*.swp",
        "**/*.log"
      ]
    }
  }
}
```

### Update Strategies
- **replace**: Update existing episode (same name overwrites)
- **version**: New episode per change (temporal history)
- **archive**: Mark old as invalid, create new (deletion handling)

## Implementation Architecture

### Components
```
┌─────────────────────────────────────────────────┐
│ MCP Server (graphiti_mcp_server.py)            │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │ FilesystemTrackingManager                │   │
│  │ - Load/save config                       │   │
│  │ - Manage watchers per project            │   │
│  │ - Handle MCP tool calls                  │   │
│  └─────────────────────────────────────────┘   │
│                 │                               │
│                 ├─────────────────┐             │
│                 │                 │             │
│  ┌──────────────▼──────┐  ┌───────▼────────┐   │
│  │ ProjectWatcher      │  │ GitDetector    │   │
│  │ - Watchdog observer │  │ - Monitor HEAD │   │
│  │ - Debounce changes  │  │ - Batch window │   │
│  │ - Queue processing  │  └────────────────┘   │
│  └─────────────────────┘                        │
│                 │                               │
│  ┌──────────────▼──────────────────────────┐   │
│  │ UpdateQueue (cached to filesystem)      │   │
│  │ - Batch operations                      │   │
│  │ - Retry failed                          │   │
│  │ - Persist across restarts               │   │
│  └─────────────────────────────────────────┘   │
│                 │                               │
│  ┌──────────────▼──────────────────────────┐   │
│  │ Graphiti.add_episode()                  │   │
│  │ - Respect episode timeout               │   │
│  │ - Non-blocking for watcher              │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### File Structure
```
mcp_server/
├── graphiti_mcp_server.py          # Main MCP server (add new tools)
├── filesystem_tracking/
│   ├── __init__.py
│   ├── manager.py                  # FilesystemTrackingManager
│   ├── watcher.py                  # ProjectWatcher + GitDetector
│   ├── queue.py                    # UpdateQueue (cached)
│   ├── config.py                   # Config loading/validation
│   └── patterns.py                 # Glob pattern matching

~/.graphiti/
├── tracking-config.json            # Configuration
└── cache/
    └── pending-updates.json        # Queued changes (resilience)
```

## Rollback Scenario Example

### Scenario: Failed Architecture Attempt

**Timeline**:
```
Session 1:
- User: "Implement Redis caching layer"
- Agent: [Creates 15 files, adds Redis integration]
- User: "Wait, this won't work with our serverless deployment"
- Agent: "You're right, I should rollback. We need a different approach."
- User: "git reset --hard HEAD~5"  ← Git operation detected

Session 2 (next day):
- Agent initialization triggers lazy-load query
```

**System Behavior**:

**Step 1: Git Operation Detection**
```
GitDetector sees .git/HEAD change
├─ Captures git metadata (Tier 1)
│  ├─ Operation: reset --hard
│  ├─ From: commit abc123 (HEAD~5)
│  ├─ To: commit def456 (current)
│  ├─ Files: 47 changed
│  └─ Timestamp: 2025-11-12T15:30:00Z
│
├─ Captures conversation context (Tier 2)
│  └─ Last 5 messages before git operation:
│      "User: Wait, this won't work with serverless..."
│      "Agent: You're right, should rollback..."
│
└─ Queues file changes (Tier 3)
    └─ 47 files marked with git_batch_id
```

**Step 2: Episodes Created**
```
Episode 1 (Tier 1 - git_metadata):
  name: "git-metadata-abc123"
  body: "Git reset --hard: 47 files, feature/redis-cache → main"
  operation: "git_metadata"  ← INCLUDED in lazy-load

Episode 2 (Tier 2 - git_context):
  name: "git-context-abc123"
  body: "Conversation: Rollback due to serverless incompatibility..."
  operation: "git_context"  ← INCLUDED in lazy-load

Episodes 3-49 (Tier 3 - file updates):
  name: "src/cache/redis.py", "src/cache/config.py", ...
  body: [current file contents after rollback]
  operation: "update"  ← EXCLUDED from lazy-load
```

**Step 3: Lazy-Load Query (Session 2)**
```python
# Agent runs INIT R8
search_memory_nodes(
    query="recent project context",
    group_ids=["hostname__abc123"],
    exclude_sources=["git_bulk_update"],  # Bulk git ops
    exclude_operations=["move", "rename"],  # Maintenance
    max_nodes=20
)

# Returns:
[
  Episode 1: "Git rollback at 15:30 (47 files)",  ✅ (git_metadata)
  Episode 2: "Context: Serverless incompatibility", ✅ (git_context)
  Episode 3: "User created auth.json config", ✅ (filesystem_watch, create)
  Episode 4: "User updated database.py schema", ✅ (filesystem_watch, update)
  Episode 5: "User preference: Use DynamoDB instead", ✅ (text)
  Episode 6: "Project convention: Avoid Redis", ✅ (text)
  ... (14 more valuable episodes)
]

# NOT returned (excluded):
# - 47 bulk git update episodes (source="git_bulk_update") ❌
# - File moves/renames (operation="move"/"rename") ❌
```

**Step 4: Agent Context (Session 2)**
```
Agent sees:
✅ "Git rollback happened yesterday at 15:30"
✅ "Reason: Redis incompatible with serverless architecture"
✅ "User created auth.json config" (individual file create)
✅ "User updated database.py schema" (individual file update)
✅ "User prefers DynamoDB for caching"
✅ Current file state (from filesystem - no Redis code)

Agent does NOT see:
❌ 47 bulk git update episodes (filtered by source="git_bulk_update")
❌ Old Redis implementation details (unless explicitly queries)
❌ File moves/renames (filtered by operation)

Result: Agent understands:
- Work was rolled back (not just disappeared)
- WHY it was rolled back (architectural mismatch)
- What individual files were created/updated (valuable context)
- What to avoid next time (Redis in serverless)
```

### Comparison: Old vs New Approach

**Old Approach (Binary Include/Exclude)**:
```
Option A: Include git_batch
  ❌ Lazy-load: "git-operation: 47 files changed" (no context WHY)
  ❌ Agent: "I see files changed, but no reasoning"

Option B: Exclude git_batch
  ❌ Lazy-load: Pre-rollback state visible (thinks Redis code still exists)
  ❌ Agent: "I see Redis implementation, should I continue?"
```

**New Approach (Three-Tier)**:
```
✅ Lazy-load:
   - Git metadata (WHAT happened)
   - Conversation context (WHY it happened)
   - No file spam (Tier 3 excluded)

✅ Agent:
   - "Rollback occurred due to serverless incompatibility"
   - "Should use DynamoDB instead"
   - Current state is correct (filesystem)
```

## Benefits
- ✅ Handles mass changes gracefully
- ✅ Preserves temporal history (old + new states)
- ✅ Doesn't pollute lazy-load context (file updates excluded)
- ✅ Preserves decision context (WHY rollback happened)
- ✅ Queryable for debugging ("show me last git operation")
- ✅ Works for any bulk operation (not just git)
- ✅ **NEW**: Agent understands project history and decisions

## Next Steps
1. Implement `GitDetector` (monitors .git/HEAD)
2. Enhance `search_memory_nodes` with metadata filtering
3. Add `git_batch_id` to episode metadata schema
4. Test with real git workflows (checkout, reset, rebase)
