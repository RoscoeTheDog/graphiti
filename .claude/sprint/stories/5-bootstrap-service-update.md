# Story 5: Bootstrap Service Update

**Status**: unassigned
**Created**: 2025-12-14 16:51

## Description

Update bootstrap service installation to use the dedicated venv Python path. Service templates must be dynamically generated at install time with no hardcoded paths in the repository.

## Acceptance Criteria

- [ ] (P0) Windows service uses `~/.graphiti/.venv/Scripts/python.exe`
- [ ] (P0) macOS launchd plist uses `~/.graphiti/.venv/bin/python`
- [ ] (P0) Linux systemd unit uses `~/.graphiti/.venv/bin/python`
- [ ] (P1) Service templates are dynamically generated (no hardcoded paths in repo)

## Dependencies

- Story 2: Package Installation to Dedicated Venv

## Implementation Notes

### Service Template Variables

Templates should use placeholders that are resolved at install time:
- `{{PYTHON_PATH}}` → `~/.graphiti/.venv/Scripts/python.exe` (Windows) or `~/.graphiti/.venv/bin/python` (Unix)
- `{{GRAPHITI_HOME}}` → `~/.graphiti/`
- `{{USER}}` → Current user (for systemd)

### Windows Service (NSSM)

```
nssm install GraphitiBootstrap "{{PYTHON_PATH}}"
nssm set GraphitiBootstrap AppParameters "-m mcp_server.daemon.bootstrap"
nssm set GraphitiBootstrap AppDirectory "{{GRAPHITI_HOME}}"
```

### macOS launchd plist

```xml
<key>ProgramArguments</key>
<array>
  <string>{{PYTHON_PATH}}</string>
  <string>-m</string>
  <string>mcp_server.daemon.bootstrap</string>
</array>
```

### Linux systemd unit

```ini
[Service]
ExecStart={{PYTHON_PATH}} -m mcp_server.daemon.bootstrap
User={{USER}}
WorkingDirectory={{GRAPHITI_HOME}}
```

## Related Stories

- Story 2: Package Installation to Dedicated Venv (dependency)
