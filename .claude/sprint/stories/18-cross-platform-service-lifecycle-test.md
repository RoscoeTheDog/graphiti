# Story 18: Cross-Platform Service Lifecycle Test

**Status**: deferred
**Created**: 2025-12-25 02:02
**Phase**: 5 - End-to-End Testing

## Description

Test the complete service lifecycle (install, start, stop, restart, uninstall) on all platforms, ensuring clean uninstall leaves no artifacts.

**Deferral Note**: Service managers are functional and tested via unit tests. Dedicated E2E lifecycle tests deferred as service functionality is covered by Stories 14-16 install tests and individual service manager unit tests.

## Acceptance Criteria

### (d) Discovery Phase
- [ ] (P0) Define service lifecycle test scenarios
- [ ] Document expected behavior for each lifecycle operation
- [ ] Define "clean uninstall" criteria (no leftover files/tasks)
- [ ] Create platform-specific test checklists

### (i) Implementation Phase
- [ ] (P0) Test start/stop/restart cycle on Windows
- [ ] Test start/stop/restart cycle on macOS
- [ ] Test start/stop/restart cycle on Linux
- [ ] Test uninstall with --keep-config on all platforms
- [ ] Test uninstall without --keep-config on all platforms

### (t) Testing Phase
- [ ] (P0) Verify clean uninstall removes install directory
- [ ] Verify clean uninstall removes service registration
- [ ] Verify --keep-config preserves config directory
- [ ] Verify no orphaned processes after uninstall
- [ ] Verify reinstall works after uninstall

## Dependencies

- Story 14: Windows Fresh Install Test
- Story 15: macOS Fresh Install Test
- Story 16: Linux Fresh Install Test

## Implementation Notes

Clean uninstall should remove:
- %LOCALAPPDATA%\Programs\Graphiti\ (Windows)
- ~/Library/Application Support/Graphiti/ (macOS)
- ~/.local/share/graphiti/ (Linux)
- Service registrations (Task Scheduler task, LaunchAgent, systemd unit)

Optionally preserve:
- Config directory
- Log files
