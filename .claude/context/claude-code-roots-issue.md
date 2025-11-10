# Claude Code MCP Roots Capability Issue

**Status**: BLOCKING
**Category**: Infrastructure / MCP Integration
**Impact**: High - Prevents standardized filepath resolution for MCP tools
**Reported**: July 2024 (GitHub Issue #3315)
**Affects**: graphiti MCP server `filepath` parameter

---

## Problem Summary

Claude Code advertises support for the MCP `roots` capability during initialization but does not implement the `roots/list` method handler. This prevents MCP servers from discovering the client's working directory via the standard MCP protocol.

## Technical Details

### What Should Happen (MCP Specification)

1. **Client Initialization**: Client declares `roots` capability
   ```json
   {
     "capabilities": {
       "roots": {
         "listChanged": true
       }
     }
   }
   ```

2. **Server Request**: Server calls `roots/list` to discover client working directories
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "method": "roots/list"
   }
   ```

3. **Client Response**: Client returns list of root URIs
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "result": {
       "roots": [
         {
           "uri": "file:///home/user/projects/myproject",
           "name": "My Project"
         }
       ]
     }
   }
   ```

### What Actually Happens (Claude Code Bug)

1. Claude Code sends: `{"capabilities": {"roots": {}}}`
2. MCP server calls `roots/list`
3. **Request times out** after 5+ seconds
4. Error returned: `{"error": {"code": -32001, "message": "Request timeout"}}`

## Impact on Graphiti MCP Server

### Current Behavior (Broken)

When using the `filepath` parameter in `add_memory`:

```python
add_memory(
    name="Test Session",
    episode_body="...",
    filepath=".claude/handoff/snapshots/s001.md"
)
```

**Problem**: File is created relative to **MCP server's working directory** (`mcp_server/`), not the **client's working directory** (project root).

**Result**:
- Expected: `{project_root}/.claude/handoff/snapshots/s001.md`
- Actual: `{project_root}/mcp_server/.claude/handoff/snapshots/s001.md`

### Desired Behavior (Standard)

MCP servers should be able to:
1. Query client's working directory via `roots/list`
2. Resolve relative paths against client's root
3. Create files in client's expected locations

## Workarounds

### Current Workaround: Environment Variable (PWD)

Since Claude Code sets `PWD` environment variable, we can use it as a fallback:

```python
import os
from pathlib import Path

# Detect client working directory
CLIENT_ROOT = Path(os.getenv('PWD', os.getcwd()))

# Resolve relative paths against client root
if not path.is_absolute():
    output_path = CLIENT_ROOT / path
```

**Pros**:
- ✅ Works immediately
- ✅ Simple implementation
- ✅ Reliable with Claude Code

**Cons**:
- ⚠️ Not standard MCP protocol
- ⚠️ Environment variable dependency
- ⚠️ May not work with other MCP clients

### Alternative Workaround: Absolute Paths Only

Require users to provide absolute paths:

```python
add_memory(
    name="Test Session",
    episode_body="...",
    filepath="/absolute/path/to/.claude/handoff/snapshots/s001.md"
)
```

**Pros**:
- ✅ Always works correctly
- ✅ No client detection needed

**Cons**:
- ❌ Poor user experience (verbose, non-portable)
- ❌ Doesn't work with path variables like `{date}`
- ❌ Breaks cross-platform compatibility

## Status Update (November 2025)**Search Results**: Conducted comprehensive search for updates, fixes, or forks addressing this issue.**Findings**:- ❌ **Issue still OPEN** as of September 4, 2025- ❌ **No merged pull requests** fixing the core problem- ❌ **No official workaround** from Anthropic- ✅ **Community workarounds**: Users manually passing workspace folders in configuration- ⚠️ **Assigned to @ashwin-ant** but no timeline provided**Conclusion**: The roots capability bug remains unfixed in Claude Code. MCP servers must implement their own working directory detection using environment variables or require absolute paths.## References- **GitHub Issue**: https://github.com/anthropics/claude-code/issues/3315  - Title: "Claude Code advertises roots capability but doesn't implement roots/list"  - Status: **OPEN** (as of September 4, 2025 - latest comment)  - Assigned: @ashwin-ant  - Reporter: MCP server developers  - Labels: `area:mcp`, `bug`, `has repro`, `platform:macos`- **MCP Specification**: https://modelcontextprotocol.io/specification/client/roots  - Defines `roots/list` method  - Requires client implementation- **Python MCP SDK**: https://github.com/modelcontextprotocol/python-sdk  - Supports roots protocol on server side  - Cannot work if client doesn't respond## Recommended Action

1. **Short-term**: Implement `PWD` environment variable workaround in `mcp_server/graphiti_mcp_server.py`
2. **Document**: Add clear notes in `docs/MCP_TOOLS.md` about relative path resolution
3. **Monitor**: Track Claude Code issue #3315 for updates
4. **Future**: When Claude Code implements `roots/list`, add it as primary detection method with `PWD` fallback

## Implementation Status

- [x] Issue documented (2025-11-09)
- [x] Workaround implemented (PWD-based resolution with mcp_server fallback)
- [x] Tests completed (s006-s009, all passing)
- [ ] Documentation updated (MCP_TOOLS.md) - pending
- [ ] Unit tests added - pending
- [ ] Monitoring GitHub issue for updates (monthly)

### Implementation Details

**Files Modified:**
- `mcp_server/export_helpers.py` - Added `_resolve_absolute_path()` function
- `mcp_server/graphiti_mcp_server.py` - Added CLIENT_ROOT detection and updated add_memory()

**Detection Logic:**
```python
_detected_root = os.getenv("PWD", os.getcwd())
if Path(_detected_root).name == "mcp_server":
    CLIENT_ROOT = str(Path(_detected_root).parent)
else:
    CLIENT_ROOT = _detected_root
```

**Test Results:**
- ✅ s008: Files now created in project root (not mcp_server/ subdirectory)
- ✅ s009: Path variables ({date}, {time}) still work correctly
- ✅ Relative paths displayed in success messages for better UX

---

**Last Updated**: 2025-11-10
**Next Review**: Check GitHub issue status monthly
