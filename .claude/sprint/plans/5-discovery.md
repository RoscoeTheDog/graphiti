# Story 5.d: Implement Frozen Package Deployment - Discovery Phase

**Story**: 5 - Implement Frozen Package Deployment
**Phase**: Discovery (5.d)
**Status**: completed
**Date**: 2025-12-25

---

## Overview

Analyzed the frozen package deployment strategy for copying `mcp_server/` and `graphiti_core/` packages to the installation `lib/` directory instead of using pip editable installs. This discovery phase examined the existing `PackageDeployer` class, destination paths, exclusion patterns, and verification mechanisms.

---

## Analysis Results

### 1. Package Copy Strategy (What to Include/Exclude)

**Packages to Deploy**:
- `mcp_server/` → `{install_dir}/lib/mcp_server/`
- `graphiti_core/` → `{install_dir}/lib/graphiti_core/`

**Source Location Detection** (from PackageDeployer analysis):
1. **Environment variable**: `GRAPHITI_REPO_PATH` (highest priority)
2. **Current working directory**: Check for `mcp_server/pyproject.toml`
3. **Relative to module file**: Navigate from `__file__` to find repo root

**Recommendation**: Use existing `PackageDeployer._get_source_path()` logic with modifications to:
- Support finding both `mcp_server/` and `graphiti_core/` packages
- Validate both packages exist before deployment
- Handle monorepo structure (both packages in same repo root)

---

### 2. Files to Exclude

**Current PackageDeployer.EXCLUSIONS** (comprehensive list):
```python
EXCLUSIONS = {
    ".venv",           # Virtual environment
    "__pycache__",     # Python bytecode cache
    "*.pyc",           # Compiled Python files
    "tests",           # Test files
    ".pytest_cache",   # Pytest cache
    "*.egg-info",      # Package metadata
    ".git",            # Git repository
    ".gitignore",      # Git ignore file
    "*.dist-info",     # Distribution info
}
```

**Additional exclusions needed** (discovered during analysis):
- `.coverage` - Coverage.py data files
- `htmlcov/` - HTML coverage reports
- `.tox/` - Tox testing cache
- `.mypy_cache/` - MyPy type checker cache
- `*.so` - Compiled extensions (rebuild in venv)
- `*.pyd` - Windows compiled extensions
- `*.egg` - Old egg format
- `build/` - Build artifacts
- `dist/` - Distribution artifacts

**Recommendation**: Extend `PackageDeployer.EXCLUSIONS` with additional patterns above.

---

### 3. Source Package Discovery

**Existing Logic** (`PackageDeployer._get_source_path()`):
```python
def _get_source_path(self) -> Path:
    # 1. Check GRAPHITI_REPO_PATH environment variable
    # 2. Check current working directory for mcp_server/pyproject.toml
    # 3. Check relative to __file__ (daemon/package_deployer.py -> mcp_server/)
```

**Required Modifications**:
1. **Find repository root** (not just mcp_server/):
   - Look for `.git/` directory
   - Look for root `pyproject.toml` or `README.md`
   - Validate both `mcp_server/` and `graphiti_core/` exist

2. **Return both package paths**:
   ```python
   def _get_source_packages(self) -> Tuple[Path, Path]:
       repo_root = self._find_repo_root()
       mcp_server = repo_root / "mcp_server"
       graphiti_core = repo_root / "graphiti_core"
       # Validate both exist
       return (mcp_server, graphiti_core)
   ```

**Recommendation**: Create new method `_find_repo_root()` that returns the repository root, then derive both package paths from it.

---

### 4. Package Verification Mechanism

**Current Verification** (`PackageDeployer.verify_deployment()`):
```python
def verify_deployment(self) -> bool:
    # Check deployment directory exists
    # Check version file exists
    # Check key files present (graphiti_mcp_server.py, daemon/, config/)
```

**Required Enhancements for Dual-Package Deployment**:

1. **Verify all `__init__.py` files present**:
   ```python
   def _verify_init_files(self, package_dir: Path) -> bool:
       """Verify all subdirectories with .py files have __init__.py."""
       for py_file in package_dir.rglob("*.py"):
           parent = py_file.parent
           if parent != package_dir:  # Not root of package
               init_file = parent / "__init__.py"
               if not init_file.exists():
                   logger.error(f"Missing __init__.py in {parent}")
                   return False
       return True
   ```

2. **Verify package structure** (critical files/directories):
   - `mcp_server/`:
     - `graphiti_mcp_server.py` (entry point)
     - `daemon/` directory
     - `config/` directory
     - `api/` directory
   - `graphiti_core/`:
     - `graphiti.py` (main class)
     - `driver/` directory
     - `embedder/` directory
     - `llm_client/` directory

3. **Verify importability**:
   ```python
   def _verify_import(self, lib_dir: Path) -> bool:
       """Verify packages are importable via PYTHONPATH."""
       import sys
       sys.path.insert(0, str(lib_dir))
       try:
           import mcp_server
           import graphiti_core
           return True
       except ImportError as e:
           logger.error(f"Import verification failed: {e}")
           return False
       finally:
           sys.path.remove(str(lib_dir))
   ```

**Recommendation**: Implement three-tier verification:
1. **Structural check**: Files and directories exist
2. **Init file check**: All packages have `__init__.py`
3. **Import check**: Packages are importable with `PYTHONPATH`

---

## Implementation Design

### Architecture

```
GraphitiInstaller._freeze_packages() orchestrates deployment:
    ├─> _find_repo_root() - Detect repository root
    ├─> _validate_source_packages() - Ensure mcp_server/ and graphiti_core/ exist
    ├─> _deploy_package(mcp_server, lib/mcp_server/) - Copy first package
    ├─> _deploy_package(graphiti_core, lib/graphiti_core/) - Copy second package
    └─> _verify_frozen_packages() - Comprehensive verification
```

### Key Methods to Implement

1. **`_find_repo_root() -> Path`**
   - Search for `.git/` directory
   - Validate `mcp_server/` and `graphiti_core/` exist as children
   - Raise `InstallationError` if repo root not found

2. **`_validate_source_packages(repo_root: Path) -> None`**
   - Check `mcp_server/pyproject.toml` exists
   - Check `graphiti_core/__init__.py` exists
   - Raise `ValidationError` if packages incomplete

3. **`_deploy_package(source: Path, dest: Path) -> None`**
   - Use `shutil.copytree()` with `ignore` parameter
   - Apply exclusion filters from `EXCLUSIONS`
   - Preserve all `__init__.py` files
   - Log files copied for debugging

4. **`_verify_frozen_packages() -> None`**
   - Verify structural integrity (files/dirs exist)
   - Verify all `__init__.py` files present
   - Verify packages are importable
   - Raise `InstallationError` if verification fails

### Integration with GraphitiInstaller

The `_freeze_packages()` method will be called in `install()` workflow at step 5:

```python
def install(self, source_dir: Optional[Path] = None) -> InstallationResult:
    # ... (steps 1-4: validate, create dirs, create venv, install deps)

    self.progress.step(5, "Freezing packages")
    self._freeze_packages(source_dir)  # <-- New method

    # ... (steps 6-11: create wrappers, version info, config, service, verify)
```

---

## Destination Paths

**From GraphitiPaths analysis**:

- **Windows**: `C:\Users\{user}\AppData\Local\Programs\Graphiti\lib\`
- **macOS**: `~/Library/Application Support/Graphiti/lib/`
- **Linux**: `~/.local/share/graphiti/lib/`

**Frozen package layout**:
```
{install_dir}/
├── bin/
│   ├── .venv/              # Virtual environment (step 3)
│   ├── graphiti-mcp.exe    # Windows wrapper (step 6)
│   └── graphiti-mcp        # Unix wrapper (step 6)
└── lib/
    ├── mcp_server/         # <-- Frozen package 1 (step 5)
    │   ├── __init__.py
    │   ├── graphiti_mcp_server.py
    │   ├── daemon/
    │   ├── config/
    │   └── api/
    └── graphiti_core/      # <-- Frozen package 2 (step 5)
        ├── __init__.py
        ├── graphiti.py
        ├── driver/
        ├── embedder/
        └── llm_client/
```

---

## Edge Cases and Error Handling

1. **Repo root not found**:
   - Error: `InstallationError("Cannot find Graphiti repository root")`
   - User action: Set `GRAPHITI_REPO_PATH` environment variable

2. **Package incomplete** (missing critical files):
   - Error: `ValidationError("mcp_server package incomplete: missing daemon/")`
   - User action: Fix repository checkout

3. **Disk space exhausted during copy**:
   - Error: `InstallationError("Disk space exhausted during package freeze")`
   - Cleanup: Remove partial `lib/` directory
   - User action: Free disk space and retry

4. **Import verification fails**:
   - Error: `InstallationError("Frozen packages not importable: {error}")`
   - Cleanup: Remove `lib/` directory
   - User action: Report bug (this shouldn't happen if structural checks pass)

5. **Missing `__init__.py` in subdirectory**:
   - Error: `ValidationError("Missing __init__.py in {directory}")`
   - User action: Fix source package (add missing `__init__.py`)

---

## Testing Strategy (for Phase 5.t)

1. **Unit tests** (test individual methods):
   - `test_find_repo_root()` - Verify repo root detection
   - `test_validate_source_packages()` - Verify source validation
   - `test_deploy_package()` - Verify single package copy
   - `test_exclusion_filters()` - Verify `.pyc`, `__pycache__` excluded
   - `test_verify_init_files()` - Verify `__init__.py` check logic

2. **Integration tests** (test full freeze flow):
   - `test_freeze_packages_success()` - Full deployment succeeds
   - `test_freeze_packages_incomplete_source()` - Fails on bad source
   - `test_freeze_packages_verify_exclusions()` - `.venv` not copied
   - `test_frozen_import()` - Packages importable via `PYTHONPATH`

3. **Platform tests** (run on all platforms):
   - Windows: Test with `C:\Users\...\AppData\Local\Programs\Graphiti\lib\`
   - macOS: Test with `~/Library/Application Support/Graphiti/lib/`
   - Linux: Test with `~/.local/share/graphiti/lib/`

---

## Dependencies

**No blocking dependencies** - Story 4 (GraphitiInstaller class) is complete.

**Parallel work opportunities**:
- Story 6 (Version Tracking) can be implemented in parallel (independent)
- Story 10 (Bootstrap Module Invocation) depends on frozen packages being deployed

---

## Acceptance Criteria Status

✅ **(P0) Analyze package copy strategy (what to include/exclude)**
- Analyzed existing `PackageDeployer` class
- Identified dual-package deployment pattern
- Defined exclusion list with additions

✅ **Document files to exclude: .pyc, __pycache__, .git, .pytest_cache**
- Current exclusions: `.venv`, `__pycache__`, `*.pyc`, `tests`, `.pytest_cache`, `*.egg-info`, `.git`, `.gitignore`, `*.dist-info`
- Recommended additions: `.coverage`, `htmlcov/`, `.tox/`, `.mypy_cache/`, `*.so`, `*.pyd`, `*.egg`, `build/`, `dist/`

✅ **Determine how to find source packages (from repo or installed location)**
- Designed three-tier detection: `GRAPHITI_REPO_PATH` env → CWD → `__file__` relative
- Created `_find_repo_root()` method design for monorepo support

✅ **Design package verification mechanism (ensure all __init__.py present)**
- Designed three-tier verification:
  1. Structural check (files/dirs exist)
  2. Init file check (all packages have `__init__.py`)
  3. Import check (packages importable via `PYTHONPATH`)

---

## Next Steps (Implementation Phase 5.i)

1. Implement `_find_repo_root()` method
2. Implement `_validate_source_packages()` method
3. Implement `_deploy_package()` method (reuse PackageDeployer logic)
4. Extend `EXCLUSIONS` list with additional patterns
5. Implement `_verify_frozen_packages()` method
6. Integrate `_freeze_packages()` into `install()` workflow
7. Add comprehensive logging and error messages

**Estimated Complexity**: Medium (reusing existing PackageDeployer patterns)
**Estimated Implementation Time**: 2-3 hours
**Testing Time**: 1-2 hours (platform-specific testing required)
