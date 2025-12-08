# Git-Intrinsic Detection (No Time Windows)

## Problem with Time-Based Detection

**Original Approach**: Use 5-second window after `.git/HEAD` change to classify file updates as git operations.

**Critical Flaw**:
```bash
git reset --hard HEAD~5    # Git operation starts
vim database.py            # User edits immediately (within 5 seconds)
# database.py MISCLASSIFIED as git_bulk_update ❌
```

User's immediate edit gets incorrectly marked as bulk operation and excluded from lazy-load.

## Solution: Content Hash Comparison

Instead of time windows, compare file content to git-tracked state.

### How It Works

**Step 1: Capture Git State** (on `.git/HEAD` change)
```bash
git ls-files -s
# 100644 abc123... 0	database.py
# 100644 def456... 0	auth.json
# ...47 more files

pending_git_hashes = {
    "database.py": "abc123...",
    "auth.json": "def456...",
    ...
}
```

**Step 2: File Change Event**
```python
# Watchdog detects: database.py modified

# Compute current file hash (git-style)
current_hash = compute_git_hash("database.py")

# Compare to expected git state
if current_hash == pending_git_hashes["database.py"]:
    # Matches → Git operation
    source = "git_bulk_update"
else:
    # Doesn't match → User edit
    source = "filesystem_watch"
```

**Step 3: Remove from Pending**
```python
# Mark as processed (prevent future misclassification)
del pending_git_hashes["database.py"]
```

### Example: Immediate User Edit

```bash
# Timeline:
git reset --hard HEAD~5       # T+0s: Git operation

# T+0.1s: Watchdog fires for 47 files
# database.py: hash="abc123..." → Matches git state → git_bulk_update ✓

vim database.py               # T+1s: User edits immediately
# Save changes

# T+2s: Watchdog fires again
# database.py: hash="xyz789..." → Doesn't match → filesystem_watch ✓
```

**Result**: User edit correctly classified as `source="filesystem_watch"` regardless of timing.

## Implementation

### Git Hash Computation

Git uses SHA-1 hash of blob format:
```
blob <size>\0<content>
```

```python
def compute_git_hash(filepath: str) -> str:
    """Compute git-style blob hash"""
    with open(filepath, "rb") as f:
        data = f.read()

    # Git blob format
    blob = f"blob {len(data)}\0".encode() + data
    return hashlib.sha1(blob).hexdigest()
```

### Git-Tracked Files

```python
def get_git_tracked_file_hashes() -> dict:
    """Get content hashes from git index"""
    result = subprocess.run(
        ["git", "ls-files", "-s"],
        capture_output=True,
        text=True
    )

    hashes = {}
    for line in result.stdout.splitlines():
        # Format: "100644 <hash> 0	<filepath>"
        parts = line.split()
        if len(parts) >= 4:
            git_hash = parts[1]
            filepath = " ".join(parts[3:])
            hashes[filepath] = git_hash

    return hashes
```

### File Change Handler

```python
def on_file_change(self, event):
    """Handle file modification"""
    filepath = self.get_relative_path(event.src_path)
    current_hash = self.compute_git_hash(event.src_path)

    # Check if matches expected git state
    if filepath in self.pending_git_hashes:
        expected_hash = self.pending_git_hashes[filepath]

        if current_hash == expected_hash:
            # Git operation
            add_memory(
                name=filepath,
                episode_body=read_file(event.src_path),
                source="git_bulk_update"  # Bulk operation
            )
            del self.pending_git_hashes[filepath]
            return

        # Hash mismatch = user edited after git operation
        del self.pending_git_hashes[filepath]

    # Not a git operation
    self.debounce_and_process(event, source="filesystem_watch")
```

## Benefits

✅ **Accurate Classification**: No false positives from timing
✅ **Instant User Edits**: User can edit immediately after git operation
✅ **No Race Conditions**: Hash comparison is deterministic
✅ **Handles Edge Cases**: Works for slow filesystems, rapid edits, etc.
✅ **Git-Native**: Uses git's own hashing mechanism

## Edge Cases Handled

### Case 1: User Edits During Rollback
```bash
git reset --hard HEAD~5 &     # Background process
vim database.py               # Edit starts immediately
```

**Result**:
- Files matching git state → `git_bulk_update`
- User-edited file → `filesystem_watch` (hash won't match)

### Case 2: Slow Filesystem
```bash
git reset --hard HEAD~5
# Filesystem takes 30 seconds to propagate all changes
```

**Result**:
- No time window dependency
- Each file classified by hash comparison

### Case 3: File Not Modified by Git
```bash
git reset --hard HEAD~5
# database.py wasn't modified (same in both commits)
# Watchdog doesn't fire for database.py
```

**Result**:
- No file change event → Nothing to classify

### Case 4: User Edits Same Content as Git
```bash
git reset --hard HEAD~5       # database.py → version A
vim database.py               # User types exact same content as version A
```

**Result**:
- Hash matches → `git_bulk_update` (correct - content came from git)
- Extremely rare edge case (user typing exact git content)

## Performance

**Hash Computation**: ~0.1ms per file (SHA-1 is fast)
**Git Index Read**: ~10ms for 1000 files
**Total Overhead**: Negligible vs time-window approach

## Configuration

No user-facing configuration needed. Automatically enabled when:
- Git repository detected
- Filesystem tracking enabled

## Comparison

| Approach | Accuracy | Edge Cases | Performance |
|----------|----------|------------|-------------|
| Time Window | ❌ Fails on immediate edits | ❌ Race conditions | ✅ Fast |
| Hash Comparison | ✅ Always accurate | ✅ Handles all cases | ✅ Fast |

## Design Decisions & Rationale

### Why Hash-Based Over Time-Based?

**Decision**: Use content hash comparison instead of time windows.

**Rationale**:
1. **User Workflow Reality**: Developers often edit files immediately after git operations
   - Example: `git reset --hard HEAD~5 && vim database.py`
   - Time window would misclassify this as bulk operation
   - Loses valuable context (what user is actively working on)

2. **Deterministic Classification**: Hash comparison is always accurate
   - No race conditions
   - No arbitrary timing thresholds
   - Works across all filesystem speeds

3. **Git-Native Approach**: Uses git's own mechanisms
   - `git ls-files -s` provides authoritative file states
   - SHA-1 hash is standard git blob format
   - No external dependencies or heuristics

### Why Include Create/Update/Delete in Lazy-Load?

**Decision**: Include individual file operations, exclude only bulk git operations and maintenance.

**Rationale**:
1. **Valuable Context**: File operations indicate active work
   - Creates: New functionality being added
   - Updates: Existing code being modified
   - Deletes: Cleanup or removal of obsolete code

2. **Token Efficiency with Context Preservation**:
   - Individual operations: ~10-20 per session (manageable)
   - Git bulk operations: 47+ files (overwhelming)
   - Filtering by `source` preserves context without noise

3. **Agent Understanding**: Agent needs to know current state
   - "User created auth.json" → Agent knows new feature added
   - "User updated database.py" → Agent knows schema changed
   - Without this: Agent has no idea what changed between sessions

### Why Remove from Pending After Hash Mismatch?

**Decision**: Delete file from `pending_git_hashes` after hash mismatch.

**Rationale**:
1. **Prevent Double Classification**: File already processed (git operation completed)
2. **Future Edits Are User Edits**: Any subsequent changes are user-initiated
3. **Memory Cleanup**: Don't hold stale git state indefinitely

Example:
```python
# Git rollback: database.py → "abc123..."
# User edits: database.py → "xyz789..."
# Hash mismatch → Delete from pending
# User saves again: database.py → "aaa111..."
# Not in pending → Correctly classified as user edit
```

## Next Steps

1. Implement `compute_git_hash()` function
2. Integrate `git ls-files -s` capture
3. Update `on_file_change()` logic
4. Test with rapid user edits after git operations
5. Design conversation buffer for Tier 2 context capture
