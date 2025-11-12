# Bug Report: Filepath Handling on Windows (add_memory)

**Reporter**: Claude Code Agent
**Date**: 2025-11-11
**Component**: MCP Server - `add_memory` tool
**Severity**: HIGH (breaks dual-storage feature)
**Status**: RESOLVED (2025-11-11)

---

## Summary

The `mcp__graphiti-memory__add_memory` tool's `filepath` parameter exhibits incorrect path handling on Windows, resulting in doubled path prefixes that prevent file creation.

---

## Environment

- **OS**: Windows 10 (MSYS_NT-10.0-26100)
- **Shell**: Git Bash (MSYS2)
- **Graphiti MCP Server**: graphiti-memory (version unknown)
- **Python**: (version unknown)
- **Use Case**: Claude Code agent session handoff dual-storage

---

## Expected Behavior

When calling `add_memory` with `filepath` parameter:
1. Episode should be stored in Graphiti database
2. File should be written to the specified filepath
3. Filepath should be normalized for the current platform

**Expected filepath**: `/c/Users/Admin/Documents/GitHub/claude-code-tooling/.claude/handoff/s004-v3.7.5-deployment-handoff-testing.md`
**Expected file location**: `C:\Users\Admin\Documents\GitHub\claude-code-tooling\.claude\handoff\s004-v3.7.5-deployment-handoff-testing.md`

---

## Actual Behavior

**Graphiti Response**:
```
Episode 'Session 004: v3.7.5 Deployment and Handoff Testing' queued successfully
Saved to C:\c\Users\Admin\Documents\GitHub\claude-code-tooling\.claude\handoff\s004-v3.7.5-deployment-handoff-testing.md
```

**Result**:
- ✅ Episode stored in Graphiti database successfully
- ❌ File NOT created at expected location
- ❌ Path doubled: `C:\c\Users\...` (invalid Windows path)

**Observed Issues**:
1. Unix-style path `/c/...` converted to `C:\c\...` (drive letter prepended instead of replaced)
2. File creation silently fails (no error reported)
3. Dual-storage feature broken (database exists, file missing)

---

## Reproduction Steps

**Test Code**:
```python
# Via MCP tool call
mcp__graphiti-memory__add_memory(
    name="Session 004: v3.7.5 Deployment and Handoff Testing",
    episode_body="<markdown content>",
    group_id="claude-code-tooling",
    source="text",
    source_description="handoff session summary",
    filepath="/c/Users/Admin/Documents/GitHub/claude-code-tooling/.claude/handoff/s004-v3.7.5-deployment-handoff-testing.md"
)
```

**Expected File**: `C:\Users\Admin\Documents\GitHub\claude-code-tooling\.claude\handoff\s004-v3.7.5-deployment-handoff-testing.md`
**Actual Result**: File not created, invalid path `C:\c\Users\...` reported

---

## Root Cause Analysis

**Hypothesis 1: Path Normalization Bug**
- Server receives Unix-style path: `/c/Users/...`
- Server attempts Windows normalization: prepends `C:` → `C:\c\Users\...`
- Should instead: convert `/c/` to `C:\` → `C:\Users\...`

**Hypothesis 2: MSYS Path Translation Issue**
- Git Bash uses MSYS paths (`/c/...`)
- Python's `pathlib` or `os.path` may not handle MSYS paths correctly
- Missing path translation layer for MSYS environments

**Hypothesis 3: Silent Failure**
- File creation fails (invalid path)
- Exception caught but not reported to MCP client
- Only success message returned: "Saved to <invalid-path>"

---

## Impact

**Severity Justification**:
- **HIGH**: Breaks critical dual-storage feature for Windows users
- File-based queries fail (filesystem-first approach unusable)
- Session continuity broken (handoffs stored only in database)
- Silent failure makes debugging difficult

**Affected Users**:
- Windows users with Git Bash/MSYS2
- Users relying on `filepath` parameter for dual-storage
- Claude Code agents using handoff workflows

---

## Workaround

**Manual File Creation**:
```bash
# Agent must manually create file after add_memory call
cat > .claude/handoff/s004-v3.7.5-deployment-handoff-testing.md <<'EOF'
<episode_body content>
EOF
```

**Alternative Path Format** (untested):
```python
# Try Windows-style path directly
filepath="C:\\Users\\Admin\\Documents\\GitHub\\claude-code-tooling\\.claude\\handoff\\s004-test.md"

# Or try raw string
filepath=r"C:\Users\Admin\Documents\GitHub\claude-code-tooling\.claude\handoff\s004-test.md"
```

---

## Recommended Fixes

**Short-term** (MCP Server):
1. Add MSYS path detection: `/c/...` → `C:\...` (regex: `^/([a-z])/` → `\1:\\`)
2. Use `pathlib.Path().resolve()` for platform-agnostic normalization
3. Report file creation errors to MCP client (don't silently fail)
4. Add filepath validation before attempting file write

**Long-term** (MCP Protocol):
1. Document expected filepath format in MCP server spec
2. Recommend clients use platform-agnostic paths (Python `Path.as_posix()`)
3. Add filepath parameter schema validation

**Example Fix** (Python):
```python
import re
from pathlib import Path

def normalize_filepath(filepath: str) -> Path:
    """Normalize filepath for current platform, handling MSYS paths."""
    # Detect MSYS path: /c/Users/... -> C:\Users\...
    if re.match(r'^/([a-z])/', filepath):
        filepath = re.sub(r'^/([a-z])/', r'\1:/', filepath)

    # Convert to Path and resolve
    return Path(filepath).resolve()

# Usage
filepath = normalize_filepath("/c/Users/Admin/Documents/test.md")
# Returns: WindowsPath('C:/Users/Admin/Documents/test.md')
```

---

## Testing Recommendations

**Test Matrix**:
| Environment | Input Path | Expected Output | Status |
|-------------|------------|-----------------|--------|
| Windows Git Bash | `/c/Users/test.md` | `C:\Users\test.md` | FAIL |
| Windows PowerShell | `C:\Users\test.md` | `C:\Users\test.md` | UNKNOWN |
| macOS/Linux | `/home/user/test.md` | `/home/user/test.md` | UNKNOWN |
| Windows WSL | `/mnt/c/Users/test.md` | `C:\Users\test.md` | UNKNOWN |

**Suggested Tests**:
1. Test all path formats in test matrix
2. Verify file creation success/failure
3. Verify error reporting to MCP client
4. Test path with spaces: `/c/Program Files/test.md`
5. Test relative paths: `./relative/test.md`
6. Test network paths: `//server/share/test.md`

---

## Additional Context

**Related Issues**:
- This bug blocks production deployment of claude-runtime v3.7.5-experimental
- Workaround: Manual file creation after `add_memory` call
- Impact: ~500 token overhead per session due to manual file handling

**Related Files**:
- `.claude/handoff/s004-v3.7.5-deployment-handoff-testing.md` (manually created)
- `claude-runtime/v3.7.5-experimental/CLAUDE.md` (HANDOFF delegation section)
- `claude-commands/context/HANDOFF.md` (dual-storage workflow)

**Session Context**:
- Testing handoff delegation workflow for v3.7.5 deployment
- Discovered during Session 004 handoff creation
- Graphiti storage succeeded, file creation failed

---

## Contact

**Reporter**: Claude Code Agent (via user: RoscoeTheDog)
**Repository**: https://github.com/RoscoeTheDog/graphiti
**Issue Type**: Bug Report
**Priority**: HIGH

---

## Appendix: Full Tool Call

**Tool**: `mcp__graphiti-memory__add_memory`

**Parameters**:
```json
{
  "name": "Session 004: v3.7.5 Deployment and Handoff Testing",
  "episode_body": "# Session 004: v3.7.5 Deployment and Handoff Testing\n\n**Status**: ACTIVE\n**Created**: 2025-11-11 16:52\n**Objective**: Deploy v3.7.5-experimental and test handoff delegation workflow\n\n---\n\n## Completed\n\n- ✅ Deployed v3.7.5-experimental CLAUDE.md to production (~/.claude/)\n- ✅ Verified handoff delegation pattern in place (lines 544-560)\n- ✅ Confirmed context/HANDOFF command deployed (~/.claude/commands/context/)\n- ✅ Testing handoff delegation workflow (in progress)\n\n---\n\n## Blocked\n\nNone\n\n---\n\n## Next Steps\n\n- Complete handoff workflow test with dual-storage verification\n- Verify Graphiti storage with proper group_id\n- Review v3.7.6 proposal for machine-tagged group IDs\n- Test filesystem-first query patterns\n- Validate session continuity across handoffs\n\n---\n\n## Context\n\n**Files Modified/Created**:\n- ~/.claude/CLAUDE.md (v3.7.5-experimental deployed)\n- ~/.claude/commands/context/HANDOFF.md (pre-deployed)\n- .claude/handoff/s004-v3.7.5-deployment-handoff-testing.md (this file)\n\n**Documentation Referenced**:\n- claude-runtime/v3.7.5-experimental/CLAUDE.md (HANDOFF delegation section)\n- claude-commands/context/HANDOFF.md (dual-storage workflow)\n- .claude/implementation/AUDIT-v3.7.5-implementation-graphiti-recommendations.md\n\n**Session Context**:\n- Previous Session: s003-v3.7.5-audit-graphiti-architecture (COMPLETED)\n- Current Branch: sprint/v1.0-experimental/git-security-branch-dev-private-commands\n- Token Usage: ~72k/200k (36%)\n\n---\n\n**Session Duration**: ~15 minutes\n**Token Usage**: 72310/200000 (36%)",
  "group_id": "claude-code-tooling",
  "source": "text",
  "source_description": "handoff session summary",
  "filepath": "/c/Users/Admin/Documents/GitHub/claude-code-tooling/.claude/handoff/s004-v3.7.5-deployment-handoff-testing.md"
}
```

**Response**:
```
Episode 'Session 004: v3.7.5 Deployment and Handoff Testing' queued successfully
Saved to C:\c\Users\Admin\Documents\GitHub\claude-code-tooling\.claude\handoff\s004-v3.7.5-deployment-handoff-testing.md
```

**Verification**:
```bash
# File check
$ ls -la .claude/handoff/s004-v3.7.5-deployment-handoff-testing.md
ls: cannot access '.claude/handoff/s004-v3.7.5-deployment-handoff-testing.md': No such file or directory

# Graphiti check (successful)
$ mcp__graphiti-memory__search_memory_nodes(query="Session 004", group_ids=["claude-code-tooling"])
# Returns: Node found with summary (Graphiti storage SUCCESS)
```

**Conclusion**: File creation failed due to invalid path `C:\c\Users\...`, but Graphiti storage succeeded.

---

## Resolution

**Fixed**: 2025-11-11
**Commits**: See git log for changes to `mcp_server/export_helpers.py` and `mcp_server/graphiti_mcp_server.py`

### Implementation

**Changes Made**:

1. **Added `_normalize_msys_path()` function** (`export_helpers.py:161-201`)
   - Detects MSYS paths (`/c/Users/...`) and converts to Windows format (`C:/Users/...`)
   - Detects WSL paths (`/mnt/c/Users/...`) and converts to Windows format (`C:/Users/...`)
   - Handles all drive letters (a-z)
   - Leaves Unix and Windows paths unchanged

2. **Updated `_resolve_absolute_path()` function** (`export_helpers.py:114-158`)
   - Normalizes filepath BEFORE creating Path object
   - Normalizes client_root as well to handle MSYS PWD environment variable
   - Prevents Path.is_absolute() from incorrectly treating MSYS paths as absolute

3. **Normalized CLIENT_ROOT** (`graphiti_mcp_server.py:887-889`)
   - Added normalization of PWD environment variable
   - Ensures CLIENT_ROOT is in Windows format, not MSYS format
   - Fixes display path calculation

4. **Added error handling** (`graphiti_mcp_server.py:1176-1215`)
   - Wrapped file export code in try-except block
   - Reports file creation failures to MCP client
   - Logs errors for debugging
   - Episodes still succeed even if file export fails

### Testing

**Test Results**:
```
PASS /c/Users/Admin/test.md -> C:/Users/Admin/test.md
PASS /mnt/c/Users/Admin/test.md -> C:/Users/Admin/test.md
PASS C:/Users/Admin/test.md -> C:/Users/Admin/test.md
PASS ./relative/path.md -> ./relative/path.md
PASS /home/user/test.md -> /home/user/test.md
PASS /d/Projects/test.py -> D:/Projects/test.py
```

**Integration Test**:
- Created test episode with relative path: `.claude/test/filepath-fix-test.md`
- File successfully created at `C:\Users\Admin\Documents\GitHub\graphiti\.claude\test\filepath-fix-test.md`
- Verified file contents match episode_body

### Files Modified

1. `mcp_server/export_helpers.py`
   - Added `_normalize_msys_path()` function
   - Updated `_resolve_absolute_path()` to use normalization

2. `mcp_server/graphiti_mcp_server.py`
   - Added import for `_normalize_msys_path`
   - Normalized `CLIENT_ROOT` initialization
   - Added error handling for file export

### Verification

To verify the fix works:

```python
# Test with relative path
mcp__graphiti-memory__add_memory(
    name="Test",
    episode_body="Content",
    filepath=".claude/test.md"
)

# Test with MSYS absolute path
mcp__graphiti-memory__add_memory(
    name="Test",
    episode_body="Content",
    filepath="/c/Users/Admin/Documents/test.md"
)

# Both should successfully create files at correct locations
```

### Notes

- **Backward Compatible**: Existing code using Windows or Unix paths continues to work
- **Cross-Platform**: Also handles WSL paths (`/mnt/c/...`)
- **Error Reporting**: File creation failures now reported to client instead of silent failure
- **Production Ready**: All tests passing, no breaking changes

### Related Documentation

- Updated `docs/MCP_TOOLS.md` with path resolution behavior
- See `.claude/context/claude-code-roots-issue.md` for background on roots capability bug
