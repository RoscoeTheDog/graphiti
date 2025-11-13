# Session Tracking Troubleshooting Guide

## Quick Diagnostic Checklist

Run through this checklist to diagnose most common issues:

```bash
# 1. Check if tracking is enabled
graphiti-mcp session-tracking status

# 2. Verify MCP server is running
ps aux | grep graphiti  # Unix
tasklist | findstr graphiti  # Windows

# 3. Check recent logs
tail -f ~/.local/state/graphiti/logs/mcp-server.log  # Unix
type %USERPROFILE%\.local\state\graphiti\logs\mcp-server.log  # Windows

# 4. Test Graphiti connection
# In Python
from graphiti_core.graphiti import Graphiti
graphiti = Graphiti()  # Should connect without errors

# 5. Check file watcher
# Look for "Watching N directories" in logs
```

---

## Issue Categories

### 1. Sessions Not Being Tracked

#### Symptom
Claude Code sessions are not appearing in Graphiti knowledge graph.

#### Diagnostic Steps

**Step 1: Verify tracking is enabled**
```bash
graphiti-mcp session-tracking status
# Expected output: "Session tracking: enabled"
```

If disabled:
```bash
graphiti-mcp session-tracking enable
```

**Step 2: Check MCP server logs**
```bash
# Look for file watcher initialization
grep "SessionFileWatcher" ~/.local/state/graphiti/logs/mcp-server.log

# Expected output:
# [INFO] SessionFileWatcher initialized
# [INFO] Watching 1 directories: ['/home/user/.claude/projects']
```

If no output, MCP server may not have session tracking enabled or has crashed.

**Step 3: Verify JSONL files exist**
```bash
# Check session directory
ls -la ~/.claude/projects/*/sessions/*.jsonl

# Should show JSONL files like:
# -rw-r--r-- 1 user user 45678 Nov 13 15:30 a1b2c3d4-e5f6-7890.jsonl
```

If no files, Claude Code may not be writing sessions, or project hash is incorrect.

**Step 4: Test file watcher manually**
```python
# test_watcher.py
from graphiti_core.session_tracking import SessionFileWatcher

def on_created(path):
    print(f"File created: {path}")
    
def on_modified(path):
    print(f"File modified: {path}")
    
watcher = SessionFileWatcher(
    watch_directories=["~/.claude/projects"],
    on_file_created=on_created,
    on_file_modified=on_modified,
    on_file_deleted=lambda p: None
)

watcher.start()
print("Watcher running... create a JSONL file to test")
input("Press Enter to stop")
watcher.stop()
```

**Step 5: Check for errors in session manager**
```bash
grep "SessionManager" ~/.local/state/graphiti/logs/mcp-server.log | grep ERROR
```

Common errors:
- `FileNotFoundError`: Watch directory doesn't exist
- `PermissionError`: No read access to session files
- `JSONDecodeError`: Malformed JSONL file

#### Common Causes & Solutions

**Cause 1: Tracking disabled globally**
```bash
# Solution
graphiti-mcp session-tracking enable
```

**Cause 2: MCP server not running**
```bash
# Solution: Start MCP server
graphiti-mcp start

# Or check status
graphiti-mcp status
```

**Cause 3: Wrong watch directory**
```json
// Solution: Update graphiti.config.json
{
  "session_tracking": {
    "watch_directories": [
      "~/.claude/projects",  // Correct path
      // "C:/Users/Admin/.claude/projects"  // Windows absolute path
    ]
  }
}
```

**Cause 4: Project hash mismatch**
```python
# Debug project hash calculation
from graphiti_core.session_tracking import ClaudePathResolver

resolver = ClaudePathResolver()
project_root = "/home/user/my-project"
sessions_dir = resolver.get_sessions_dir(project_root)
print(f"Sessions directory: {sessions_dir}")

# Check if directory exists
import os
print(f"Exists: {os.path.exists(sessions_dir)}")
```

---

### 2. High CPU/Memory Usage

#### Symptom
MCP server using excessive CPU or memory.

#### Diagnostic Steps

**Step 1: Check resource usage**
```bash
# Unix
top -p $(pgrep -f graphiti-mcp)

# Windows
tasklist /FI "IMAGENAME eq python.exe" /V
```

**Step 2: Identify bottleneck**
```bash
# Check log frequency
wc -l ~/.local/state/graphiti/logs/mcp-server.log

# If thousands of lines per minute, file watcher may be in tight loop
```

**Step 3: Review scan interval**
```json
// Check graphiti.config.json
{
  "session_tracking": {
    "scan_interval_seconds": 2  // Lower = higher CPU
  }
}
```

#### Common Causes & Solutions

**Cause 1: Scan interval too low**
```json
// Solution: Increase scan interval
{
  "session_tracking": {
    "scan_interval_seconds": 5  // Increase from 2 to 5 seconds
  }
}
```

**Cause 2: Watching too many directories**
```json
// Solution: Limit watch scope
{
  "session_tracking": {
    "watch_directories": [
      "~/.claude/projects/a1b2c3d4"  // Specific project only
    ]
  }
}
```

**Cause 3: Rapid file changes during builds**
```bash
# Solution: Exclude build directories
# Add to watch directory ignore patterns (if supported by watchdog)
# Or disable tracking temporarily during builds
graphiti-mcp session-tracking disable
# ... run build ...
graphiti-mcp session-tracking enable
```

**Cause 4: Memory leak in session manager**
```bash
# Check number of active sessions
grep "sessions in registry" ~/.local/state/graphiti/logs/mcp-server.log | tail -1

# If number keeps growing, sessions aren't being closed
# Reduce inactivity timeout
```

```json
{
  "session_tracking": {
    "inactivity_timeout_minutes": 15  // Reduce from 30 to 15
  }
}
```

---

### 3. Missing Session Context

#### Symptom
Claude Code doesn't remember past work, queries return no results.

#### Diagnostic Steps

**Step 1: Verify sessions are indexed**
```python
# query_sessions.py
from graphiti_core.graphiti import Graphiti

graphiti = Graphiti()
episodes = await graphiti.get_episodes(
    group_id="hostname__projecthash",
    limit=10
)

print(f"Found {len(episodes)} episodes")
for ep in episodes:
    print(f"- {ep.name} ({ep.created_at})")
```

If no episodes found, sessions are not being indexed.

**Step 2: Check group ID**
```python
# check_group_id.py
from graphiti_core.session_tracking import ClaudePathResolver
import os

hostname = os.uname().nodename  # Unix
# hostname = os.environ['COMPUTERNAME']  # Windows

project_root = "/home/user/my-project"
resolver = ClaudePathResolver()
project_hash = resolver._calculate_hash(project_root)

group_id = f"{hostname}__{project_hash}"
print(f"Expected group ID: {group_id}")

# Compare with actual episodes
episodes = await graphiti.get_episodes(group_id=group_id, limit=1)
if episodes:
    print(f"Actual group ID: {episodes[0].group_id}")
```

**Step 3: Test search query**
```python
# Test semantic search
results = await graphiti.search(
    query="authentication implementation",
    group_id="hostname__hash",
    limit=5
)

print(f"Found {len(results)} results")
for result in results:
    print(f"- {result.content[:100]}...")
```

#### Common Causes & Solutions

**Cause 1: Group ID mismatch**
```python
# Solution: Recalculate correct group ID
# Sessions from different group IDs won't be found

# Verify project root normalization
from graphiti_core.session_tracking.path_resolver import ClaudePathResolver

resolver = ClaudePathResolver()

# Windows
project_root_windows = "C:\\Users\\Admin\\project"
project_root_unix = resolver._to_unix_path(project_root_windows)
print(f"Normalized: {project_root_unix}")  # Should be /c/Users/Admin/project

# Calculate hash from normalized path
hash_value = resolver._calculate_hash(project_root_windows)
print(f"Hash: {hash_value}")
```

**Cause 2: Sessions indexed but not closed yet**
```bash
# Solution: Wait for inactivity timeout (default 30 min)
# Or force close by stopping MCP server
graphiti-mcp stop
graphiti-mcp start

# Sessions should be indexed on shutdown
```

**Cause 3: Query too specific**
```python
# Solution: Use broader queries
# Instead of: "why did we choose FastAPI over Flask for API implementation"
# Try: "API framework choice"

results = await graphiti.search(
    query="API framework",  # Broader
    group_id="hostname__hash",
    limit=10
)
```

**Cause 4: Wrong search method**
```python
# Solution: Use search_nodes for entities, search_facts for relationships

# For entities (files, tools, patterns)
nodes = await graphiti.search_nodes(
    query="authentication",
    group_ids=["hostname__hash"],
    max_nodes=10
)

# For relationships (connections between entities)
facts = await graphiti.search_facts(
    query="authentication uses JWT",
    group_ids=["hostname__hash"],
    max_facts=10
)
```

---

### 4. Indexing Errors

#### Symptom
Sessions detected but fail to index to Graphiti.

#### Diagnostic Steps

**Step 1: Check indexing errors**
```bash
grep "SessionIndexer.*ERROR" ~/.local/state/graphiti/logs/mcp-server.log
```

**Step 2: Test Graphiti connection**
```python
# test_graphiti.py
from graphiti_core.graphiti import Graphiti

try:
    graphiti = Graphiti()
    # Try adding a test episode
    uuid = await graphiti.add_episode(
        name="Test Episode",
        episode_body="This is a test",
        source="text",
        reference_time=datetime.now()
    )
    print(f"Test episode created: {uuid}")
except Exception as e:
    print(f"Graphiti error: {e}")
```

**Step 3: Check OpenAI API key**
```bash
# Verify API key is set
echo $OPENAI_API_KEY  # Unix
echo %OPENAI_API_KEY%  # Windows

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### Common Causes & Solutions

**Cause 1: Graphiti not initialized**
```python
# Solution: Initialize Graphiti properly
from graphiti_core.graphiti import Graphiti

graphiti = Graphiti()
await graphiti.build_indices()  # Build Neo4j indices
```

**Cause 2: Neo4j connection failed**
```bash
# Solution: Check Neo4j status
neo4j status

# Check connection string in config
cat graphiti.config.json | grep neo4j_uri

# Test connection
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "neo4j://localhost:7687",
    auth=("neo4j", "password")
)
driver.verify_connectivity()
```

**Cause 3: OpenAI API quota exceeded**
```bash
# Solution: Check API usage at https://platform.openai.com/usage

# Use cheaper model (gpt-4o-mini)
# Verify in graphiti.config.json:
{
  "llm_model": "gpt-4o-mini"  // Not gpt-4
}
```

**Cause 4: Content too large**
```bash
# Solution: Verify filtering is working
grep "Token reduction" ~/.local/state/graphiti/logs/mcp-server.log

# Should see: "Token reduction: 93% (10000 -> 700 tokens)"

# If not, filter may be disabled or broken
```

---

### 5. File Watcher Not Detecting Changes

#### Symptom
New JSONL files created but not detected by file watcher.

#### Diagnostic Steps

**Step 1: Test watchdog directly**
```python
# test_watchdog.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TestHandler(FileSystemEventHandler):
    def on_created(self, event):
        print(f"Created: {event.src_path}")
    def on_modified(self, event):
        print(f"Modified: {event.src_path}")

handler = TestHandler()
observer = Observer()
observer.schedule(handler, "~/.claude/projects", recursive=True)
observer.start()

print("Watching... create a file to test")
input("Press Enter to stop")
observer.stop()
observer.join()
```

**Step 2: Check directory permissions**
```bash
# Unix
ls -ld ~/.claude/projects/*/sessions/
# Should show: drwxr-xr-x (readable)

# Windows
icacls %USERPROFILE%\.claude\projects
# Should show: (F) Full control or (R) Read
```

**Step 3: Verify watchdog is installed**
```bash
pip list | grep watchdog
# Should show: watchdog==6.0.0 or higher
```

#### Common Causes & Solutions

**Cause 1: Directory doesn't exist**
```bash
# Solution: Create directory
mkdir -p ~/.claude/projects

# Or configure existing directory
# in graphiti.config.json
{
  "session_tracking": {
    "watch_directories": ["/path/to/existing/dir"]
  }
}
```

**Cause 2: Permission denied**
```bash
# Solution: Fix permissions
chmod -R u+r ~/.claude/projects  # Unix
# Windows: Right-click folder → Properties → Security → Edit
```

**Cause 3: Symbolic link issue**
```bash
# watchdog may not follow symlinks by default
# Solution: Use real path
realpath ~/.claude/projects

# Update config with real path
{
  "session_tracking": {
    "watch_directories": ["/home/user/.claude/projects"]  // Real path
  }
}
```

**Cause 4: File system type not supported**
```bash
# Check filesystem type
df -T ~/.claude  # Unix

# Some network filesystems (NFS, SMB) may not support inotify
# Solution: Copy files locally or increase poll interval
```

---

### 6. Cost Overruns

#### Symptom
OpenAI API costs higher than expected.

#### Diagnostic Steps

**Step 1: Check actual costs**
```bash
# Get token usage from logs
grep "Token usage" ~/.local/state/graphiti/logs/mcp-server.log | tail -20

# Calculate total tokens
grep "Token usage" ~/.local/state/graphiti/logs/mcp-server.log | \
  awk '{sum+=$3} END {print sum " total tokens"}'
```

**Step 2: Verify model**
```bash
# Check which model is being used
grep "LLM model" ~/.local/state/graphiti/logs/mcp-server.log | head -1

# Should be: gpt-4o-mini (cheap)
# Not: gpt-4 or gpt-4-turbo (expensive)
```

**Step 3: Check filtering effectiveness**
```bash
# Look for filter statistics
grep "filtered.*tokens" ~/.local/state/graphiti/logs/mcp-server.log

# Should show significant reduction: "93% filtered (10000 -> 700)"
```

#### Common Causes & Solutions

**Cause 1: Wrong model configured**
```json
// Solution: Use gpt-4o-mini
{
  "llm_model": "gpt-4o-mini",  // $0.15/1M input tokens
  // NOT "gpt-4": $30/1M input tokens (200x more expensive!)
}
```

**Cause 2: Filtering disabled**
```python
# Solution: Verify filter is being used
from graphiti_core.session_tracking import SessionFilter

filter = SessionFilter()
messages = [...]  # Your messages
filtered = filter.filter_messages(messages)

print(f"Original: {len(str(messages))} chars")
print(f"Filtered: {len(filtered)} chars")
print(f"Reduction: {(1 - len(filtered)/len(str(messages))) * 100:.1f}%")

# Should be 90%+ reduction
```

**Cause 3: Too many sessions**
```bash
# Solution: Opt-out for experimental work
graphiti-mcp session-tracking disable  # Before experiments
graphiti-mcp session-tracking enable   # After
```

**Cause 4: Very long sessions**
```bash
# Solution: Close sessions more frequently
# Either:
# 1. Reduce inactivity timeout
{
  "session_tracking": {
    "inactivity_timeout_minutes": 15  // Shorter timeout
  }
}

# 2. Manually close long sessions
graphiti-mcp stop  # Forces indexing of active sessions
graphiti-mcp start
```

---

### 7. Session Linking Broken

#### Symptom
Sequential sessions not linked, context discontinuity.

#### Diagnostic Steps

**Step 1: Check episode relationships**
```python
# query_relationships.py
from graphiti_core.graphiti import Graphiti

graphiti = Graphiti()
episodes = await graphiti.get_episodes(group_id="hostname__hash", limit=5)

for ep in episodes:
    # Check if episode has relationships
    facts = await graphiti.get_facts(source_node_uuid=ep.uuid)
    print(f"{ep.name}: {len(facts)} relationships")
```

**Step 2: Verify previous_episode_uuid**
```bash
# Look for linking logs
grep "previous_episode_uuid" ~/.local/state/graphiti/logs/mcp-server.log

# Should see: "Linking to previous episode: abc123..."
```

#### Common Causes & Solutions

**Cause 1: Group ID changes between sessions**
```python
# Solution: Ensure consistent group ID calculation
# Debug: Log group ID for each session
import logging
logger = logging.getLogger(__name__)
logger.info(f"Indexing session with group_id: {group_id}")
```

**Cause 2: Sessions indexed out of order**
```bash
# Solution: This is a known limitation
# Sessions must be indexed sequentially for linking

# Workaround: Link manually after indexing
await graphiti.create_relationship(
    source_uuid=prev_episode_uuid,
    target_uuid=new_episode_uuid,
    relationship_type="preceded_by"
)
```

**Cause 3: MCP server restart between sessions**
```bash
# Solution: Session state is lost on restart
# This is expected behavior - linking only works for continuous sessions

# Workaround: Use Graphiti's search to find related sessions
related = await graphiti.search(
    query="similar to session X",
    group_id="hostname__hash"
)
```

---

## Platform-Specific Issues

### Windows

**Issue: Path separators causing errors**
```python
# Solution: Use pathlib for platform-agnostic paths
from pathlib import Path

path = Path("C:\\Users\\Admin\\.claude\\projects")
# Automatically handles separators correctly
```

**Issue: File watching not working on network drives**
```bash
# Solution: Copy .claude directory to local drive
# Or increase poll interval
{
  "session_tracking": {
    "scan_interval_seconds": 10  // Increase for network drives
  }
}
```

### macOS

**Issue: Too many open files error**
```bash
# Solution: Increase file descriptor limit
ulimit -n 4096

# Make permanent (add to ~/.zshrc or ~/.bash_profile)
echo "ulimit -n 4096" >> ~/.zshrc
```

### Linux

**Issue: inotify watch limit exceeded**
```bash
# Error: "inotify watch limit reached"
# Solution: Increase limit
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### WSL (Windows Subsystem for Linux)

**Issue: Path resolution fails**
```python
# Solution: WSL paths need special handling
from graphiti_core.session_tracking import ClaudePathResolver

resolver = ClaudePathResolver()

# WSL path: /mnt/c/Users/Admin/project
# Normalizes to: /c/Users/Admin/project (consistent with Windows)
unix_path = resolver._to_unix_path("/mnt/c/Users/Admin/project")
print(unix_path)  # /c/Users/Admin/project
```

---

## Diagnostic Tools

### 1. Session Tracking Health Check

```python
# health_check.py
import asyncio
from graphiti_core.graphiti import Graphiti
from graphiti_core.session_tracking import *

async def health_check():
    print("=== Session Tracking Health Check ===\n")
    
    # Check 1: Graphiti connection
    try:
        graphiti = Graphiti()
        print("✓ Graphiti connected")
    except Exception as e:
        print(f"✗ Graphiti connection failed: {e}")
        return
    
    # Check 2: File watcher
    try:
        watcher = SessionFileWatcher(
            watch_directories=["~/.claude/projects"],
            on_file_created=lambda p: None,
            on_file_modified=lambda p: None,
            on_file_deleted=lambda p: None
        )
        watcher.start()
        print("✓ File watcher started")
        watcher.stop()
    except Exception as e:
        print(f"✗ File watcher failed: {e}")
    
    # Check 3: Session indexing
    try:
        indexer = SessionIndexer(graphiti)
        test_uuid = await indexer.index_session(
            session_id="health-check-test",
            filtered_content="Test session",
            group_id="health_check__test",
            session_number=1
        )
        print(f"✓ Session indexing works (test UUID: {test_uuid[:8]}...)")
        
        # Cleanup test episode
        await graphiti.delete_episode(test_uuid)
    except Exception as e:
        print(f"✗ Session indexing failed: {e}")
    
    # Check 4: Episodes exist
    try:
        episodes = await graphiti.get_episodes(limit=5)
        print(f"✓ Found {len(episodes)} recent episodes")
    except Exception as e:
        print(f"✗ Episode retrieval failed: {e}")
    
    print("\n=== Health Check Complete ===")

if __name__ == "__main__":
    asyncio.run(health_check())
```

### 2. Session Statistics

```python
# session_stats.py
import asyncio
from graphiti_core.graphiti import Graphiti
from datetime import datetime, timedelta

async def session_stats(group_id: str):
    graphiti = Graphiti()
    
    # Get all episodes for group
    episodes = await graphiti.get_episodes(group_id=group_id, limit=100)
    
    if not episodes:
        print(f"No episodes found for group: {group_id}")
        return
    
    # Calculate stats
    total = len(episodes)
    oldest = min(ep.created_at for ep in episodes)
    newest = max(ep.created_at for ep in episodes)
    
    print(f"=== Session Statistics for {group_id} ===")
    print(f"Total sessions: {total}")
    print(f"Date range: {oldest} to {newest}")
    print(f"Average per day: {total / max(1, (newest - oldest).days):.1f}")
    
    # Entity counts
    total_entities = sum(len(ep.entities) for ep in episodes)
    print(f"Total entities: {total_entities}")
    print(f"Avg entities per session: {total_entities / total:.1f}")

if __name__ == "__main__":
    group_id = input("Enter group ID (hostname__hash): ")
    asyncio.run(session_stats(group_id))
```

### 3. Token Usage Analyzer

```bash
# analyze_tokens.sh
#!/bin/bash

LOG_FILE="$HOME/.local/state/graphiti/logs/mcp-server.log"

echo "=== Token Usage Analysis ==="
echo

# Total tokens
total=$(grep "Token usage" "$LOG_FILE" | awk '{sum+=$3} END {print sum}')
echo "Total tokens: $total"

# Average per session
count=$(grep "Token usage" "$LOG_FILE" | wc -l)
avg=$((total / count))
echo "Average per session: $avg"

# Cost estimate (gpt-4o-mini: $0.15/1M input tokens)
cost=$(echo "scale=2; $total * 0.15 / 1000000" | bc)
echo "Estimated cost: \$$cost"

# Filtering effectiveness
echo
echo "Filtering effectiveness:"
grep "filtered" "$LOG_FILE" | tail -10
```

---

## Getting Help

### Information to Include in Bug Reports

When reporting issues, include:

1. **Configuration**:
```bash
cat graphiti.config.json | jq .session_tracking
```

2. **Environment**:
```bash
python --version
pip list | grep -E "(graphiti|watchdog|neo4j)"
uname -a  # Unix
ver  # Windows
```

3. **Logs** (last 50 lines):
```bash
tail -50 ~/.local/state/graphiti/logs/mcp-server.log
```

4. **Reproduction steps**:
- What you did (exact commands)
- What you expected
- What actually happened

### Support Channels

- **GitHub Issues**: https://github.com/getzep/graphiti/issues
- **Discord**: https://discord.com/invite/W8Kw6bsgXQ
- **Documentation**: 
  - User Guide: `docs/SESSION_TRACKING_USER_GUIDE.md`
  - Dev Guide: `docs/SESSION_TRACKING_DEV_GUIDE.md`

---

## FAQ

**Q: Why are my sessions taking 5+ minutes to index?**
A: Check OpenAI API rate limits. Use gpt-4o-mini model to reduce latency.

**Q: Can I disable tracking for specific projects?**
A: Not yet (planned for v0.5.0). Workaround: Disable globally when working on that project.

**Q: How do I delete all session data?**
A: Use `graphiti.clear_graph()` (nuclear option) or delete specific episodes with `graphiti.delete_episode(uuid)`.

**Q: Does session tracking work offline?**
A: No. Requires OpenAI API access for entity extraction. Sessions are queued until connection restored.

**Q: Can I use a different LLM (non-OpenAI)?**
A: Yes. Configure Graphiti to use Anthropic, Azure OpenAI, or other providers in `graphiti.config.json`.

**Q: What's the minimum Neo4j version?**
A: Neo4j 5.x required. Tested with 5.15.0+.

**Q: How do I backup session data?**
A: Use Neo4j's `neo4j-admin dump` command to backup database. Sessions are in the graph.

---

## Performance Tuning

### For High-Volume Environments

```json
// graphiti.config.json
{
  "session_tracking": {
    "enabled": true,
    "inactivity_timeout_minutes": 15,  // Close sessions faster
    "scan_interval_seconds": 5,  // Reduce CPU usage
    "watch_directories": [
      "~/.claude/projects/active"  // Limit scope
    ]
  },
  "llm_model": "gpt-4o-mini",  // Use cheapest model
  "batch_size": 10  // Process sessions in batches
}
```

### For Low-Resource Systems

```json
{
  "session_tracking": {
    "enabled": true,
    "inactivity_timeout_minutes": 60,  // Longer timeout
    "scan_interval_seconds": 10,  // Lower CPU usage
    "watch_directories": [
      "~/.claude/projects"
    ]
  }
}
```

---

This troubleshooting guide covers the most common issues. For more help, see the user guide and developer guide, or reach out on Discord!