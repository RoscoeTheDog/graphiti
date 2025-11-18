# Cross-Cutting Requirements for Session Tracking Integration

**Version**: 1.0
**Last Updated**: 2025-11-13
**Applies To**: All stories in Session Tracking Integration sprint

---

## Overview

This document defines requirements that apply across all implementation stories in the Session Tracking Integration sprint. These requirements must be satisfied by all code, regardless of the specific story being implemented.

---

## 1. Platform-Agnostic Path Handling

### Requirement
**All path operations MUST be platform-agnostic, returning paths in the native OS format while maintaining cross-platform consistency for internal operations.**

### Strategy

#### 1.1 Dual-Path Strategy

**For Hashing/Storage (Internal):**
- Always normalize to UNIX format: `/c/Users/...` on Windows, `/home/...` on Unix
- Use for: Hash calculation, storage keys, cross-platform comparisons
- Implementation: `_normalize_path_for_hash()` or equivalent

**For Return Values (External):**
- Always use native OS format: `C:\Users\...` on Windows, `/home/...` on Unix
- Use for: All Path objects returned to callers, filesystem operations
- Implementation: Python's `pathlib.Path` (handles platform automatically)

#### 1.2 Platform Detection

```python
import platform
from pathlib import Path

# Detect OS
is_windows = platform.system() == "Windows"

# Pre-flight check for all path operations
def normalize_path_for_hash(path: str) -> str:
    """Normalize to UNIX format for consistent hashing."""
    p = Path(path).resolve()
    path_str = p.as_posix()

    if is_windows and ":" in path_str:
        drive, rest = path_str.split(":", 1)
        path_str = f"/{drive.lower()}{rest}"

    return path_str.rstrip('/')

def to_native_path(unix_path: str) -> Path:
    """Convert UNIX path to native OS format."""
    if is_windows:
        match = re.match(r'^/([a-zA-Z])(/.*)?$', unix_path)
        if match:
            drive = match.group(1).upper()
            rest = match.group(2) or ''
            return Path(f"{drive}:{rest}")
    return Path(unix_path)
```

### Acceptance Criteria

For every story that handles paths:

- [ ] Internal hashing/comparison uses UNIX format
- [ ] Returned Path objects use native OS format
- [ ] Cross-platform tests validate both Windows and Unix behavior
- [ ] Path operations work correctly on Windows, Unix, MSYS, WSL
- [ ] Hash consistency maintained across platforms for same logical path

### Test Requirements

Each module handling paths MUST include:

1. **Hash Consistency Tests**: Validate same logical path produces same hash on different platforms
2. **Native Format Tests**: Validate returned paths use OS-native format
3. **Platform-Specific Tests**: Test with both Windows and Unix path styles
4. **Edge Cases**: Test MSYS format (`/c/...`), UNC paths (`//server/...`), relative paths

### Examples

**Good Example (path_resolver.py):**
```python
def get_session_file(self, project_path: str, session_id: str) -> Path:
    # Hash uses UNIX format internally
    project_hash = self.get_project_hash(project_path)

    # Return uses native format (Path handles this automatically)
    sessions_dir = self.projects_dir / project_hash / "sessions"
    return sessions_dir / f"{session_id}.jsonl"
```

**Bad Example:**
```python
def get_session_file(self, project_path: str, session_id: str) -> str:
    # Returns string in UNIX format - breaks on Windows!
    project_hash = self.get_project_hash(project_path)
    return f"{self.projects_dir}/{project_hash}/sessions/{session_id}.jsonl"
```

---

## 2. Error Handling and Logging

### Requirement
**All modules MUST implement comprehensive error handling with structured logging.**

### Standards

#### 2.1 Logging Levels

- **DEBUG**: Detailed diagnostic information (offset tracking, hash calculations)
- **INFO**: Normal operation milestones (session started, file detected)
- **WARNING**: Recoverable issues (missing file, parse failure)
- **ERROR**: Failures requiring attention (database errors, I/O errors)
- **CRITICAL**: System-level failures (MCP server crash, database unavailable)

#### 2.2 Exception Handling

```python
import logging

logger = logging.getLogger(__name__)

try:
    # Operation
    result = parse_file(file_path)
except FileNotFoundError:
    logger.warning(f"File not found: {file_path}")
    return None  # Graceful degradation
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in {file_path}: {e}")
    return None
except Exception as e:
    logger.error(f"Unexpected error processing {file_path}: {e}", exc_info=True)
    raise  # Re-raise unexpected errors
```

### Acceptance Criteria

- [ ] All file I/O wrapped in try-except blocks
- [ ] Appropriate logging levels used
- [ ] Error messages include context (file paths, IDs)
- [ ] Unexpected errors logged with stack traces (`exc_info=True`)
- [ ] Graceful degradation for recoverable errors

---

## 3. Type Safety and Documentation

### Requirement
**All code MUST use type hints and comprehensive docstrings.**

### Standards

#### 3.1 Type Hints

```python
from typing import Optional, List, Dict, Tuple
from pathlib import Path

def parse_file(
    file_path: str,
    start_offset: int = 0
) -> Tuple[List[SessionMessage], int]:
    """Parse JSONL file from given offset.

    Args:
        file_path: Path to JSONL file
        start_offset: Byte offset to start reading from

    Returns:
        Tuple of (parsed messages, new offset)

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file not readable
    """
    pass
```

#### 3.2 Pydantic Models

Use Pydantic for configuration and complex types:

```python
from pydantic import BaseModel, Field

class SessionTrackingConfig(BaseModel):
    """Configuration for session tracking."""

    enabled: bool = Field(default=False, description="Enable session tracking")
    inactivity_timeout: int = Field(default=300, description="Seconds before session close")
    summarization_model: str = Field(default="gpt-4o-mini", description="Model for summaries")
```

### Acceptance Criteria

- [ ] All functions have type hints for parameters and return values
- [ ] Complex types documented with docstrings
- [ ] Configuration uses Pydantic models
- [ ] Type checking passes with mypy (if configured)

---

## 4. Testing Requirements

### Requirement
**All modules MUST have comprehensive unit tests with >80% coverage.**

### Standards

#### 4.1 Test Structure

```python
import pytest
from pathlib import Path

class TestModuleName:
    """Test suite for ModuleName."""

    def test_basic_functionality(self):
        """Test basic operation."""
        pass

    def test_error_handling(self):
        """Test error conditions."""
        pass

    def test_edge_cases(self):
        """Test boundary conditions."""
        pass

    @pytest.mark.parametrize("input,expected", [
        ("case1", "result1"),
        ("case2", "result2"),
    ])
    def test_multiple_cases(self, input, expected):
        """Test multiple scenarios."""
        pass
```

#### 4.2 Coverage Requirements

- **Unit Tests**: Test individual functions/methods
- **Integration Tests**: Test module interactions
- **Platform Tests**: Test Windows and Unix behavior
- **Edge Cases**: Test boundary conditions, errors, empty inputs

### Acceptance Criteria

- [ ] All public methods have unit tests
- [ ] Error conditions tested
- [ ] Platform-specific behavior tested
- [ ] Integration tests for cross-module interactions
- [ ] Tests pass on CI/CD pipeline

---

## 5. Performance Requirements

### Requirement
**Session tracking MUST have minimal performance impact (<5% overhead).**

### Standards

#### 5.1 Resource Efficiency

- **File Watching**: Use offset tracking for incremental reads
- **Memory**: Limit in-memory session data to active sessions only
- **CPU**: Async/background processing for summarization
- **I/O**: Batch operations where possible

#### 5.2 Monitoring

```python
import time

def monitored_operation(operation_name: str):
    """Decorator for performance monitoring."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start

            if duration > 1.0:  # Log slow operations
                logger.warning(f"{operation_name} took {duration:.2f}s")

            return result
        return wrapper
    return decorator
```

### Acceptance Criteria

- [ ] File watcher overhead <5% CPU
- [ ] Memory usage bounded (no leaks)
- [ ] Summarization runs asynchronously
- [ ] Large sessions (100+ exchanges) handled efficiently
- [ ] Performance benchmarks documented

---

## 6. Security Requirements

### Requirement
**Session tracking MUST NOT expose sensitive information.**

### Standards

#### 6.1 Data Filtering

- **Never log**: Credentials, API keys, tokens, passwords
- **Sanitize**: File paths (use relative paths in logs)
- **Redact**: User-specific information in summaries

#### 6.2 File Permissions

```python
from pathlib import Path
import os

def create_session_file(file_path: Path):
    """Create session file with restricted permissions."""
    # Create with read/write for owner only
    os.umask(0o077)
    file_path.touch(mode=0o600)
```

### Acceptance Criteria

- [ ] No credentials logged or stored
- [ ] File permissions restricted appropriately
- [ ] User data sanitized in summaries
- [ ] Security audit passed

---

## 7. Configuration Management

### Requirement
**All configuration MUST use unified configuration system (`graphiti.config.json`).**

### Standards

#### 7.1 Configuration Structure

```json
{
  "session_tracking": {
    "enabled": false,
    "inactivity_timeout": 300,
    "summarization": {
      "model": "gpt-4o-mini",
      "max_tokens": 1000
    },
    "file_watching": {
      "poll_interval": 1.0
    }
  }
}
```

#### 7.2 Schema Validation

Use Pydantic for validation:

```python
from graphiti_core.config import SessionTrackingConfig

config = SessionTrackingConfig.from_json("graphiti.config.json")
```

### Acceptance Criteria

- [ ] Configuration uses `graphiti.config.json`
- [ ] Schema defined with Pydantic
- [ ] Validation errors reported clearly
- [ ] Secrets use `.env` (not JSON)
- [ ] Documentation updated with config options

---

## 8. Documentation Requirements

### Requirement
**All features MUST be documented for users and developers.**

### Standards

#### 8.1 User Documentation

- **README.md**: High-level overview and quick start
- **CONFIGURATION.md**: All configuration options
- **MCP_TOOLS.md**: MCP tool reference
- **Guides**: Step-by-step tutorials

#### 8.2 Developer Documentation

- **Module docstrings**: Purpose and usage
- **Function docstrings**: Parameters, returns, raises
- **Architecture docs**: System design and interactions
- **Troubleshooting**: Common issues and solutions

### Acceptance Criteria

- [ ] User-facing documentation updated
- [ ] Developer documentation complete
- [ ] Code examples provided
- [ ] Troubleshooting guide created
- [ ] CHANGELOG.md updated

---

## Compliance Checklist

Use this checklist for each story:

### Implementation Phase
- [ ] Platform-agnostic path handling implemented
- [ ] Error handling and logging added
- [ ] Type hints and docstrings complete
- [ ] Configuration uses unified system
- [ ] Security requirements satisfied

### Testing Phase
- [ ] Unit tests written and passing
- [ ] Integration tests added
- [ ] Platform-specific tests included
- [ ] Performance benchmarks run
- [ ] Security audit completed

### Documentation Phase
- [ ] User documentation updated
- [ ] Developer documentation complete
- [ ] Configuration documented
- [ ] Examples provided
- [ ] CHANGELOG updated

### Review Phase
- [ ] Code review completed
- [ ] All acceptance criteria met
- [ ] Cross-cutting requirements satisfied
- [ ] Tests passing on CI/CD
- [ ] Documentation reviewed

---

## References

- **Platform Path Handling**: `.claude/implementation/PLATFORM_AGNOSTIC_PATHS.md`
- **Configuration Schema**: `CONFIGURATION.md`
- **Testing Standards**: `tests/README.md` (to be created)
- **Security Guidelines**: `SECURITY.md` (to be created)

---

**Note**: This document is living and will be updated as new cross-cutting requirements are identified during the sprint.
