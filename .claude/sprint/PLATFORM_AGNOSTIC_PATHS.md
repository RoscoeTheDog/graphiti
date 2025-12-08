# Platform-Agnostic Path Handling in Session Tracking

## Problem
Initial implementation normalized all paths to UNIX format for both hashing and return values. This created issues when returned paths needed to work with native OS filesystem operations.

## Solution
Implemented a dual-strategy approach:

### 1. Hashing Strategy (Always UNIX)
- Method: `_normalize_path_for_hash(path: str) -> str`
- Purpose: Ensure consistent hash values across platforms
- Format: Always UNIX-style (`/c/Users/...` on Windows)
- Used for: Project hash calculation only

### 2. Return Strategy (Native OS Format)
- Method: `_to_native_path(unix_path: str) -> Path`
- Purpose: Return paths in format expected by OS filesystem
- Format: OS-specific (Windows: `C:\...`, Unix: `/...`)
- Used for: All Path objects returned to callers

## Key Implementation Details

**Path Normalization for Hashing:**
```python
def _normalize_path_for_hash(self, path: str) -> str:
    # Convert to absolute path
    p = Path(path).resolve()
    # Convert to POSIX format
    path_str = p.as_posix()
    # Windows: C:/Users/... -> /c/Users/...
    if platform.system() == "Windows" and ":" in path_str:
        drive, rest = path_str.split(":", 1)
        path_str = f"/{drive.lower()}{rest}"
    return path_str.rstrip('/')
```

**Native Path Conversion:**
```python
def _to_native_path(self, unix_path: str) -> Path:
    # On Windows: /c/Users/... -> C:\Users\...
    if platform.system() == "Windows":
        match = re.match(r'^/([a-zA-Z])(/.*)?$', unix_path)
        if match:
            drive = match.group(1).upper()
            rest = match.group(2) or ''
            return Path(f"{drive}:{rest}")
    # Unix: use as-is
    return Path(unix_path)
```

## Benefits
1. **Hash Consistency**: Same logical path produces same hash on any platform
2. **OS Compatibility**: Returned paths work natively with filesystem operations
3. **Cross-Platform**: Code works identically on Windows, Unix, MSYS, WSL
4. **Transparent**: Callers don't need to know about platform differences

## Test Coverage
- 30 tests passing (10 parser + 20 path resolver)
- Platform-specific test cases for Windows and Unix
- Hash consistency validation across path format variations
- Native format validation for returned Path objects

## Related Files
- `graphiti_core/session_tracking/path_resolver.py` - Implementation
- `tests/session_tracking/test_path_resolver.py` - Test suite
- Inspired by: `~/.claude/resources/scripts/filepath_to_unix.py`