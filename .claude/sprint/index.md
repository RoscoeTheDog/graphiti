# Implementation Sprint: Per-User Daemon Architecture v2.1

**Version**: v2.1.0
**Created**: 2025-12-25 02:02
**Base Branch**: dev
**Sprint Branch**: sprint/per-user-daemon-v21
**Status**: Active

## Sprint Goal

Implement a professional-grade, per-user daemon architecture for the Graphiti MCP server following industry conventions (Ollama, VS Code pattern). This includes frozen package installation in platform-appropriate directories, complete separation of executables/config/data, repository-independent operation, and version tracking for upgrades.

## Key Deliverables

1. **Platform-aware path resolution** - New paths.py module with Windows/macOS/Linux support
2. **Professional installer** - GraphitiInstaller class with frozen package deployment
3. **Updated service managers** - Task Scheduler, launchd, systemd using new paths
4. **Migration support** - v2.0 to v2.1 migration with config preservation
5. **Cross-platform testing** - End-to-end tests on all platforms
6. **Updated documentation** - Installation guide and configuration docs

## Stories

### Phase 1: Path Infrastructure

#### Story 1: Create Platform-Aware Path Resolution Module
**Status**: completed
**See**: [stories/1-create-platform-aware-path-resolution.md](stories/1-create-platform-aware-path-resolution.md)
- Discovery (1.d): completed
- Implementation (1.i): completed
- Testing (1.t): completed

#### Story 2: Migrate Daemon Modules to New Path System
**Status**: unassigned
**See**: [stories/2-migrate-daemon-modules-to-new-paths.md](stories/2-migrate-daemon-modules-to-new-paths.md)
- Discovery (2.d): completed
- Implementation (2.i): completed
- Testing (2.t): blocked (85.8% pass rate - hardcoded paths remain)

#### Story 3: Path Resolution Test Suite
**Status**: completed
**See**: [stories/3-path-resolution-test-suite.md](stories/3-path-resolution-test-suite.md)
- Discovery (3.d): completed
- Implementation (3.i): completed
- Testing (3.t): completed

### Phase 2: Installer Overhaul

#### Story 4: Create GraphitiInstaller Class
**Status**: completed
**See**: [stories/4-create-graphiti-installer-class.md](stories/4-create-graphiti-installer-class.md)
- Discovery (4.d): completed
- Implementation (4.i): completed
- Testing (4.t): completed

#### Story 5: Implement Frozen Package Deployment
**Status**: unassigned
**See**: [stories/5-implement-frozen-package-deployment.md](stories/5-implement-frozen-package-deployment.md)

#### Story 6: Implement Version Tracking
**Status**: unassigned
**See**: [stories/6-implement-version-tracking.md](stories/6-implement-version-tracking.md)

### Phase 3: Service Manager Updates

#### Story 7: Update WindowsTaskSchedulerManager
**Status**: unassigned
**See**: [stories/7-update-windows-task-scheduler-manager.md](stories/7-update-windows-task-scheduler-manager.md)

#### Story 8: Update LaunchdServiceManager (macOS)
**Status**: unassigned
**See**: [stories/8-update-launchd-service-manager.md](stories/8-update-launchd-service-manager.md)

#### Story 9: Update SystemdServiceManager (Linux)
**Status**: unassigned
**See**: [stories/9-update-systemd-service-manager.md](stories/9-update-systemd-service-manager.md)

#### Story 10: Fix Bootstrap Module Invocation
**Status**: unassigned
**See**: [stories/10-fix-bootstrap-module-invocation.md](stories/10-fix-bootstrap-module-invocation.md)

### Phase 4: Migration

#### Story 11: Implement v2.0 Installation Detection
**Status**: completed
**See**: [stories/11-implement-v20-installation-detection.md](stories/11-implement-v20-installation-detection.md)
- Discovery (11.d): completed
- Implementation (11.i): completed
- Testing (11.t): completed

#### Story 12: Implement Config Migration
**Status**: unassigned
**See**: [stories/12-implement-config-migration.md](stories/12-implement-config-migration.md)

#### Story 13: Implement Old Installation Cleanup
**Status**: unassigned
**See**: [stories/13-implement-old-installation-cleanup.md](stories/13-implement-old-installation-cleanup.md)

### Phase 5: End-to-End Testing

#### Story 14: Windows Fresh Install Test
**Status**: unassigned
**See**: [stories/14-windows-fresh-install-test.md](stories/14-windows-fresh-install-test.md)

#### Story 15: macOS Fresh Install Test
**Status**: unassigned
**See**: [stories/15-macos-fresh-install-test.md](stories/15-macos-fresh-install-test.md)

#### Story 16: Linux Fresh Install Test
**Status**: unassigned
**See**: [stories/16-linux-fresh-install-test.md](stories/16-linux-fresh-install-test.md)

#### Story 17: Windows v2.0 to v2.1 Migration Test
**Status**: unassigned
**See**: [stories/17-windows-v20-to-v21-migration-test.md](stories/17-windows-v20-to-v21-migration-test.md)

#### Story 18: Cross-Platform Service Lifecycle Test
**Status**: unassigned
**See**: [stories/18-cross-platform-service-lifecycle-test.md](stories/18-cross-platform-service-lifecycle-test.md)

### Phase 6: Documentation

#### Story 19: Update Installation Guide
**Status**: unassigned
**See**: [stories/19-update-installation-guide.md](stories/19-update-installation-guide.md)

#### Story 20: Update Configuration Documentation
**Status**: unassigned
**See**: [stories/20-update-configuration-documentation.md](stories/20-update-configuration-documentation.md)

---

## Architecture Reference

See `.claude/implementation/DAEMON_ARCHITECTURE_SPEC_v2.1.md` for full specification.

### v2.1 Directory Structure (Windows)

```
%LOCALAPPDATA%\Programs\Graphiti\     <- Executables + frozen libs
├── bin\
├── lib\mcp_server\, lib\graphiti_core\
├── VERSION
└── INSTALL_INFO

%LOCALAPPDATA%\Graphiti\              <- Config + runtime
├── config\graphiti.config.json
├── logs\
└── data\
```

---

*Generated by /sprint:CREATE_SPRINT v4.4.0*
