#!/usr/bin/env python3
"""
Script to apply audit remediation changes to index.md
"""
import re
from pathlib import Path

def update_index():
    index_path = Path(__file__).parent / "index.md"

    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update header metadata
    content = re.sub(
        r'(\*\*Created\*\*: 2025-11-13 09:30\n)',
        r'\1**Updated**: 2025-11-13 (Audit remediation)\n',
        content
    )

    # 2. Update cross-cutting requirements statement
    content = content.replace(
        '**ALL stories must satisfy',
        '**ALL stories and sub-stories must satisfy'
    )

    # 3. Mark sub-stories 1.1-1.3 as completed
    for story_num in ['1.1', '1.2', '1.3']:
        content = re.sub(
            rf'(### Story {re.escape(story_num)}:.*?\n\*\*Status\*\*: )unassigned',
            r'\1completed',
            content,
            flags=re.DOTALL
        )
        # Update checkboxes to checked
        section_pattern = rf'(### Story {re.escape(story_num)}:.*?)(###|\Z)'
        match = re.search(section_pattern, content, re.DOTALL)
        if match:
            section = match.group(1)
            section = section.replace('- [ ]', '- [x]')
            content = content.replace(match.group(1), section)

    # Add cross-cutting requirements note to sub-stories 1.1-1.3
    for story_num in ['1.1', '1.2', '1.3']:
        pattern = rf'(### Story {re.escape(story_num)}:.*?- \[x\] [^\n]+\n)'
        replacement = r'\1**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md (satisfied by parent Story 1)\n'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # 4. Mark sub-stories 2.1-2.2 as completed
    for story_num in ['2.1', '2.2']:
        content = re.sub(
            rf'(### Story {re.escape(story_num)}:.*?\n\*\*Status\*\*: )unassigned',
            r'\1completed',
            content,
            flags=re.DOTALL
        )
        section_pattern = rf'(### Story {re.escape(story_num)}:.*?)(###|\Z)'
        match = re.search(section_pattern, content, re.DOTALL)
        if match:
            section = match.group(1)
            section = section.replace('- [ ]', '- [x]')
            content = content.replace(match.group(1), section)

    # Add cross-cutting requirements note to sub-stories 2.1-2.2
    for story_num in ['2.1', '2.2']:
        pattern = rf'(### Story {re.escape(story_num)}:.*?- \[x\] [^\n]+\n)'
        replacement = r'\1**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md (satisfied by parent Story 2)\n'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # 5. Add NEW Story 2.3 after Story 2.2
    story_23 = '''
### Story 2.3: Configurable Filtering System (NEW - REMEDIATION)
**Status**: unassigned
**Parent**: Story 2
**Depends on**: Story 2
**Description**: Add configurable filtering rules for opt-in/opt-out per message type with multiple content modes (full/omit/summary)
**Rationale**: Existing filter.py has fixed rules. User requires flexible configuration to control what gets tracked and how content is processed (full preservation, omission, or LLM summarization).
**File**: `graphiti_core/session_tracking/filter_config.py` (new), `filter.py` (modify)
**Acceptance Criteria**:
- [ ] FilterConfig dataclass created with per-type settings:
  - [ ] `tool_calls: bool` - Track tool call structure (default: true)
  - [ ] `tool_content: ContentMode` - Tool result content mode (default: "summary")
  - [ ] `user_messages: ContentMode` - User message content mode (default: "full")
  - [ ] `agent_messages: ContentMode` - Agent message content mode (default: "full")
  - [ ] ContentMode enum: "full" | "omit" | "summary"
- [ ] Configuration integrated into SessionTrackingConfig in unified_config.py
- [ ] SessionFilter.filter_messages() updated to use configuration
- [ ] Summarizer class integration for ContentMode.SUMMARY (reuse existing summarizer.py or create lightweight version)
- [ ] Unit tests for all configuration combinations (9+ test scenarios)
- [ ] Documentation: CONFIGURATION.md updated with filtering options
- [ ] **Cross-cutting requirements satisfied** (see CROSS_CUTTING_REQUIREMENTS.md):
  - [ ] Type hints and Pydantic models for configuration
  - [ ] Error handling with logging (invalid config)
  - [ ] >80% test coverage
  - [ ] Configuration uses unified system
  - [ ] Documentation updated

**Implementation Notes**:
- Reuse existing summarizer.py if present, or create minimal LLM summarization for ContentMode.SUMMARY
- Default configuration maintains current behavior (user/agent full, tool content summarized)
- Allow users to opt-out of specific message types entirely with ContentMode.OMIT
'''

    # Insert Story 2.3 after Story 2.2
    content = re.sub(
        r'(### Story 2\.2: Tool Output Summarization.*?- \[x\] Summary format is consistent and informative\n\*\*Cross-cutting requirements\*\*: See CROSS_CUTTING_REQUIREMENTS\.md \(satisfied by parent Story 2\)\n)',
        r'\1' + story_23,
        content,
        flags=re.DOTALL
    )

    # Write back
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ Stage 1 complete: Updated metadata, marked sub-stories 1.1-1.3, 2.1-2.2 completed, added Story 2.3")

if __name__ == '__main__':
    update_index()
