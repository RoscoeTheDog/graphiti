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
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from graphiti_core.llm_client import LLMClient

from .types import ConversationContext

logger = logging.getLogger(__name__)


class SessionSummarySchema(BaseModel):
    """Structured schema for session summaries."""

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
    token_count: int | None = Field(default=None, description='Total tokens used in session')
    duration_estimate: str | None = Field(
        default=None, description='Estimated session duration (e.g., "2 hours")'
    )


@dataclass
class SessionSummary:
    """Dataclass representing a processed session summary."""

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
    token_count: int | None
    duration_estimate: str | None
    created_at: datetime
    status: str = 'ACTIVE'

    def to_markdown(self) -> str:
        """Convert summary to markdown format for file storage."""
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
        if self.token_count:
            markdown += f'**Token Usage**: {self.token_count:,}\n'

        return markdown

    def to_metadata(self) -> dict[str, Any]:
        """Convert summary to metadata dict for Graphiti storage."""
        return {
            'sequence_number': self.sequence_number,
            'slug': self.slug,
            'objective': self.objective,
            'status': self.status,
            'files_count': len(self.files_modified),
            'completed_count': len(self.completed_tasks),
            'blocked_count': len(self.blocked_items),
            'token_count': self.token_count,
            'duration_estimate': self.duration_estimate,
            'mcp_tools_used': self.mcp_tools_used,
            'created_at': self.created_at.isoformat(),
        }


class SessionSummarizer:
    """
    Generates structured session summaries using LLM.

    Uses the Graphiti LLM client to process session data and extract
    key information like objectives, completed tasks, blockers, and next steps.
    """

    SUMMARIZATION_PROMPT = """You are analyzing a Claude Code session to create a structured handoff summary.

Session Context:
- Total messages: {message_count}
- User messages: {user_count}
- Agent messages: {agent_count}
- Tool calls: {tool_count}
- Total tokens: {token_count}

Session Content (filtered):
{filtered_content}

Extract the following information:

1. **Objective**: What was the main goal of this session? (1 sentence)

2. **Completed Tasks**: What specific tasks were accomplished? (list)

3. **Blocked Items**: What blockers or issues prevented progress? (list, empty if none)

4. **Next Steps**: What should be done next to continue this work? (list)

5. **Files Modified**: Which file paths were created or modified? Extract from Write/Edit tool calls.

6. **Documentation Referenced**: Which documentation paths were read or referenced?

7. **Key Decisions**: What important decisions were made during the session?

8. **MCP Tools Used**: List unique MCP tools used (e.g., serena, graphiti-memory, claude-context).

9. **Duration Estimate**: Estimate session duration based on message count (e.g., "1-2 hours").

Focus on actionable information that helps the next session continue work efficiently.
"""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize the SessionSummarizer.

        Args:
            llm_client: LLM client for generating summaries (uses gpt-4.1-mini for cost efficiency)
        """
        self.llm_client = llm_client
        logger.info('SessionSummarizer initialized')

    async def summarize_session(
        self,
        context: ConversationContext,
        filtered_content: str,
        sequence_number: int,
    ) -> SessionSummary:
        """
        Generate a structured summary of a session.

        Args:
            context: ConversationContext with session metadata
            filtered_content: Filtered session content (from SessionFilter)
            sequence_number: Session sequence number for handoff file

        Returns:
            SessionSummary with all extracted fields

        Raises:
            Exception: If LLM call fails or response parsing fails
        """
        logger.info(f'Summarizing session with {len(context.messages)} messages')

        try:
            # Count message types
            user_count = sum(1 for m in context.messages if m.role == 'user')
            agent_count = sum(1 for m in context.messages if m.role == 'assistant')
            tool_count = sum(len(m.tool_calls) for m in context.messages if m.tool_calls)

            # Build prompt
            prompt = self.SUMMARIZATION_PROMPT.format(
                message_count=len(context.messages),
                user_count=user_count,
                agent_count=agent_count,
                tool_count=tool_count,
                token_count=context.total_tokens,
                filtered_content=filtered_content[:15000],  # Limit content to avoid token overflow
            )

            # Call LLM with structured output
            logger.debug('Calling LLM for structured summary extraction')
            response = await self.llm_client.generate_response(
                messages=[{'role': 'user', 'content': prompt}],
                response_model=SessionSummarySchema,
            )

            # Extract title from objective (first 50 chars, title case)
            title = response.objective[:50].strip()
            if title.endswith('.'):
                title = title[:-1]

            # Generate slug from title
            slug = self._generate_slug(title)

            # Create SessionSummary
            summary = SessionSummary(
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
                token_count=response.token_count or context.total_tokens,
                duration_estimate=response.duration_estimate,
                created_at=datetime.now(timezone.utc),
            )

            logger.info(
                f'Session summarized: {summary.title} '
                f'({len(summary.completed_tasks)} tasks completed, '
                f'{len(summary.blocked_items)} blocked)'
            )
            return summary

        except Exception as e:
            logger.error(f'Error summarizing session: {e}', exc_info=True)
            raise

    def _generate_slug(self, title: str) -> str:
        """
        Generate a URL-safe slug from title.

        Rules:
        - Lowercase
        - Replace spaces with hyphens
        - Remove articles (a, an, the)
        - Max 40 characters
        - Remove special characters

        Args:
            title: Title to convert to slug

        Returns:
            Slug string
        """
        import re

        # Lowercase and replace spaces with hyphens
        slug = title.lower().replace(' ', '-')

        # Remove articles
        slug = re.sub(r'\b(a|an|the)\b-?', '', slug)

        # Remove special characters (keep alphanumeric and hyphens)
        slug = re.sub(r'[^a-z0-9-]', '', slug)

        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        # Limit to 40 characters
        return slug[:40]
