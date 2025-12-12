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


class DecisionRecord(BaseModel):
    """Structured record of an important decision made during a session."""

    decision: str = Field(description='The decision that was made')
    rationale: str = Field(description='Why this decision was made')
    alternatives: list[str] | None = Field(
        default=None, description='Alternative options considered'
    )


class ErrorResolution(BaseModel):
    """Structured record of an error that was resolved during a session."""

    error: str = Field(description='The error that occurred')
    root_cause: str = Field(description='Root cause analysis')
    fix: str = Field(description='How the error was fixed')
    verification: str = Field(description='How the fix was verified')


class ConfigChange(BaseModel):
    """Structured record of a configuration change made during a session."""

    file: str = Field(description='Configuration file path')
    setting: str = Field(description='Setting name that was changed')
    change: str = Field(description='Description of change (e.g., "60 -> 3600")')
    reason: str = Field(description='Why this change was made')


class TestResults(BaseModel):
    """Structured record of test execution results."""

    framework: str = Field(description='Test framework used (e.g., pytest, jest)')
    passed: int = Field(description='Number of tests passed')
    failed: int = Field(description='Number of tests failed')
    coverage: float | None = Field(
        default=None, description='Code coverage percentage (0-100)'
    )


class SessionSummarySchema(BaseModel):
    """Structured schema for session summaries."""

    objective: str = Field(description='Main goal of the session (1 sentence)')
    activity_profile: str | None = Field(
        default=None, description='Activity profile describing dominant work type (e.g., "fixing (0.80), testing (0.50)")'
    )
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
    key_decisions: list[DecisionRecord] = Field(
        default_factory=list, description='Important decisions made during the session with rationale'
    )
    errors_resolved: list[ErrorResolution] = Field(
        default_factory=list, description='Errors encountered and how they were resolved'
    )
    config_changes: list[ConfigChange] = Field(
        default_factory=list, description='Configuration changes made during the session'
    )
    test_results: TestResults | None = Field(
        default=None, description='Test execution results if tests were run'
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
    activity_profile: str | None
    completed_tasks: list[str]
    blocked_items: list[str]
    next_steps: list[str]
    files_modified: list[str]
    documentation_referenced: list[str]
    key_decisions: list[DecisionRecord]
    errors_resolved: list[ErrorResolution]
    config_changes: list[ConfigChange]
    test_results: TestResults | None
    mcp_tools_used: list[str]
    token_count: int | None
    duration_estimate: str | None
    created_at: datetime
    status: str = 'ACTIVE'

    def to_markdown(self) -> str:
        """Convert summary to markdown format for file storage."""
        created_str = self.created_at.strftime('%Y-%m-%d %H:%M')

        # Build header with optional activity profile
        header_lines = [
            f'# Session {self.sequence_number:03d}: {self.title}',
            '',
            f'**Status**: {self.status}',
            f'**Created**: {created_str}',
        ]

        if self.activity_profile:
            header_lines.append(f'**Activity Profile**: {self.activity_profile}')
            header_lines.append(f'**Outcome**: {self.status.lower()}')
            header_lines.append('')
            header_lines.append('## Objective')
            header_lines.append(self.objective)
        else:
            header_lines.append(f'**Objective**: {self.objective}')

        markdown = '\n'.join(header_lines) + '\n\n---\n\n## Completed\n\n'
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
                markdown += f'- **{decision.decision}**\n'
                markdown += f'  - Rationale: {decision.rationale}\n'
                if decision.alternatives:
                    markdown += f'  - Alternatives: {", ".join(decision.alternatives)}\n'

        if self.errors_resolved:
            markdown += '\n---\n\n## Errors Resolved\n\n'
            for err in self.errors_resolved:
                markdown += f'### {err.error}\n'
                markdown += f'- **Root Cause**: {err.root_cause}\n'
                markdown += f'- **Fix**: {err.fix}\n'
                markdown += f'- **Verification**: {err.verification}\n\n'

        if self.config_changes:
            markdown += '\n---\n\n## Configuration Changes\n\n'
            markdown += '| File | Setting | Change | Reason |\n'
            markdown += '|------|---------|--------|--------|\n'
            for config in self.config_changes:
                # Escape pipe characters in cell content
                file = config.file.replace('|', '\\|')
                setting = config.setting.replace('|', '\\|')
                change = config.change.replace('|', '\\|')
                reason = config.reason.replace('|', '\\|')
                markdown += f'| {file} | {setting} | {change} | {reason} |\n'

        if self.test_results:
            markdown += '\n---\n\n## Test Results\n\n'
            total = self.test_results.passed + self.test_results.failed
            markdown += f'- **Framework**: {self.test_results.framework}\n'
            markdown += f'- **Results**: {self.test_results.passed}/{total} passed'
            if self.test_results.failed > 0:
                markdown += f' ({self.test_results.failed} failed)'
            markdown += '\n'
            if self.test_results.coverage is not None:
                markdown += f'- **Coverage**: {self.test_results.coverage:.1f}%\n'

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

2. **Activity Profile** (optional): What type of work was primarily done?
   - Example: "fixing (0.80), configuring (0.70), testing (0.50)"
   - Leave null if unclear

3. **Completed Tasks**: What specific tasks were accomplished? (list)

4. **Blocked Items**: What blockers or issues prevented progress? (list, empty if none)

5. **Next Steps**: What should be done next to continue this work? (list)

6. **Files Modified**: Which file paths were created or modified? Extract from Write/Edit tool calls.

7. **Documentation Referenced**: Which documentation paths were read or referenced?

8. **Key Decisions**: What important decisions were made during the session?
   For each decision, provide:
   - decision: The actual decision (e.g., "Used RS256 over HS256 for JWT signing")
   - rationale: Why this was chosen (e.g., "RS256 is more secure for production")
   - alternatives: Other options considered (e.g., ["HS256", "EdDSA"]) or null if none

9. **Errors Resolved**: What errors were encountered and fixed during the session?
   For each error, provide:
   - error: The error message or description
   - root_cause: What caused the error
   - fix: How it was resolved
   - verification: How the fix was verified to work

10. **Configuration Changes** (optional): Were any configuration files modified?
    For each change, provide:
    - file: Configuration file path (e.g., ".env", "config.py")
    - setting: Setting name (e.g., "JWT_EXPIRY")
    - change: What changed (e.g., "60 -> 3600")
    - reason: Why it was changed (e.g., "Fix timeout - was ambiguous units")

11. **Test Results** (optional): Were tests executed during this session?
    If yes, provide:
    - framework: Test framework name (e.g., "pytest", "jest")
    - passed: Number of tests that passed
    - failed: Number of tests that failed
    - coverage: Code coverage percentage (e.g., 87.3) or null

12. **MCP Tools Used**: List unique MCP tools used (e.g., serena, graphiti-memory, claude-context).

13. **Duration Estimate**: Estimate session duration based on message count (e.g., "1-2 hours").

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
                activity_profile=response.activity_profile,
                completed_tasks=response.completed_tasks,
                blocked_items=response.blocked_items,
                next_steps=response.next_steps,
                files_modified=response.files_modified,
                documentation_referenced=response.documentation_referenced,
                key_decisions=response.key_decisions,
                errors_resolved=response.errors_resolved,
                config_changes=response.config_changes,
                test_results=response.test_results,
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
