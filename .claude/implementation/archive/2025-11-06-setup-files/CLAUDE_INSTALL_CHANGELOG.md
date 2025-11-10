# CLAUDE_INSTALL.md - Changelog

All notable changes to installation guide. Adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Version Format

**MAJOR.MINOR.PATCH**:
- **MAJOR**: Breaking (new prereq, removed option, breaking change)
- **MINOR**: New features, backward-compat (new option, new optional dep)
- **PATCH**: Fixes, clarifications (typos, better explanations, validation updates)

---

## [Unreleased]

Planned:
- [ ] Docker Compose option
- [ ] Validate local DB on Linux
- [ ] M1/M2 Mac troubleshooting

---

## [1.0.0] - [YYYY-MM-DD]

### Initial Release

**Summary**: Initial install guide for [PROJECT_NAME]

#### Added
- Install guide structure
- Prereq: Python [VERSION], Git
- [COMPONENT] install options:
  - ✅ Cloud (W11, M14)
  - ⚠️ Local (needs validation)
  - ✅ Docker (all platforms)
- Env config guide
- API keys: [LLM_1], [LLM_2]
- Validation script
- Troubleshooting
- Platform notes (W, M, L)

#### Validation
- ✅ Python [VERSION]: W11, M14, U22.04
- ✅ [COMPONENT] cloud: W11, M14
- ✅ [COMPONENT] Docker: W11, M14, U22.04
- ⚠️ [COMPONENT] local: Needs testing
- ✅ [LLM_1]: All platforms
- ⚠️ [LLM_2]: Experimental

---

## Example Entries

### MINOR (New Feature)

## [1.1.0] - 2025-11-15

### Added
- Redis caching option
- Redis install (W, M, L)
- Env var: `REDIS_URL` (optional)
- Validation script checks Redis

### Changed
- Prereq: Redis as optional
- Troubleshooting: Redis-specific

### Validation
- ✅ Redis Docker: W11, M14, U22.04
- ⚠️ Redis local: Needs testing W

---

### PATCH (Fix)

## [1.0.1] - 2025-10-28

### Fixed
- DB connection string typo
- Broken [LLM] docs link
- Clarified venv activation (W PowerShell)

### Changed
- Formatting in Env Config section

---

### MAJOR (Breaking)

## [2.0.0] - 2025-12-01

### BREAKING
- **Python3.11+ required** (was 3.10+)
  - Reason: Deps require 3.11+ for async
  - Impact: Users on 3.10 must upgrade

### Migration
1. Upgrade Python:
   ```bash
   python --version  # Check current
   # Install Python3.11+ (see Prereq)
   ```
2. Recreate venv:
   ```bash
   deactivate
   rm -rf venv              # M/L
   rmdir /s venv            # W
   python3.11 -m venv venv
   source venv/bin/activate # M/L
   venv\Scripts\activate    # W
   ```
3. Reinstall:
   ```bash
   pip install -r requirements.txt
   ```

### Added
- Python3.11+ async features
- Platform validation with 3.11

### Removed
- Python3.10 support
- `LEGACY_API_MODE` env var

### Validation
- ✅ Python3.11: All platforms
- ✅ Python3.12: W11, M14

---

## Version Decision

```
breaks-setup?           → MAJOR
adds-feature?(compat)   → MINOR
fixes|clarifies?        → PATCH
```

**Examples**:
- MAJOR: Python ver change, remove option, rename env-vars, config structure change
- MINOR: New option, new optional dep, new env-var(optional), enhanced instructions
- PATCH: Typos, clarifications, validation badge updates, broken link fixes

---

## Entry Structure

**Sections** (use relevant):
- `Added` - New features, options, instructions
- `Changed` - Updates to existing
- `Deprecated` - Soon removed (with migration)
- `Removed` - Removed features, options
- `Fixed` - Bug fixes, corrections
- `Security` - Security changes
- `BREAKING CHANGES` - Requires user action
- `Migration Guide` - Upgrade instructions
- `Validation Status` - Updated badges

**Good**:
- ✅ "Added Redis caching with Docker install"
- ✅ "Changed Python 3.10+ to 3.11+ (BREAKING)"
- ✅ "Fixed Neo4j connection string in Aura section"

**Bad**:
- ❌ "Updated stuff"
- ❌ "Fixed things"
- ❌ "Changes to installation"

---

**Template**: v1.1.0 | **Created**: 2025-10-25 | **Purpose**: Track install changes with semver

**Note**: AI agents auto-update per `CLAUDE_README.md` policies
