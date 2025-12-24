# Deployment Manifest: mcp_server Package

**Story**: 2 - Deploy standalone package to ~/.graphiti/
**Version**: 1.0
**Created**: 2025-12-23
**Author**: Story 2.i Implementation

---

## Overview

This document describes the structure and contents of the deployed mcp_server package at `~/.graphiti/mcp_server/`.

## Deployment Location

**Primary Path**: `~/.graphiti/mcp_server/`

**Platform-Specific Expansions**:
- **Windows**: `C:\Users\{username}\.graphiti\mcp_server\`
- **macOS/Linux**: `/home/{username}/.graphiti/mcp_server/`

## Deployment Structure

```
~/.graphiti/mcp_server/
├── .version                    # Version marker (e.g., "1.0.1")
├── graphiti_mcp_server.py     # Main MCP server entry point
├── __init__.py
├── daemon/                     # Daemon management modules
│   ├── __init__.py
│   ├── bootstrap.py           # Bootstrap service
│   ├── manager.py             # DaemonManager
│   ├── package_deployer.py    # PackageDeployer (this module)
│   ├── venv_manager.py        # VenvManager
│   ├── wrapper_generator.py   # Wrapper script generator
│   ├── path_integration.py    # PATH integration helpers
│   ├── windows_service.py     # Windows/NSSM service manager
│   ├── launchd_service.py     # macOS launchd service manager
│   └── systemd_service.py     # Linux systemd service manager
├── config/                     # Configuration modules
│   ├── __init__.py
│   └── unified_config.py      # Unified configuration system
├── api/                        # MCP API implementations
│   ├── __init__.py
│   ├── memory/                # Memory-related endpoints
│   ├── graph/                 # Graph operations
│   └── ...
└── [other submodules]

NOT DEPLOYED:
├── .venv/                     # Excluded (local development venv)
├── __pycache__/               # Excluded (bytecode cache)
├── tests/                     # Excluded (test files)
├── .pytest_cache/             # Excluded (pytest cache)
└── *.pyc                      # Excluded (compiled bytecode)
```

## Version Tracking

### Version File Format

**File**: `~/.graphiti/mcp_server/.version`

**Content**: Plain text version string matching `pyproject.toml` version
```
1.0.1
```

### Version Detection Logic

1. **On deployment**: Extract version from `mcp_server/pyproject.toml`
2. **On idempotency check**: Compare deployed `.version` with source version
3. **On upgrade**: If versions differ, backup old deployment and install new

### Version Compatibility

**Backwards Compatibility**: Not guaranteed between major versions (1.x → 2.x)

**Forwards Compatibility**: Minor/patch versions are generally compatible (1.0.x → 1.1.x)

**Upgrade Path**: Always creates backup before replacing deployment

## Exclusion Patterns

The following patterns are excluded from deployment:

| Pattern | Type | Reason |
|---------|------|--------|
| `.venv/` | Directory | Local development virtual environment |
| `__pycache__/` | Directory | Python bytecode cache (platform-specific) |
| `*.pyc` | File | Compiled Python bytecode (regenerated on import) |
| `tests/` | Directory | Unit/integration tests (not needed for runtime) |
| `.pytest_cache/` | Directory | Pytest cache |
| `*.egg-info/` | Directory | Python package metadata (development artifact) |
| `.git/` | Directory | Git repository data |
| `.gitignore` | File | Git configuration |
| `*.dist-info/` | Directory | Python distribution metadata |

## Backup Strategy

### Backup Naming Convention

**Format**: `~/.graphiti/mcp_server.backup.{timestamp}/`

**Timestamp Format**: `YYYYMMDD-HHMMSS` (e.g., `20231215-143022`)

**Example**: `~/.graphiti/mcp_server.backup.20231215-143022/`

### When Backups Are Created

1. **Version upgrade**: Existing deployment version != source version
2. **Force redeployment**: `deploy_package(force=True)` called
3. **Manual deployment**: User explicitly triggers deployment

### Backup Retention

**Automatic Cleanup**: Not implemented (manual cleanup required)

**Recommendation**: Keep 3-5 most recent backups, delete older ones

### Restore from Backup

**Manual Restore** (if needed):
```bash
# Remove current deployment
rm -rf ~/.graphiti/mcp_server/

# Restore from backup (replace timestamp)
mv ~/.graphiti/mcp_server.backup.20231215-143022/ ~/.graphiti/mcp_server/
```

## Deployment Process

### Initial Deployment

1. **Detection**: Find source `mcp_server/` in repository
2. **Version extraction**: Read version from `pyproject.toml`
3. **Directory creation**: Create `~/.graphiti/mcp_server/`
4. **File copy**: Copy all files excluding exclusion patterns
5. **Version marker**: Write `.version` file
6. **Verification**: Validate deployment structure

### Idempotent Redeployment

1. **Check existing**: Verify `~/.graphiti/mcp_server/` exists
2. **Version comparison**: Compare `.version` with source version
3. **Skip if match**: If versions match and `force=False`, skip deployment
4. **Upgrade if different**: If versions differ, proceed with backup + deployment

### Upgrade Deployment

1. **Backup**: Create timestamped backup of existing deployment
2. **Remove old**: Delete `~/.graphiti/mcp_server/`
3. **Deploy new**: Copy new version to deployment location
4. **Update version**: Write new version to `.version` file
5. **Verify**: Validate new deployment

## Integration Points

### Bootstrap Service

**Path Resolution** (in `bootstrap.py`):
```python
def _get_mcp_server_path(self) -> Path:
    # 1. Environment override
    if env_path := os.environ.get("GRAPHITI_MCP_SERVER"):
        return Path(env_path)

    # 2. Deployed location (NEW)
    deployed_path = Path.home() / ".graphiti" / "mcp_server" / "graphiti_mcp_server.py"
    if deployed_path.exists():
        return deployed_path

    # 3. Relative path (fallback for development)
    bootstrap_dir = Path(__file__).parent
    mcp_server_dir = bootstrap_dir.parent
    return mcp_server_dir / "graphiti_mcp_server.py"
```

### Daemon Manager

**Installation Workflow** (in `manager.py`):
```
1. Validate Python version
2. Create dedicated venv (~/.graphiti/.venv/)
2.4. Deploy mcp_server package (NEW STEP)
2.5. Install mcp_server into venv
2.6. Generate CLI wrappers
3. Create config file
4. Install OS service
```

## Security Considerations

### Path Traversal Prevention

- **All paths validated**: Resolved to absolute paths before operations
- **Deployment scope**: Only writes to `~/.graphiti/` directory
- **No user input in paths**: Timestamp format is fixed (no injection)

### File Permissions

- **Windows**: Inherits user permissions (typically writable by user only)
- **Unix**: Created with mode `0755` for directories, `0644` for files

### Version File Integrity

- **Content**: Plain text version string only
- **No code execution**: File is read as text, not executed
- **Validation**: Version format checked against pattern `^\d+\.\d+\.\d+$`

## Troubleshooting

### Deployment Fails: "Cannot write to ~/.graphiti/"

**Cause**: Insufficient permissions

**Solution**:
```bash
# Check permissions
ls -la ~/.graphiti/

# Fix permissions (Unix)
chmod 755 ~/.graphiti/
```

### Deployment Fails: "Insufficient disk space"

**Cause**: Low disk space

**Solution**:
```bash
# Check available space
df -h ~/.graphiti/

# Clean up old backups
rm -rf ~/.graphiti/mcp_server.backup.*
```

### Deployment Succeeds but Bootstrap Fails

**Cause**: Deployment incomplete or corrupted

**Solution**:
```bash
# Force redeployment
graphiti-mcp daemon install --force

# Or manually verify deployment
ls -la ~/.graphiti/mcp_server/
cat ~/.graphiti/mcp_server/.version
```

### Old Deployment Not Backed Up

**Cause**: Backup process failed mid-operation

**Solution**: Check `~/.graphiti/` for partial backups:
```bash
ls -la ~/.graphiti/ | grep backup
```

## Upgrade Implications

### Minor Version Upgrades (1.0.x → 1.1.x)

- **Backup created**: Yes (automatic)
- **Config migration**: Not required (config schema stable)
- **Service restart**: Not required (bootstrap detects new deployment)

### Major Version Upgrades (1.x → 2.x)

- **Backup created**: Yes (automatic)
- **Config migration**: May be required (check release notes)
- **Service restart**: May be required (check release notes)
- **Manual intervention**: Possible (breaking changes documented)

### Downgrade Strategy

**Supported**: Yes, via backup restore

**Process**:
1. Stop daemon: `graphiti-mcp daemon uninstall`
2. Restore from backup (see "Restore from Backup" above)
3. Reinstall daemon: `graphiti-mcp daemon install`

## Maintenance

### Cleanup Recommendations

**Old Backups**: Remove backups older than 30 days
```bash
find ~/.graphiti/ -name "mcp_server.backup.*" -mtime +30 -exec rm -rf {} \;
```

**Deployment Verification**: Monthly check
```bash
# Verify deployment structure
ls -la ~/.graphiti/mcp_server/

# Check version
cat ~/.graphiti/mcp_server/.version

# Validate with deployer
python -c "from mcp_server.daemon.package_deployer import PackageDeployer; print(PackageDeployer().verify_deployment())"
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-23
**Maintained By**: Graphiti development team
