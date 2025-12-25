# Design: Version Tracking System

**Story**: 6 - Implement Version Tracking
**Phase**: Discovery (6.d)
**Created**: 2025-12-25
**Status**: Complete

## Overview

This document outlines the design for version tracking in the Graphiti MCP server installer. The system enables upgrade detection, rollback capability, and installation audit trails.

---

## 1. VERSION File Format

### Location
- `{install_dir}/VERSION`
- Example: `C:\Users\Admin\AppData\Local\Programs\Graphiti\VERSION`

### Format
Simple text file containing semantic version string (single line, no whitespace):

```
0.24.3
```

### Specification
- **Semantic Versioning**: `MAJOR.MINOR.PATCH` format (https://semver.org/)
- **No prefix**: Plain version string (no "v" prefix)
- **Single line**: No trailing newline
- **Encoding**: UTF-8

### Rationale
- **Simplicity**: Easy to read programmatically and manually
- **Industry standard**: Used by pip, npm, Docker, and other tools
- **Lightweight**: Minimal disk space (~10 bytes)
- **Version comparison**: Compatible with `packaging.version` module

---

## 2. INSTALL_INFO JSON Schema

### Location
- `{install_dir}/INSTALL_INFO`
- Example: `C:\Users\Admin\AppData\Local\Programs\Graphiti\INSTALL_INFO`

### Schema (v1.0)

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "installed_at", "installed_from", "installer_version"],
  "properties": {
    "version": {
      "type": "string",
      "description": "Installed version (matches VERSION file)",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "installed_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of installation (UTC)"
    },
    "installed_from": {
      "type": "string",
      "description": "Absolute path to source repository at install time"
    },
    "source_commit": {
      "type": "string",
      "description": "Git commit SHA (optional, 40-char hex)",
      "pattern": "^[a-f0-9]{40}$"
    },
    "python_version": {
      "type": "string",
      "description": "Python version used for installation",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "platform": {
      "type": "string",
      "description": "Platform string from platform.platform()"
    },
    "installer_version": {
      "type": "string",
      "description": "Version of installer script itself",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    }
  }
}
```

### Example

```json
{
  "version": "0.24.3",
  "installed_at": "2025-12-25T18:30:45Z",
  "installed_from": "C:\\Users\\Admin\\Documents\\GitHub\\graphiti",
  "source_commit": "75efd02abc123def456789012345678901234567",
  "python_version": "3.10.18",
  "platform": "Windows-10-10.0.26100-SP0",
  "installer_version": "2.1.0"
}
```

### Rationale
- **Audit trail**: Full context for debugging installation issues
- **Upgrade safety**: Verify Python compatibility before upgrade
- **Rollback support**: Know exactly which commit to restore to
- **Support requests**: Users can share INSTALL_INFO for diagnosis

---

## 3. Source Version Detection

### Strategy: Multi-Source Fallback

The installer must determine the version to install from the source repository using a priority cascade:

#### Priority Order

1. **pyproject.toml** (HIGHEST PRIORITY)
   - Location: `{source_dir}/pyproject.toml`
   - Key: `tool.poetry.version` or `project.version`
   - Example: `version = "0.24.3"`
   - Use: `tomllib.loads()` (Python 3.11+) or `toml` package

2. **Git tag** (FALLBACK 1)
   - Command: `git describe --tags --exact-match HEAD`
   - Format: `v0.24.3` (strip "v" prefix if present)
   - Requires: Source directory is a git repo with annotated/signed tag

3. **Git commit SHA** (FALLBACK 2)
   - Command: `git rev-parse --short=7 HEAD`
   - Format: `0.24.3-dev+abc1234` (version from pyproject.toml + commit)
   - Indicates: Development version from uncommitted/untagged code

4. **Error** (NO VERSION FOUND)
   - Raise `ValidationError` with message: "Cannot determine version from source"
   - User action: Tag release or ensure pyproject.toml has version

### Implementation Function

```python
def get_source_version(source_dir: Path) -> str:
    """
    Detect version from source repository.

    Args:
        source_dir: Path to source repository root

    Returns:
        Semantic version string (e.g., "0.24.3" or "0.24.3-dev+abc1234")

    Raises:
        ValidationError: If version cannot be determined
    """
    # 1. Try pyproject.toml
    pyproject = source_dir / "pyproject.toml"
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text())

        # Poetry format
        if "tool" in data and "poetry" in data["tool"] and "version" in data["tool"]["poetry"]:
            return data["tool"]["poetry"]["version"]

        # PEP 621 format
        if "project" in data and "version" in data["project"]:
            return data["project"]["version"]

    # 2. Try git tag
    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            cwd=source_dir,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        return tag.lstrip("v")  # Remove v prefix
    except subprocess.CalledProcessError:
        pass

    # 3. Try git commit + pyproject version
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=source_dir,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()

        # Get base version from pyproject.toml (required for dev version)
        if pyproject.exists():
            data = tomllib.loads(pyproject.read_text())
            base_version = (
                data.get("tool", {}).get("poetry", {}).get("version") or
                data.get("project", {}).get("version")
            )
            if base_version:
                return f"{base_version}-dev+{commit}"
    except subprocess.CalledProcessError:
        pass

    # 4. Error - no version found
    raise ValidationError(
        "Cannot determine version from source repository",
        step="get_source_version",
        details={"source_dir": str(source_dir)}
    )
```

---

## 4. Installed Version Detection

### Strategy: Read VERSION File

The upgrade system must detect the currently installed version to determine if upgrade is needed.

### Implementation Function

```python
def get_installed_version(install_dir: Path) -> Optional[str]:
    """
    Read installed version from VERSION file.

    Args:
        install_dir: Path to installation directory

    Returns:
        Semantic version string (e.g., "0.24.3") or None if not installed
    """
    version_file = install_dir / "VERSION"

    if not version_file.exists():
        return None

    version = version_file.read_text().strip()

    # Validate format (basic check - full validation in upgrade logic)
    if not version or not version[0].isdigit():
        logger.warning(f"Invalid VERSION file format: {version}")
        return None

    return version
```

---

## 5. Upgrade Detection Algorithm

### Strategy: Semantic Version Comparison

Use Python's `packaging.version` module for robust version comparison that handles:
- Pre-release versions (0.24.3-alpha.1)
- Development versions (0.24.3-dev+abc1234)
- Build metadata (+build.123)

### Implementation Function

```python
from packaging.version import Version, InvalidVersion

def check_for_upgrade(install_dir: Path, source_dir: Path) -> Dict[str, Any]:
    """
    Compare installed version with source version to detect upgrade.

    Args:
        install_dir: Path to installation directory
        source_dir: Path to source repository

    Returns:
        Dictionary with upgrade info:
        {
            "upgrade_available": bool,
            "installed_version": str or None,
            "source_version": str,
            "comparison": str  # "newer", "same", "older", "not_installed"
        }

    Raises:
        ValidationError: If source version cannot be determined
    """
    # Get versions
    installed = get_installed_version(install_dir)
    source = get_source_version(source_dir)

    # Not installed case
    if installed is None:
        return {
            "upgrade_available": False,
            "installed_version": None,
            "source_version": source,
            "comparison": "not_installed"
        }

    # Parse versions for comparison
    try:
        installed_ver = Version(installed)
        source_ver = Version(source)
    except InvalidVersion as e:
        raise ValidationError(
            f"Invalid version format: {e}",
            step="check_for_upgrade",
            details={"installed": installed, "source": source}
        )

    # Compare
    if source_ver > installed_ver:
        comparison = "newer"
        upgrade_available = True
    elif source_ver == installed_ver:
        comparison = "same"
        upgrade_available = False
    else:
        comparison = "older"
        upgrade_available = False

    return {
        "upgrade_available": upgrade_available,
        "installed_version": installed,
        "source_version": source,
        "comparison": comparison
    }
```

---

## 6. Integration Points

### In GraphitiInstaller.install()

**Step 7: Write version information**

```python
def _write_version_info(self, source_dir: Path) -> str:
    """
    Write VERSION and INSTALL_INFO files.

    Returns:
        Version string that was written
    """
    # Detect version from source
    version = get_source_version(source_dir)

    # Write VERSION file
    version_file = self.paths.install_dir / "VERSION"
    version_file.write_text(version)

    # Collect install metadata
    install_info = {
        "version": version,
        "installed_at": datetime.utcnow().isoformat() + "Z",
        "installed_from": str(source_dir.resolve()),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.platform(),
        "installer_version": "2.1.0"
    }

    # Add git commit if available
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=source_dir,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        install_info["source_commit"] = commit
    except subprocess.CalledProcessError:
        pass  # Not a git repo or no git - skip commit field

    # Write INSTALL_INFO
    info_file = self.paths.install_dir / "INSTALL_INFO"
    info_file.write_text(json.dumps(install_info, indent=2))

    logger.info(f"Wrote version info: {version}")
    return version
```

### In GraphitiInstaller.upgrade()

**Step 1: Detect existing version**

```python
def upgrade(self, source_dir: Optional[Path] = None, force: bool = False) -> InstallationResult:
    """Upgrade existing installation."""

    # Check for upgrade
    upgrade_info = check_for_upgrade(self.paths.install_dir, source_dir)

    if upgrade_info["comparison"] == "not_installed":
        raise ValidationError(
            "No existing installation found. Use install() instead.",
            step="upgrade"
        )

    if not force and not upgrade_info["upgrade_available"]:
        logger.info(f"No upgrade needed: {upgrade_info['installed_version']} is current")
        return InstallationResult(
            success=True,
            version=upgrade_info["installed_version"],
            details={"action": "skipped", "reason": "version_current"}
        )

    # Continue with upgrade...
```

---

## 7. Testing Strategy

### Unit Tests

1. **test_version_file_format()**
   - Write VERSION file with various formats
   - Verify get_installed_version() parses correctly
   - Test invalid formats return None

2. **test_install_info_schema()**
   - Generate INSTALL_INFO with all fields
   - Validate against JSON schema
   - Test missing optional fields (source_commit)

3. **test_source_version_detection()**
   - Mock pyproject.toml with version
   - Mock git tag
   - Mock git commit
   - Test fallback cascade (pyproject -> tag -> commit -> error)

4. **test_upgrade_detection()**
   - Test newer source (upgrade needed)
   - Test same version (no upgrade)
   - Test older source (no upgrade)
   - Test pre-release comparison (0.24.3-alpha.1 < 0.24.3)
   - Test dev version comparison (0.24.3-dev+abc < 0.24.3)

### Integration Tests

1. **test_full_install_creates_version_files()**
   - Run GraphitiInstaller.install()
   - Verify VERSION exists and has correct content
   - Verify INSTALL_INFO exists and is valid JSON

2. **test_upgrade_detection_integration()**
   - Install version 0.24.3
   - Change source to 0.25.0
   - Run check_for_upgrade()
   - Verify upgrade_available=True

---

## 8. Dependencies

### Python Packages

- `packaging` - Semantic version comparison (already in requirements)
- `tomllib` - TOML parsing (Python 3.11+ stdlib) OR `toml` package (fallback)

### System Requirements

- Git (optional) - For commit SHA extraction
- Write permissions to install_dir

---

## 9. Error Handling

### Error Cases

1. **Source version not found**
   - Raise: `ValidationError("Cannot determine version from source")`
   - User action: Ensure pyproject.toml has version or tag the release

2. **Invalid VERSION file**
   - Log warning, return None from get_installed_version()
   - Treat as "not installed" in upgrade check

3. **Invalid INSTALL_INFO JSON**
   - Log warning, continue (non-critical)
   - Upgrade can proceed without install metadata

4. **Git not available**
   - Skip source_commit field in INSTALL_INFO
   - Skip git tag fallback in version detection

---

## 10. Migration Notes

### For Existing Installations (v0.24.3 and earlier)

Installations created before version tracking will not have VERSION or INSTALL_INFO files.

**Detection Strategy**:
```python
if not (install_dir / "VERSION").exists():
    # Legacy installation detected
    # Option 1: Treat as version 0.24.3 (last version without tracking)
    # Option 2: Force reinstall to add version tracking
    # Recommendation: Option 1 for smooth migration
```

**Recommended Behavior**:
- First upgrade after v2.1.0 deployment creates VERSION + INSTALL_INFO
- Use version 0.24.3 as baseline for legacy installs
- Log migration event in INSTALL_INFO as metadata

---

## 11. Future Enhancements

### Post-v2.1 Features

1. **Upgrade history log**
   - Track all upgrades in `state_dir/upgrade_history.json`
   - Include rollback count, success rate

2. **Version pinning**
   - Allow users to pin to specific version
   - Skip auto-upgrades when pinned

3. **Beta channel support**
   - Allow installation of pre-release versions
   - Separate VERSION file or suffix (0.25.0-beta.1)

4. **Downgrade support**
   - Detect older source version
   - Warn user before downgrade
   - Use same rollback mechanism as failed upgrade

---

## Acceptance Criteria Checklist

### Discovery Phase (6.d)

- [x] (P0) Design VERSION file format (semantic version string)
- [x] Design INSTALL_INFO JSON schema
- [x] Design upgrade detection algorithm (version comparison)
- [x] Determine how to get source version from repo

---

## References

- Semantic Versioning: https://semver.org/
- Python packaging.version: https://packaging.pypa.io/en/stable/version.html
- XDG Base Directory: https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
- Graphiti Paths: `mcp_server/daemon/paths.py`
- Graphiti Installer: `mcp_server/daemon/installer.py`
