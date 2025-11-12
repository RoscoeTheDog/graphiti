# Bug Report: Group ID Validation - Overly Restrictive Character Set

**Reporter**: Claude Code Agent (User: RoscoeTheDog)
**Date**: 2025-11-11
**Component**: Graphiti Core - `group_id` validation
**Severity**: MEDIUM (silent data loss, workaround available)
**Status**: OPEN
**Type**: Enhancement Request

---

## Summary

The `group_id` parameter validation restricts characters to `[a-zA-Z0-9_-]` only, rejecting common delimiter characters like colon (`:`), pipe (`|`), and others. This causes **silent failures** when using natural composite identifiers (e.g., `hostname:workspace_hash`).

**Proposed Solution**: Implement string encoding/decoding to allow any characters in group_ids while maintaining backend compatibility.

---

## Environment

- **Component**: Graphiti Core (graphiti_core)
- **Validation Regex**: `^[a-zA-Z0-9_-]+$` (assumed from observed behavior)
- **Use Case**: Claude Code runtime - project isolation via `GRAPHITI_GROUP_ID`
- **Impact**: Episodes not persisting (silent failure, no error thrown)

---

## Expected Behavior

**Ideal UX**: Users should be able to use any valid string as a `group_id`, including natural delimiters:
- ✅ `hostname:workspace_hash` (colon separator)
- ✅ `user|project` (pipe separator)
- ✅ `team::project::env` (double colon)
- ✅ `user@domain:project` (email-like)

**Backend Handling**:
1. MCP server receives `group_id` with special characters
2. MCP server encodes to backend-safe format (e.g., URL encoding, base64, custom substitution)
3. Backend stores encoded version
4. MCP server decodes when returning results to client

**User Experience**: Transparent - users never see encoded version

---

## Actual Behavior

**Symptom**: Episodes silently fail to persist when `group_id` contains restricted characters.

**Example**:
```python
# Client call
g:add_memory(
    name="test-episode",
    episode_body="Test content",
    group_id="DESKTOP-9SIHNJI:82c00f09"  # ❌ Colon not allowed
)

# Result
# - No error thrown
# - Episode appears to succeed
# - Data NOT persisted (silent failure)
# - No validation error message
```

**Discovery Process**:
1. User created episodes with `group_id="hostname:hash"` format
2. MCP tool returned success messages
3. Querying with `g:search_memory_nodes` returned 0 results
4. User tested with valid characters: `group_id="hostname__hash"` → Success
5. Confirmed colon (`:`) was the issue

**Actual Validation**: Backend rejects `group_id` with characters outside `[a-zA-Z0-9_-]`

---

## Root Cause Analysis

### Current Implementation (Inferred)

**Validation Location**: Likely in Graphiti Core validation layer or Neo4j query builder

**Rationale for Restriction** (likely):
1. **Database Safety**: Prevent SQL/Cypher injection
2. **Filesystem Safety**: group_ids may be used in file paths
3. **URL Safety**: group_ids may be exposed in APIs
4. **Query Safety**: Prevent special character issues in graph queries

**Why This Is Overly Restrictive**:
- Modern databases support parameterized queries (injection-safe)
- URL encoding exists for API exposure
- Filesystem encoding exists for file paths
- Users sacrifice UX for backend implementation details

---

## Proposed Solutions

### Option 1: URL Encoding (Recommended)

**Concept**: Transparently encode/decode `group_id` using URL encoding.

**Implementation**:
```python
import urllib.parse

class GroupIDCodec:
    """Encode/decode group_ids for backend storage"""

    @staticmethod
    def encode(group_id: str) -> str:
        """Encode group_id for backend storage"""
        # URL encode, but preserve - and _ for readability
        return urllib.parse.quote(group_id, safe='_-')

    @staticmethod
    def decode(encoded: str) -> str:
        """Decode group_id from backend storage"""
        return urllib.parse.unquote(encoded)

# Example
original = "DESKTOP-9SIHNJI:82c00f09"
encoded = GroupIDCodec.encode(original)  # "DESKTOP-9SIHNJI%3A82c00f09"
decoded = GroupIDCodec.decode(encoded)   # "DESKTOP-9SIHNJI:82c00f09"
```

**Pros**:
- ✅ Standard (RFC 3986)
- ✅ All languages have URL encode/decode
- ✅ Safe for URLs, filesystems, databases
- ✅ Readable (mostly unchanged for alphanumeric)
- ✅ Reversible (lossless)

**Cons**:
- ⚠️ Stored format differs from user input (visible in backend queries)
- ⚠️ Backend database shows `%3A` instead of `:`

---

### Option 2: Custom Character Substitution

**Concept**: Use a bijective mapping for common special characters.

**Implementation**:
```python
class GroupIDCodec:
    """Custom encoding for readability in backend"""

    # Substitution map (bijective)
    ENCODE_MAP = {
        ':': '__COLON__',
        '|': '__PIPE__',
        '@': '__AT__',
        '/': '__SLASH__',
        '\\': '__BSLASH__',
        ' ': '__SPACE__',
        '.': '__DOT__',
    }

    DECODE_MAP = {v: k for k, v in ENCODE_MAP.items()}

    @staticmethod
    def encode(group_id: str) -> str:
        """Encode group_id using substitution"""
        result = group_id
        for char, sub in GroupIDCodec.ENCODE_MAP.items():
            result = result.replace(char, sub)
        return result

    @staticmethod
    def decode(encoded: str) -> str:
        """Decode group_id using reverse substitution"""
        result = encoded
        for sub, char in GroupIDCodec.DECODE_MAP.items():
            result = result.replace(sub, char)
        return result

# Example
original = "DESKTOP-9SIHNJI:82c00f09"
encoded = GroupIDCodec.encode(original)  # "DESKTOP-9SIHNJI__COLON__82c00f09"
decoded = GroupIDCodec.decode(encoded)   # "DESKTOP-9SIHNJI:82c00f09"
```

**Pros**:
- ✅ Readable in backend (semantic substitution)
- ✅ No percent encoding clutter
- ✅ Safe for all backends
- ✅ Custom vocabulary can be extended

**Cons**:
- ⚠️ Non-standard (custom implementation)
- ⚠️ Longer strings (e.g., `:` → `__COLON__`)
- ⚠️ Risk of collision if user uses `__COLON__` literally

---

### Option 3: Base64 Encoding

**Concept**: Base64 encode entire `group_id`.

**Implementation**:
```python
import base64

class GroupIDCodec:
    """Base64 encoding for maximum safety"""

    @staticmethod
    def encode(group_id: str) -> str:
        """Base64 encode group_id"""
        return base64.urlsafe_b64encode(group_id.encode()).decode()

    @staticmethod
    def decode(encoded: str) -> str:
        """Base64 decode group_id"""
        return base64.urlsafe_b64decode(encoded.encode()).decode()

# Example
original = "DESKTOP-9SIHNJI:82c00f09"
encoded = GroupIDCodec.encode(original)  # "REVTS1RPUC05U0lITkpJOjgyYzAwZjA5"
decoded = GroupIDCodec.decode(encoded)   # "DESKTOP-9SIHNJI:82c00f09"
```

**Pros**:
- ✅ Maximally safe (only alphanumeric + = padding)
- ✅ Standard encoding (RFC 4648)
- ✅ Fixed character set `[A-Za-z0-9_-]` (URL-safe variant)
- ✅ No collision risk

**Cons**:
- ❌ Completely unreadable in backend
- ❌ Hard to debug (can't visually identify group_ids)
- ❌ Longer strings (~1.33x original length)

---

### Option 4: Relax Validation (NOT Recommended)

**Concept**: Remove character restrictions, trust parameterized queries.

**Pros**:
- ✅ Simple (no encoding needed)
- ✅ User input matches storage

**Cons**:
- ❌ Risk of injection attacks if not using parameterized queries
- ❌ Filesystem issues if group_id used in paths
- ❌ URL issues if group_id exposed in APIs
- ❌ Not future-proof (assumes all backends safe)

---

## Recommended Approach

**Primary**: **Option 1 (URL Encoding)**
- Standard, universally supported
- Balances readability and safety
- Works with any string input

**Fallback**: **Option 2 (Custom Substitution)**
- Better readability in backend logs/queries
- Good for limited set of special characters

**Migration Path**:
1. Implement encoding in MCP server layer (transparent to clients)
2. Add `legacy_mode` flag for backward compatibility
3. Document encoding scheme in API docs
4. Provide utility functions for backend queries (if needed)

---

## Impact Assessment

### Current Impact (Without Fix)

**User Experience**:
- ❌ Silent failures (no error messages)
- ❌ Confusion when data doesn't persist
- ❌ Trial-and-error to discover valid characters
- ❌ Forced to use unnatural delimiters (e.g., `__` instead of `:`)

**Workarounds**:
- ✅ Use only `[a-zA-Z0-9_-]` characters (documented)
- ✅ Client-side encoding before calling Graphiti (not ideal)
- ✅ Choose alternate delimiters (e.g., `__`, `---`)

**Data Loss**:
- ⚠️ Episodes created with invalid `group_id` are **silently lost**
- ⚠️ No error message to indicate validation failure

### Expected Impact (With Fix)

**User Experience**:
- ✅ Any string works as `group_id` (no restrictions)
- ✅ Natural delimiters (`:`, `|`, `/`) work as expected
- ✅ No silent failures (encoding always succeeds)
- ✅ Error messages if encoding fails (rare)

**Backend**:
- ✅ Encoded `group_id` stored in database (safe)
- ✅ MCP server handles encoding/decoding (transparent)
- ✅ Backward compatible (can decode legacy values)

---

## Reproduction Steps

### Reproduce Silent Failure

**Test Case 1: Invalid Character (Colon)**
```python
# Step 1: Create episode with colon in group_id
g:add_memory(
    name="test-colon",
    episode_body="Test with colon",
    group_id="hostname:workspace"  # ❌ Contains colon
)
# Expected: Error or validation warning
# Actual: Success message (but data not persisted)

# Step 2: Query episodes
g:search_memory_nodes("test", group_ids=["hostname:workspace"])
# Expected: Returns episode if validation passed
# Actual: Returns 0 results (episode silently lost)
```

**Test Case 2: Valid Character (Underscore)**
```python
# Step 1: Create episode with underscore in group_id
g:add_memory(
    name="test-underscore",
    episode_body="Test with underscore",
    group_id="hostname__workspace"  # ✅ Double underscore
)
# Expected: Success
# Actual: Success (data persisted correctly)

# Step 2: Query episodes
g:search_memory_nodes("test", group_ids=["hostname__workspace"])
# Expected: Returns episode
# Actual: Returns episode ✅
```

---

## Validation Error Improvement

### Current Behavior (Inferred)

```python
# Pseudocode of current validation
def validate_group_id(group_id: str) -> bool:
    pattern = r'^[a-zA-Z0-9_-]+$'
    if not re.match(pattern, group_id):
        # Silent failure: No error, no warning, just fails
        return False
    return True
```

### Proposed Behavior

```python
# Pseudocode of improved validation
def validate_and_encode_group_id(group_id: str) -> str:
    """Validate and encode group_id for backend storage"""

    # Option 1: Encode transparently (no validation needed)
    encoded = urllib.parse.quote(group_id, safe='_-')
    return encoded

    # OR Option 2: Validate and throw descriptive error
    pattern = r'^[a-zA-Z0-9_-]+$'
    if not re.match(pattern, group_id):
        raise ValueError(
            f"Invalid group_id: '{group_id}' contains restricted characters. "
            f"Allowed: [a-zA-Z0-9_-]. Found: {set(group_id) - set(string.ascii_letters + string.digits + '_-')}"
        )
    return group_id
```

---

## User Workaround (Current)

**Discovered Solution** (2025-11-11):
- Change delimiter from `:` to `__` (double underscore)
- Example: `DESKTOP-9SIHNJI:82c00f09` → `DESKTOP-9SIHNJI__82c00f09`

**Rationale for `__`**:
- ✅ Allowed by validation regex `[a-zA-Z0-9_-]`
- ✅ Clear visual separation (more distinctive than single `-` or `_`)
- ✅ Programming convention (Python dunder methods)
- ✅ Low collision risk (hostnames rarely contain `__`, hashes never do)

**Implementation** (Claude Code runtime):
```bash
# v3.8.2+ (fixed)
HOSTNAME="$(hostname)"
PWD_HASH="$(echo -n "$(pwd)" | sha256sum | cut -c1-8)"
GRAPHITI_GROUP_ID="${HOSTNAME}__${PWD_HASH}"  # Double underscore
```

---

## Testing Checklist

**Pre-Fix Testing** (Validate Current Behavior):
- [ ] Confirm `:` in `group_id` causes silent failure
- [ ] Confirm `|` in `group_id` causes silent failure
- [ ] Confirm `__` in `group_id` works correctly
- [ ] Document exact validation regex used

**Post-Fix Testing** (Validate Encoding Works):
- [ ] Test `group_id` with `:` → Episodes persist correctly
- [ ] Test `group_id` with `|` → Episodes persist correctly
- [ ] Test `group_id` with spaces → Episodes persist correctly
- [ ] Test `group_id` with `/` → Episodes persist correctly
- [ ] Test round-trip: encode → store → decode → verify match
- [ ] Test backward compatibility with existing non-encoded group_ids
- [ ] Test error handling for invalid encoding (edge cases)

---

## Related Issues

- **BUG_REPORT-filepath-handling-windows.md**: Similar encoding issue (Windows path handling)
- **Graphiti Issue #XXX**: (Link to upstream issue if reported)

---

## Implementation Locations

**Where to Implement Encoding/Decoding**:

1. **MCP Server Layer** (Recommended):
   - `mcp_server/` directory
   - Encode `group_id` before passing to Graphiti Core
   - Decode `group_id` when returning results

2. **Graphiti Core Layer** (Alternative):
   - `graphiti_core/` validation module
   - Encode at data persistence layer
   - Decode at query layer

**Files to Modify** (Estimated):
- `mcp_server/server.py` (or equivalent) - Add encoding/decoding wrapper
- `graphiti_core/models.py` (or equivalent) - Update validation logic
- `tests/test_group_id.py` - Add test cases for special characters

---

## Documentation Updates Needed

**If Implemented**:
1. **API Documentation**: Document that `group_id` accepts any string (encoding is transparent)
2. **Migration Guide**: Explain behavior change (if validation previously threw errors)
3. **Backend Queries**: Document encoded format for direct database access
4. **Changelog**: Note fix in release notes

**Current Workaround Documentation** (Interim):
1. **README.md**: Document allowed characters `[a-zA-Z0-9_-]` for `group_id`
2. **Error Messages**: Add validation error with clear allowed character set
3. **Examples**: Show valid `group_id` formats

---

## Questions for Maintainers

1. **Is the validation regex documented anywhere?** (Assumed `^[a-zA-Z0-9_-]+$` from testing)
2. **Why is the character set restricted?** (Database safety, filesystem, URLs?)
3. **Are group_ids used in file paths or URLs?** (Would affect encoding choice)
4. **Is there a preference between URL encoding vs. custom substitution?**
5. **Should encoding be transparent or explicit?** (User-facing API decision)
6. **Are there existing group_ids in production that would need migration?**

---

## Priority Justification

**Severity**: MEDIUM (not HIGH)
- ❌ Silent data loss (users don't know episodes aren't saved)
- ✅ Workaround available (use `__` delimiter)
- ✅ Not a security issue (validation is working, just too strict)

**Priority**: MEDIUM-HIGH (UX improvement + data integrity)
- Silent failures are confusing and frustrating
- Forced to use unnatural identifiers (e.g., `hostname__workspace` instead of `hostname:workspace`)
- Easy fix with high user impact (encoding solves problem completely)

---

## References

- **URL Encoding (RFC 3986)**: https://datatracker.ietf.org/doc/html/rfc3986
- **Base64 (RFC 4648)**: https://datatracker.ietf.org/doc/html/rfc4648
- **Neo4j Parameterized Queries**: https://neo4j.com/docs/cypher-manual/current/syntax/parameters/
- **Claude Code Runtime**: https://github.com/RoscoeTheDog/claude-code-tooling (private)

---

**Submitted By**: RoscoeTheDog (via Claude Code Agent)
**Contact**: (Add GitHub handle or email if maintainers need clarification)
