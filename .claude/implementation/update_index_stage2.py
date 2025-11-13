#!/usr/bin/env python3
"""
Stage 2: Update Story 3 sub-stories, add dependencies, deprecate Story 4 sub-stories
"""
import re
from pathlib import Path

def update_index_stage2():
    index_path = Path(__file__).parent / "index.md"

    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Mark sub-stories 3.1-3.3 as completed
    for story_num in ['3.1', '3.2', '3.3']:
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

    # Add cross-cutting requirements note to sub-stories 3.1-3.3
    for story_num in ['3.1', '3.2', '3.3']:
        pattern = rf'(### Story {re.escape(story_num)}:.*?- \[x\] [^\n]+\n)'
        replacement = r'\1**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md (satisfied by parent Story 3)\n'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # 2. Add **Depends on**: Story 1 to Story 3
    content = re.sub(
        r'(### Story 3: File Monitoring\n\*\*Status\*\*: completed\n\*\*Claimed\*\*: 2025-11-13 11:00\n\*\*Completed\*\*: 2025-11-13 12:30\n)',
        r'\1**Depends on**: Story 1\n',
        content
    )

    # 3. Add **Depends on**: Story 2, Story 3 to Story 4
    content = re.sub(
        r'(### Story 4: Graphiti Integration \(REFACTORED\)\n\*\*Status\*\*: completed\n\*\*Original Completion\*\*: 2025-11-13 13:50\n\*\*Refactoring Completed\*\*: 2025-11-13 14:45\n)',
        r'\1**Depends on**: Story 2, Story 3\n',
        content
    )

    # 4. Mark Story 4.1 and 4.2 as deprecated
    for story_num in ['4.1', '4.2']:
        content = re.sub(
            rf'(### Story {re.escape(story_num)}:.*?\n\*\*Status\*\*: )unassigned',
            r'\1deprecated',
            content,
            flags=re.DOTALL
        )

    # Update Story 4.1 and 4.2 titles and add rationale
    content = re.sub(
        r'### Story 4\.1: Session Summarizer\n\*\*Status\*\*: deprecated\n\*\*Parent\*\*: Story 4\n\*\*Description\*\*: Use Graphiti LLM client to generate structured summaries\n\*\*Acceptance Criteria\*\*:\n- \[ \] SessionSummarizer class implemented\n- \[ \] Uses gpt-4\.1-mini for cost efficiency\n- \[ \] Prompt template matches handoff design\n- \[ \] Extracts all required fields \(objective, work, decisions, etc\.\)\n- \[ \] Handles errors gracefully',
        '''### Story 4.1: Session Summarizer (DEPRECATED - REFACTORED OUT)
**Status**: deprecated
**Parent**: Story 4
**Rationale**: Refactoring removed redundant LLM summarization layer. Graphiti's built-in LLM handles entity extraction and summarization automatically.
**Note**: May be reused for Story 2.3 (Configurable Filtering) if selective content summarization is needed.''',
        content
    )

    content = re.sub(
        r'### Story 4\.2: Graphiti Storage Integration\n\*\*Status\*\*: deprecated\n\*\*Parent\*\*: Story 4\n\*\*Description\*\*: Store session summaries as EpisodicNodes in Graphiti graph\n\*\*Acceptance Criteria\*\*:\n- \[ \] SessionStorage class implemented\n- \[ \] Sessions stored as EpisodicNodes\n- \[ \] Metadata includes token_count, mcp_tools_used, files_modified\n- \[ \] Relations created correctly \(preceded_by, continued_by\)\n- \[ \] Integration test with real Graphiti instance passes',
        '''### Story 4.2: Graphiti Storage Integration (DEPRECATED - REPLACED BY indexer.py)
**Status**: deprecated
**Parent**: Story 4
**Rationale**: Replaced by SessionIndexer class in indexer.py which provides direct episode addition without intermediate storage layer.''',
        content
    )

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("[OK] Stage 2 complete: Marked sub-stories 3.1-3.3 completed, added dependencies to Stories 3-4, deprecated Stories 4.1-4.2")

if __name__ == '__main__':
    update_index_stage2()
