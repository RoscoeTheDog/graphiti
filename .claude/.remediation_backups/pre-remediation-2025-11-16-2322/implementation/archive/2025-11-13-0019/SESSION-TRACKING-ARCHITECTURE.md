# Session Tracking Architecture - Technical Deep Dive

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude Code Agent Session                                      │
│  (User working on project)                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ Writes to
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ~/.claude/projects/{hash}/sessions/{session-id}.jsonl         │
│  (Conversation log - written by Claude Code CLI)               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ Monitored by
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Graphiti MCP Server - Session Tracking Service                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  File Watcher (watchdog)                                 │  │
│  │  - Monitors ~/.claude/projects/                          │  │
│  │  - Detects new/modified JSONL files                      │  │
│  │  - Incremental reading (offset tracking)                 │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                         │
│                       ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  JSONL Parser + Filter                                   │  │
│  │  - Parse messages (user/assistant/tool)                  │  │
│  │  - Extract MCP tool interactions                         │  │
│  │  - Apply smart filtering (93% token reduction)           │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                         │
│                       ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Session Manager                                         │  │
│  │  - Track active sessions (in-memory registry)            │  │
│  │  - Detect session close (inactivity timeout)             │  │
│  │  - Trigger summarization                                 │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                         │
│                       ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  LLM Summarizer                                          │  │
│  │  - Use Graphiti LLM client (gpt-4.1-mini)               │  │
│  │  - Extract structured summary                            │  │
│  │  - Cost: ~$0.03-$0.10 per session                        │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                         │
│                       ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Graphiti Storage                                        │  │
│  │  - Store as EpisodicNode                                 │  │
│  │  - Create relations (preceded_by, continued_by, etc.)    │  │
│  │  - Metadata: tools used, files modified, costs           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ Query via
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Future Agent Sessions                                          │
│  - "What were we working on last time?"                         │
│  - "Why did we choose approach X?"                              │
│  - "How did we solve this error before?"                        │
└─────────────────────────────────────────────────────────────────┘
```

## Module Dependency Graph (Detailed)

### Layer 1: Core Types (No dependencies)

**`graphiti_core/session_tracking/types.py`**
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class TokenUsage:
    """Token usage from Claude API response"""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        return sum([self.input_tokens, self.output_tokens, 
                   self.cache_read_tokens, self.cache_creation_tokens])

@dataclass
class ToolCall:
    """Extracted tool call from conversation"""
    tool_id: str
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[str] = None
    is_error: bool = False
    is_mcp: bool = False  # True if mcp__ prefix

@dataclass
class SessionMessage:
    """Single message in conversation"""
    uuid: str
    session_id: str
    role: str  # "user" | "assistant"
    timestamp: datetime
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    tokens: Optional[TokenUsage] = None

@dataclass
class ConversationContext:
    """Filtered conversation ready for summarization"""
    session_id: str
    project_root: str
    messages: List[SessionMessage]
    mcp_interactions: List[ToolCall]
    files_touched: List[str]
    start_time: datetime
    end_time: datetime
    total_tokens: int
    filtered_token_estimate: int  # After 93% reduction

@dataclass
class SessionMetadata:
    """Metadata for Graphiti storage"""
    session_id: str
    project_root: str
    message_count: int
    token_count: int
    filtered_token_count: int
    mcp_tools_used: List[str]
    files_modified: List[str]
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    llm_cost_estimate: float
```

**Dependencies**: None (pure dataclasses)

---

### Layer 2: Path Resolution & Parsing

**`graphiti_core/session_tracking/path_resolver.py`**
```python
from pathlib import Path
import hashlib
from typing import Optional

class ClaudePathResolver:
    """Resolve Claude Code JSONL file paths"""
    
    @staticmethod
    def get_projects_dir() -> Path:
        """Get ~/.claude/projects directory"""
        return Path.home() / ".claude" / "projects"
    
    @staticmethod
    def project_to_hash(project_root: str) -> str:
        """Convert project root to Claude Code hash"""
        # Claude Code uses sha256 hash of path
        # Example: C:/Users/Admin/Documents/GitHub/graphiti
        #       → c1a2b3c4d5e6f7g8
        normalized = Path(project_root).as_posix()
        hash_full = hashlib.sha256(normalized.encode()).hexdigest()
        return hash_full[:16]  # First 16 chars
    
    @staticmethod
    def get_session_dir(project_root: str) -> Path:
        """Get session directory for project"""
        projects_dir = ClaudePathResolver.get_projects_dir()
        project_hash = ClaudePathResolver.project_to_hash(project_root)
        return projects_dir / project_hash / "sessions"
    
    @staticmethod
    def find_session_files(project_root: str) -> List[Path]:
        """Find all JSONL session files for project"""
        session_dir = ClaudePathResolver.get_session_dir(project_root)
        if not session_dir.exists():
            return []
        return list(session_dir.glob("*.jsonl"))
```

**Dependencies**: `types.py` (for type hints only)

---

**`graphiti_core/session_tracking/parser.py`**

**Source**: Extracted from `claude-window-watchdog/src/claude_window_watchdog/daemon/parser.py`

**Changes**:
- Remove `store_content` parameter (always extract content)
- Add tool call extraction logic
- Add MCP tool detection (`mcp__` prefix)
- Return `SessionMessage` instead of `MessageData`
- Add `parse_session_file()` method (full session parsing)

```python
import json
from typing import Optional, List, Tuple
from datetime import datetime
from pathlib import Path

from graphiti_core.session_tracking.types import (
    SessionMessage, ToolCall, TokenUsage
)

class JSONLParser:
    """Parse Claude Code JSONL conversation files"""
    
    def parse_line(self, line: str) -> Optional[SessionMessage]:
        """Parse single JSONL line into SessionMessage"""
        # Extract from watchdog implementation
        # Add tool call extraction
        # Add MCP detection
    
    def extract_tool_calls(self, content: List[Dict]) -> List[ToolCall]:
        """Extract tool calls from message content"""
        # NEW: Identify tool_use blocks
        # NEW: Match with tool_result blocks
        # NEW: Detect MCP tools (mcp__ prefix)
    
    def parse_file(
        self, 
        file_path: Path, 
        start_offset: int = 0
    ) -> Tuple[List[SessionMessage], int]:
        """Parse JSONL file from offset, return messages and new offset"""
        # Extracted from watchdog (minor changes)
    
    def parse_session_file(self, file_path: Path) -> List[SessionMessage]:
        """Parse entire session file (for closed sessions)"""
        # NEW: Convenience method for full file parsing
```

**Dependencies**: `types.py`

---

### Layer 3: Filtering & Utilities

**`graphiti_core/session_tracking/filter.py`**

**Source**: NEW (based on handoff design docs)

**Purpose**: Smart filtering to achieve 93% token reduction

```python
from typing import List
from graphiti_core.session_tracking.types import (
    SessionMessage, ConversationContext, ToolCall
)

class SessionFilter:
    """Smart filtering for token reduction"""
    
    def filter_session(
        self, 
        messages: List[SessionMessage],
        session_id: str,
        project_root: str
    ) -> ConversationContext:
        """
        Apply smart filtering to reduce tokens by ~93%
        
        Filtering rules:
        - KEEP: All user messages (full content)
        - KEEP: All assistant text responses (full content)
        - KEEP: Tool call structure (name + params)
        - OMIT: Tool results (replace with 1-line summary)
        - EXTRACT: MCP tool interactions separately
        - EXTRACT: Files touched (from Write/Edit tools)
        """
    
    def _summarize_tool_result(self, result: str, tool_name: str) -> str:
        """
        Create 1-line summary of tool result
        
        Examples:
        - Read(file.py) → "File read: 245 lines"
        - Grep(pattern) → "Found 12 matches across 5 files"
        - Edit(file.py) → "Modified: file.py:123-145"
        """
    
    def _extract_files_touched(
        self, 
        messages: List[SessionMessage]
    ) -> List[str]:
        """Extract files from Write/Edit/Read tool calls"""
    
    def _estimate_filtered_tokens(
        self, 
        context: ConversationContext
    ) -> int:
        """Rough token estimate after filtering"""
        # Use: len(text) / 4 heuristic
```

**Dependencies**: `types.py`, `parser.py`

---

### Layer 4: Monitoring

**`graphiti_core/session_tracking/watcher.py`**

**Source**: Extracted from `claude-window-watchdog/src/claude_window_watchdog/daemon/watcher.py`

**Changes**:
- Remove SQLite database storage
- Use callback pattern instead
- Add session lifecycle detection
- Integration with `SessionManager`

```python
from pathlib import Path
from typing import Dict, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from graphiti_core.session_tracking.parser import JSONLParser
from graphiti_core.session_tracking.types import SessionMessage

class JSONLFileHandler(FileSystemEventHandler):
    """Handle JSONL file events"""
    
    def __init__(
        self,
        parser: JSONLParser,
        file_offsets: Dict[str, int],
        on_new_messages: Callable[[List[SessionMessage]], None]
    ):
        self.parser = parser
        self.file_offsets = file_offsets
        self.on_new_messages = on_new_messages
    
    def on_modified(self, event):
        """Handle file modification"""
        # Extract from watchdog implementation
        # Replace database storage with callback
    
    def on_created(self, event):
        """Handle new session file"""
        # Extract from watchdog implementation

class SessionFileWatcher:
    """Watch Claude Code session files"""
    
    def __init__(
        self,
        projects_dir: Path,
        on_new_messages: Callable[[List[SessionMessage]], None]
    ):
        self.projects_dir = projects_dir
        self.on_new_messages = on_new_messages
        self.observer = Observer()
        # ...
    
    def start(self):
        """Start watching"""
    
    def stop(self):
        """Stop watching"""
    
    def is_running(self) -> bool:
        """Check if watcher is active"""
```

**Dependencies**: `types.py`, `parser.py`

---

**`graphiti_core/session_tracking/session_manager.py`**

**Source**: NEW (orchestration layer)

**Purpose**: Manage active sessions, detect close, trigger summarization

```python
from typing import Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
import asyncio

from graphiti_core.session_tracking.types import SessionMessage, ConversationContext
from graphiti_core.session_tracking.parser import JSONLParser
from graphiti_core.session_tracking.filter import SessionFilter
from graphiti_core.session_tracking.watcher import SessionFileWatcher

class SessionManager:
    """Orchestrate session tracking lifecycle"""
    
    def __init__(
        self,
        graphiti_instance,  # Graphiti for storage
        inactivity_timeout: int = 300,  # 5 minutes
        auto_summarize: bool = True
    ):
        self.graphiti = graphiti_instance
        self.inactivity_timeout = inactivity_timeout
        self.auto_summarize = auto_summarize
        
        # Active session registry
        self.active_sessions: Dict[str, SessionState] = {}
        
        # Components
        self.parser = JSONLParser()
        self.filter = SessionFilter()
        self.watcher = SessionFileWatcher(
            projects_dir=Path.home() / ".claude" / "projects",
            on_new_messages=self._on_new_messages
        )
    
    def start(self):
        """Start session monitoring"""
        self.watcher.start()
        # Start inactivity checker background task
        asyncio.create_task(self._check_inactive_sessions())
    
    def stop(self):
        """Stop session monitoring"""
        self.watcher.stop()
    
    def enable_session(self, session_id: str, project_root: str, force: bool = False):
        """Enable tracking for specific session (MCP tool call)"""
        # Add to active_sessions registry
        # Override global config if force=True
    
    def disable_session(self, session_id: str):
        """Disable tracking for specific session (MCP tool call)"""
        # Remove from active_sessions registry
    
    def _on_new_messages(self, messages: List[SessionMessage]):
        """Callback when new messages detected"""
        # Update last_activity timestamp for session
        # If session not in registry, check global config
    
    async def _check_inactive_sessions(self):
        """Background task: check for inactive sessions"""
        while True:
            await asyncio.sleep(60)  # Check every minute
            
            for session_id, state in self.active_sessions.items():
                inactive_time = datetime.now() - state.last_activity
                
                if inactive_time > timedelta(seconds=self.inactivity_timeout):
                    # Session is inactive, trigger close
                    await self._close_session(session_id, state)
    
    async def _close_session(self, session_id: str, state: "SessionState"):
        """Handle session close"""
        # Parse full session file
        # Apply filtering
        # Trigger summarization (if auto_summarize=True)
        # Store in Graphiti
        # Remove from active_sessions
```

**Dependencies**: `types.py`, `parser.py`, `filter.py`, `watcher.py`

---

### Layer 5: Summarization & Storage

**`graphiti_core/session_tracking/summarizer.py`**

**Source**: NEW (LLM-based summarization)

**Purpose**: Use Graphiti LLM client to generate structured summaries

```python
from typing import Dict, Any
from graphiti_core.llm_client import LLMClient
from graphiti_core.session_tracking.types import ConversationContext

class SessionSummarizer:
    """LLM-based session summarization"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    async def summarize(
        self, 
        context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Generate structured summary of session
        
        Returns:
            Dict with keys:
            - objective: str
            - work_completed: Dict[str, List[str]]
            - external_research: Dict[str, Any]
            - knowledge_stored: Dict[str, List[str]]
            - decisions: List[str]
            - unresolved: List[str]
            - next_steps: List[str]
            - continuation_context: str
        """
        prompt = self._build_prompt(context)
        
        # Use Graphiti LLM client (gpt-4.1-mini for cost)
        response = await self.llm_client.generate_text(
            prompt=prompt,
            model="gpt-4.1-mini",
            max_tokens=2000
        )
        
        # Parse JSON response
        summary = json.loads(response)
        return summary
    
    def _build_prompt(self, context: ConversationContext) -> str:
        """Build LLM prompt from handoff template"""
        # Use prompt template from handoff docs
        # Format: conversation, MCP interactions, files touched
```

**Dependencies**: `types.py`, Graphiti LLM client

---

**`graphiti_core/session_tracking/graphiti_storage.py`**

**Source**: NEW (Graphiti integration)

**Purpose**: Store session summaries as EpisodicNodes with relations

```python
from typing import Dict, Any
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodicNode
from graphiti_core.session_tracking.types import SessionMetadata

class SessionStorage:
    """Store sessions in Graphiti graph"""
    
    def __init__(self, graphiti: Graphiti):
        self.graphiti = graphiti
    
    async def store_session(
        self,
        session_id: str,
        summary: Dict[str, Any],
        metadata: SessionMetadata,
        group_id: str
    ) -> str:
        """
        Store session as EpisodicNode
        
        Returns:
            Episode UUID
        """
        episode_name = f"session_{session_id[:8]}"
        
        # Format summary as episode content
        content = self._format_summary(summary)
        
        # Store as episode
        episode_uuid = await self.graphiti.add_episode(
            name=episode_name,
            episode_body=content,
            source="claude_code_jsonl",
            source_description=f"Session from {metadata.project_root}",
            reference_time=metadata.end_time,
            group_id=group_id
        )
        
        # Add custom metadata (not supported yet in add_episode)
        # TODO: Enhance Graphiti to support episode metadata
        
        return episode_uuid
    
    def _format_summary(self, summary: Dict[str, Any]) -> str:
        """Format summary dict as markdown for episode_body"""
        # Convert structured summary to readable markdown
```

**Dependencies**: `types.py`, Graphiti core

---

### Layer 6: MCP Integration

**`mcp_server/session_tracking_service.py`**

**Source**: NEW (service facade)

**Purpose**: Integrate session tracking with MCP server

```python
from graphiti_core.session_tracking.session_manager import SessionManager
from mcp_server.unified_config import get_config

class SessionTrackingService:
    """Service layer for MCP server integration"""
    
    def __init__(self, graphiti_instance):
        self.graphiti = graphiti_instance
        
        # Load config
        config = get_config()
        st_config = config.session_tracking
        
        # Initialize session manager
        self.manager = SessionManager(
            graphiti_instance=graphiti_instance,
            inactivity_timeout=st_config.inactivity_timeout,
            auto_summarize=st_config.auto_summarize_on_close
        )
        
        # Start if globally enabled
        if st_config.enabled:
            self.manager.start()
    
    def enable(self):
        """Enable session tracking globally"""
        self.manager.start()
        # Update config file
    
    def disable(self):
        """Disable session tracking globally"""
        self.manager.stop()
        # Update config file
    
    def track_session(self, session_id: str, group_id: str, force: bool = False):
        """Enable tracking for specific session (MCP tool)"""
        # Extract project_root from JSONL path
        project_root = self._resolve_project_root(session_id)
        self.manager.enable_session(session_id, project_root, force)
    
    def stop_tracking_session(self, session_id: str):
        """Disable tracking for specific session (MCP tool)"""
        self.manager.disable_session(session_id)
    
    def get_status(self) -> Dict[str, Any]:
        """Get tracking status (MCP tool)"""
        return {
            "global_enabled": self.manager.watcher.is_running(),
            "active_sessions": len(self.manager.active_sessions),
            "sessions": [
                {
                    "session_id": sid,
                    "project_root": state.project_root,
                    "last_activity": state.last_activity.isoformat()
                }
                for sid, state in self.manager.active_sessions.items()
            ]
        }
```

**Dependencies**: `session_manager.py`, unified_config

---

**`mcp_server/graphiti_mcp_server.py` (updated)**

**Changes**: Register MCP tools

```python
from mcp_server.session_tracking_service import SessionTrackingService

# Initialize service
session_tracking = SessionTrackingService(graphiti_instance)

@mcp.tool()
def track_session(group_id: str, force: bool = False) -> str:
    \"\"\"
    Enable session tracking for current session.
    
    Use this when you want to automatically track the current conversation
    to Graphiti memory, even if global session tracking is disabled.
    
    Args:
        group_id: Graphiti group ID for session storage
        force: Force tracking even if globally disabled
    
    Returns:
        Success message with session ID
    \"\"\"
    # Extract session_id from current context (how?)
    # Call session_tracking.track_session()

@mcp.tool()
def stop_tracking_session(session_id: str) -> str:
    \"\"\"Stop tracking for specific session.\"\"\"
    session_tracking.stop_tracking_session(session_id)
    return f"Stopped tracking session {session_id}"

@mcp.tool()
def get_session_tracking_status() -> dict:
    \"\"\"Get current session tracking status.\"\"\"
    return session_tracking.get_status()
```

**Challenge**: How to get current session_id from within MCP tool?
- Option 1: Agent provides it as parameter
- Option 2: Inspect environment variables (if available)
- Option 3: Parse JSONL directory for most recent active session

---

## CLI Integration

**`graphiti-mcp` CLI enhancement**

Add subcommands:

```bash
graphiti-mcp session-tracking enable
graphiti-mcp session-tracking disable
graphiti-mcp session-tracking status
```

Implementation in `mcp_server/__main__.py` or similar CLI entry point.

---

## Configuration Schema

**`graphiti.config.json`** additions:

```json
{
  "version": "2.0",
  "session_tracking": {
    "enabled": false,
    "auto_summarize_on_close": true,
    "inactivity_timeout": 300,
    "filtering": {
      "keep_user_messages": true,
      "keep_agent_responses": true,
      "keep_tool_structure": true,
      "omit_tool_outputs": true
    },
    "summarization": {
      "model": "gpt-4.1-mini",
      "max_summary_tokens": 2000
    }
  }
}
```

**`mcp_server/unified_config.py`** schema:

```python
class SessionTrackingFilteringConfig(BaseModel):
    keep_user_messages: bool = True
    keep_agent_responses: bool = True
    keep_tool_structure: bool = True
    omit_tool_outputs: bool = True

class SessionTrackingSummarizationConfig(BaseModel):
    model: str = "gpt-4.1-mini"
    max_summary_tokens: int = 2000

class SessionTrackingConfig(BaseModel):
    enabled: bool = False
    auto_summarize_on_close: bool = True
    inactivity_timeout: int = 300
    filtering: SessionTrackingFilteringConfig = Field(default_factory=SessionTrackingFilteringConfig)
    summarization: SessionTrackingSummarizationConfig = Field(default_factory=SessionTrackingSummarizationConfig)

class GraphitiConfig(BaseModel):
    # ... existing fields ...
    session_tracking: SessionTrackingConfig = Field(default_factory=SessionTrackingConfig)
```

---

## Testing Strategy

### Unit Tests

1. **test_parser.py**: JSONL parsing
2. **test_filter.py**: Token reduction
3. **test_path_resolver.py**: Path resolution
4. **test_summarizer.py**: LLM summarization (with mocks)

### Integration Tests

1. **test_session_manager.py**: Full lifecycle
2. **test_watcher.py**: File monitoring (with temp files)
3. **test_graphiti_storage.py**: Graph storage (with test Graphiti instance)

### End-to-End Tests

1. **test_e2e_session_tracking.py**: Complete workflow with real JSONL files

---

## Open Questions

1. **How to get current session_id in MCP tool context?**
   - Need to investigate MCP server context/request metadata
   
2. **Should we track agent-spawned sessions separately?**
   - `agent-{id}.jsonl` files have parent linkage
   - Store as separate episodes with `spawned_agent` relation?

3. **How to handle auto-compaction (session continuation)?**
   - Detect new JSONL file with continuation context
   - Create `continued_by` relation to new session

4. **Performance impact on MCP server?**
   - File watcher runs in separate thread
   - LLM summarization is async
   - Should be negligible, but needs testing

---

## Success Metrics

- **Parsing accuracy**: 100% of messages extracted correctly
- **Token reduction**: 90%+ reduction from filtering
- **Summarization quality**: Context preserved (human evaluation)
- **Cost**: <$0.50 per session
- **Performance**: <5% overhead on MCP server
- **Reliability**: No crashes or data loss over 100+ sessions

---

## Next Steps

1. Begin Phase 1 implementation (Foundation)
2. Create test fixtures (sample JSONL files)
3. Set up continuous integration for tests
4. Document each module as implemented