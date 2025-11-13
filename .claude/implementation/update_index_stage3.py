#!/usr/bin/env python3
"""
Stage 3: Update Stories 5-8 with dependencies, new requirements, and cross-cutting requirements for sub-stories
"""
import re
from pathlib import Path

def update_index_stage3():
    index_path = Path(__file__).parent / "index.md"

    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add dependencies and default=enabled requirement to Story 5
    content = re.sub(
        r'(### Story 5: CLI Integration\n\*\*Status\*\*: unassigned\n)',
        r'\1**Depends on**: Story 1, Story 2, Story 3\n',
        content
    )

    # Update Story 5 description to include default=enabled
    content = re.sub(
        r'(### Story 5: CLI Integration\n\*\*Status\*\*: unassigned\n\*\*Depends on\*\*: Story 1, Story 2, Story 3\n\*\*Description\*\*: )Add global opt-in/out CLI commands for session tracking',
        r'\1Add global opt-in/out CLI commands for session tracking with default=enabled preference',
        content
    )

    # Update Story 5 acceptance criteria to include default=enabled
    content = re.sub(
        r'(### Story 5: CLI Integration.*?- \[ \] CLI commands implemented \(enable, disable, status\)\n)',
        r'\1- [ ] **Default configuration is enabled (opt-out model)** - NEW REQUIREMENT\n',
        content,
        flags=re.DOTALL
    )

    # Add migration note to Story 5 criteria
    content = re.sub(
        r'(### Story 5: CLI Integration.*?- \[ \] Opt-out instructions clear\n)',
        r'\1- [ ] Migration note for existing users (default behavior change)\n',
        content,
        flags=re.DOTALL
    )

    # 2. Add file path note and cross-cutting requirements to Story 5.1
    content = re.sub(
        r'(### Story 5\.1: CLI Commands\n\*\*Status\*\*: unassigned\n\*\*Parent\*\*: Story 5\n\*\*Description\*\*: Implement session tracking CLI commands\n)',
        r'\1**File**: `mcp_server/cli.py` or `graphiti_core/cli.py` (determine location based on existing CLI structure)\n',
        content
    )

    # Add file path note to criteria
    content = re.sub(
        r'(### Story 5\.1:.*?- \[ \] Commands integrated with existing MCP server CLI\n)',
        r'\1- [ ] File path explicitly documented in implementation\n**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md\n  - [ ] Type hints and comprehensive docstrings\n  - [ ] Error handling with logging\n  - [ ] >80% test coverage\n  - [ ] Documentation updated\n',
        content,
        flags=re.DOTALL
    )

    # 3. Add cross-cutting requirements to Story 5.2
    content = re.sub(
        r'(### Story 5\.2:.*?- \[ \] Validation works correctly\n)',
        r'\1- [ ] **Default value is enabled=true** - NEW REQUIREMENT\n**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md\n  - [ ] Type hints and Pydantic validation\n  - [ ] Error handling with logging\n  - [ ] Configuration uses unified system\n',
        content,
        flags=re.DOTALL
    )

    # 4. Add dependencies and update Story 6 with new MCP tool names
    content = re.sub(
        r'(### Story 6: MCP Tool Integration\n\*\*Status\*\*: unassigned\n)',
        r'\1**Depends on**: Story 3, Story 5\n',
        content
    )

    content = re.sub(
        r'(### Story 6: MCP Tool Integration\n\*\*Status\*\*: unassigned\n\*\*Depends on\*\*: Story 3, Story 5\n\*\*Description\*\*: )Add runtime toggle via MCP tool calls for per-session control',
        r'\1Add runtime toggle via MCP tool calls for per-session control with updated naming convention',
        content
    )

    # Update Story 6 MCP tool names in acceptance criteria
    content = re.sub(
        r'- \[ \] `track_session\(\)` MCP tool implemented',
        r'- [ ] `session_tracking_start()` MCP tool implemented (renamed from track_session)',
        content
    )
    content = re.sub(
        r'- \[ \] `stop_tracking_session\(\)` MCP tool implemented',
        r'- [ ] `session_tracking_stop()` MCP tool implemented (renamed from stop_tracking_session)',
        content
    )
    content = re.sub(
        r'- \[ \] `get_session_tracking_status\(\)` MCP tool implemented',
        r'- [ ] `session_tracking_status()` MCP tool implemented (renamed from get_session_tracking_status)',
        content
    )

    # 5. Add file path and cross-cutting requirements to Story 6.1
    content = re.sub(
        r'(### Story 6\.1: MCP Tool Implementation\n\*\*Status\*\*: unassigned\n\*\*Parent\*\*: Story 6\n\*\*Description\*\*: )Add MCP tools to graphiti_mcp_server\.py',
        r'\1Add MCP tools to graphiti_mcp_server.py with new naming convention\n**File**: `mcp_server/graphiti_mcp_server.py` (tool registration), handler module TBD',
        content
    )

    # Update Story 6.1 criteria with new names
    content = re.sub(
        r'(### Story 6\.1:.*?)- \[ \] All three MCP tools registered\n',
        r'\1- [ ] All three MCP tools registered with new names (session_tracking_start/stop/status)\n',
        content,
        flags=re.DOTALL
    )

    # Add file path note and cross-cutting requirements to Story 6.1
    content = re.sub(
        r'(### Story 6\.1:.*?- \[ \] Tools integrated with SessionTrackingService\n)',
        r'\1- [ ] Handler file path explicitly documented\n**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md\n  - [ ] Type hints and comprehensive docstrings\n  - [ ] Error handling with logging\n  - [ ] >80% test coverage\n  - [ ] Documentation: MCP_TOOLS.md updated\n',
        content,
        flags=re.DOTALL
    )

    # 6. Add cross-cutting requirements to Story 6.2
    content = re.sub(
        r'(### Story 6\.2:.*?- \[ \] force=True parameter works as expected\n)',
        r'\1**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md\n  - [ ] Type hints and comprehensive docstrings\n  - [ ] Error handling with logging\n  - [ ] >80% test coverage\n',
        content,
        flags=re.DOTALL
    )

    # 7. Add dependencies to Story 7
    content = re.sub(
        r'(### Story 7: Testing & Validation\n\*\*Status\*\*: unassigned\n)',
        r'\1**Depends on**: Story 1, Story 2, Story 3, Story 4, Story 5, Story 6\n',
        content
    )

    # 8. Add cross-cutting requirements to Story 7.1-7.4
    content = re.sub(
        r'(### Story 7\.1:.*?- \[ \] Agent spawning \(parent-child linkage\) tested\n)',
        r'\1**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md\n  - [ ] Platform-specific tests (Windows + Unix)\n  - [ ] >80% test coverage\n  - [ ] Error handling tested\n',
        content,
        flags=re.DOTALL
    )

    content = re.sub(
        r'(### Story 7\.2:.*?- \[ \] Token reduction confirmed \(90\+%\)\n)',
        r'\1**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md\n  - [ ] Error handling with logging\n  - [ ] Documentation: Cost analysis documented\n',
        content,
        flags=re.DOTALL
    )

    content = re.sub(
        r'(### Story 7\.3:.*?- \[ \] No performance degradation for MCP server\n)',
        r'\1**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md\n  - [ ] Performance benchmarks documented\n  - [ ] Error handling tested\n',
        content,
        flags=re.DOTALL
    )

    content = re.sub(
        r'(### Story 7\.4:.*?- \[ \] CONFIGURATION\.md updated\n)',
        r'\1**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md\n  - [ ] All documentation complete and reviewed\n  - [ ] Migration guide for existing users\n',
        content,
        flags=re.DOTALL
    )

    # 9. Add dependencies to Story 8
    content = re.sub(
        r'(### Story 8: Refinement & Launch\n\*\*Status\*\*: unassigned\n)',
        r'\1**Depends on**: Story 7\n',
        content
    )

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("[OK] Stage 3 complete: Updated Stories 5-8 with dependencies, new requirements, and cross-cutting requirements for all sub-stories")

if __name__ == '__main__':
    update_index_stage3()
