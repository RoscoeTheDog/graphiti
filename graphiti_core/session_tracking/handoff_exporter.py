"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from graphiti_core.llm_client import LLMClient
from pydantic import BaseModel, Field

from .types import ConversationContext

logger = logging.getLogger(__name__)


class HandoffSummarySchema(BaseModel):
    """Structured schema for handoff file summaries."""

    objective: str = Field(description='Main goal of the session (1 sentence)')
    completed_tasks: list[str] = Field(description='List of completed tasks')
    blocked_items: list[str] = Field(
        default_factory=list, description='List of blockers preventing progress'
    )
    next_steps: list[str] = Field(description='List of next actions to take')
    files_modified: list[str] = Field(
        default_factory=list, description='List of file paths modified or created'
    )
    documentation_referenced: list[str] = Field(
        default_factory=list, description='List of documentation paths referenced'
    )
    key_decisions: list[str] = Field(
        default_factory=list, description='Important decisions made during the session'
    )
    mcp_tools_used: list[str] = Field(
        default_factory=list, description='MCP tools used during the session'
    )
    duration_estimate: str | None = Field(
        default=None, description='Estimated session duration (e.g., "2 hours")'
    )


@dataclass
class HandoffSummary:
    """Dataclass representing a handoff file summary."""

    sequence_number: int
    title: str
    slug: str
    objective: str
    completed_tasks: list[str]
    blocked_items: list[str]
    next_steps: list[str]
    files_modified: list[str]
    documentation_referenced: list[str]
    key_decisions: list[str]
    mcp_tools_used: list[str]
    duration_estimate: str | None
    created_at: datetime
    status: str = 'ACTIVE'

    def to_markdown(self) -> str:
        """Convert summary to markdown format for handoff file."""
        created_str = self.created_at.strftime('%Y-%m-%d %H:%M')

        markdown = f"""# Session {self.sequence_number:03d}: {self.title}

**Status**: {self.status}
**Created**: {created_str}
**Objective**: {self.objective}

---

## Completed

"""
        for task in self.completed_tasks:
            markdown += f'- {task}\n'

        markdown += '\n---\n\n## Blocked\n\n'
        if self.blocked_items:
            for item in self.blocked_items:
                markdown += f'- {item}\n'
        else:
            markdown += 'None\n'

        markdown += '\n---\n\n## Next Steps\n\n'
        for step in self.next_steps:
            markdown += f'- {step}\n'

        if self.key_decisions:
            markdown += '\n---\n\n## Key Decisions\n\n'
            for decision in self.key_decisions:
                markdown += f'- {decision}\n'

        markdown += '\n---\n\n## Context\n\n'
        if self.files_modified:
            markdown += '**Files Modified/Created**:\n'
            for file_path in self.files_modified:
                markdown += f'- {file_path}\n'
            markdown += '\n'

        if self.documentation_referenced:
            markdown += '**Documentation Referenced**:\n'
            for doc_path in self.documentation_referenced:
                markdown += f'- {doc_path}\n'
            markdown += '\n'

        if self.mcp_tools_used:
            markdown += '**MCP Tools Used**:\n'
            for tool in self.mcp_tools_used:
                markdown += f'- {tool}\n'
            markdown += '\n'

        markdown += '---\n\n'
        if self.duration_estimate:
            markdown += f'**Session Duration**: {self.duration_estimate}\n'

        return markdown


class HandoffExporter:
    """
    OPTIONAL: Export session summaries to user-friendly handoff markdown files.

    This is a convenience feature for users who want human-readable handoff files.
    It is NOT part of the core session tracking flow - the graph is the source of truth.

    Architecture Notes:
    - NOT called automatically by session tracking
    - Invoked explicitly via CLI: `graphiti session export-handoff`
    - Uses LLM to create structured summaries optimized for human readability
    - Separate from core flow (graph indexing via SessionIndexer)

    Cost Consideration:
    - Adds extra LLM call (~$0.03-$0.10 per export)
    - Only incurred when user explicitly exports
    - Not part of automatic session tracking costs
    """

    HANDOFF_PROMPT = """You are analyzing a Claude Code session to create a handoff summary for the next developer or agent.

Session Context:
- Total messages: {message_count}
- User messages: {user_count}
- Agent messages: {agent_count}
- Tool calls: {tool_count}

Session Content (filtered):
{filtered_content}

Extract the following information for a handoff document:

1. **Objective**: What was the main goal of this session? (1 sentence)

2. **Completed Tasks**: What specific tasks were accomplished? (list)

3. **Blocked Items**: What blockers or issues prevented progress? (list, empty if none)

4. **Next Steps**: What should be done next to continue this work? (list)

5. **Files Modified**: Which file paths were created or modified? Extract from Write/Edit tool calls.

6. **Documentation Referenced**: Which documentation paths were read or referenced?

7. **Key Decisions**: What important decisions were made during the session?

8. **MCP Tools Used**: List unique MCP tools used (e.g., serena, graphiti-memory, claude-context).

9. **Duration Estimate**: Estimate session duration based on message count (e.g., "1-2 hours").

Focus on actionable information that helps the next person continue work efficiently.
"""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize the HandoffExporter.

        Args:
            llm_client: LLM client for generating summaries
        """
        self.llm_client = llm_client
        logger.info('HandoffExporter initialized (optional export feature)')

    async def export_handoff(
        self,
        context: ConversationContext,
        filtered_content: str,
        sequence_number: int,
        output_path: Path,
    ) -> Path:
        """
        Generate a handoff markdown file from session content.

        NOTE: This is an optional feature, not part of core session tracking.
        The graph (via SessionIndexer) is the source of truth for session data.

        Args:
            context: ConversationContext with session metadata
            filtered_content: Filtered session content (from SessionFilter)
            sequence_number: Session sequence number for handoff file
            output_path: Path to write handoff markdown file

        Returns:
            Path to created handoff file

        Raises:
            Exception: If LLM call fails or file write fails

        Example:
            >>> exporter = HandoffExporter(llm_client)
            >>> handoff_path = await exporter.export_handoff(
            ...     context=context,
            ...     filtered_content=filtered_session,
            ...     sequence_number=5,
            ...     output_path=Path(".claude/handoff/s005-auth-fix.md")
            ... )
            >>> print(f"Handoff file created: {handoff_path}")
        """
        logger.info(
            f'Exporting handoff file for session with {len(context.messages)} messages '
            f'(optional export, not part of core tracking)'
        )

        try:
            # Count message types
            user_count = sum(1 for m in context.messages if m.role == 'user')
            agent_count = sum(1 for m in context.messages if m.role == 'assistant')
            tool_count = sum(len(m.tool_calls) for m in context.messages if m.tool_calls)

            # Build prompt
            prompt = self.HANDOFF_PROMPT.format(
                message_count=len(context.messages),
                user_count=user_count,
                agent_count=agent_count,
                tool_count=tool_count,
                filtered_content=filtered_content[:15000],  # Limit to avoid token overflow
            )

            # Call LLM with structured output
            logger.debug('Calling LLM for handoff summary extraction')
            response = await self.llm_client.generate_response(
                messages=[{'role': 'user', 'content': prompt}],
                response_model=HandoffSummarySchema,
            )

            # Extract title from objective
            title = response.objective[:50].strip()
            if title.endswith('.'):
                title = title[:-1]

            # Generate slug
            slug = self._generate_slug(title)

            # Create HandoffSummary
            summary = HandoffSummary(
                sequence_number=sequence_number,
                title=title,
                slug=slug,
                objective=response.objective,
                completed_tasks=response.completed_tasks,
                blocked_items=response.blocked_items,
                next_steps=response.next_steps,
                files_modified=response.files_modified,
                documentation_referenced=response.documentation_referenced,
                key_decisions=response.key_decisions,
                mcp_tools_used=response.mcp_tools_used,
                duration_estimate=response.duration_estimate,
                created_at=datetime.now(),
            )

            # Write markdown file
            markdown = summary.to_markdown()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown, encoding='utf-8')

            logger.info(f'Handoff file exported: {output_path}')
            return output_path

        except Exception as e:
            logger.error(f'Error exporting handoff file: {e}', exc_info=True)
            raise

    def _generate_slug(self, title: str) -> str:
        """
        Generate a URL-safe slug from title.

        Args:
            title: Title to convert to slug

        Returns:
            Slug string (lowercase, hyphens, max 40 chars)
        """
        import re

        slug = title.lower().replace(' ', '-')
        slug = re.sub(r'\b(a|an|the)\b-?', '', slug)
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        return slug[:40]
