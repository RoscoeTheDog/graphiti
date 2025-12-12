"""Hardcoded template sources for session summarization.

These templates define the default prompts used for LLM-based summarization
of different message types in session tracking.
"""

DEFAULT_TOOL_CONTENT_TEMPLATE = """Summarize this tool result concisely in 1 paragraph.

**Tool**: {context}

**Focus on**:
- What operation was performed
- Key findings or outputs
- Any errors or warnings
- Relevant file paths, function names, or data values

**Original content**:
{content}

**Summary** (1 paragraph, actionable information):
"""

DEFAULT_USER_MESSAGES_TEMPLATE = """Summarize this user message in 2 paragraphs or less.

**Context**: {context}

**Focus on**:
- What the user is asking for
- Key requirements or constraints
- Context or background provided

**Original message**:
{content}

**Summary** (preserve user intent, 2 paragraphs or less):
"""

DEFAULT_AGENT_MESSAGES_TEMPLATE = """Summarize this agent response in 2 paragraphs or less.

**Context**: {context}

**Focus on**:
- Main explanation or reasoning
- Decisions made or approaches taken
- Important context or caveats
- Follow-up actions planned

**Original response**:
{content}

**Summary** (reasoning and decisions, 2 paragraphs or less):
"""

DEFAULT_SESSION_SUMMARY_TEMPLATE = """Summarize this coding session into structured format.

**Activity Profile**: {activity_profile}

**Extract based on session activities**:

{dynamic_extraction_instructions}

**Session Content**:
{content}

**Response** (JSON matching EnhancedSessionSummary schema):
"""

DEFAULT_SESSION_TURN_TEMPLATE = """## Content Prioritization

**HIGH Priority** (always extract):
- Files created, modified, or read during the turn
- Tools invoked and their outcomes
- Errors encountered and their resolutions
- Explicit decisions made by user or agent

**MEDIUM Priority** (extract if significant):
- Concepts discussed or defined
- Patterns or approaches mentioned
- Configuration changes or settings modified

**LOW Priority** (extract only if central to the turn):
- Background context or historical references
- General questions or clarifications
- Routine operations without unique outcomes

## Entity Type Hints

Focus on these entity types:
- **File**: Source files, configuration files, data files
- **Tool**: Commands, utilities, APIs, libraries used
- **Error**: Exceptions, failures, warnings encountered
- **Decision**: Choices made, approaches selected, alternatives rejected
- **Concept**: Ideas, patterns, architectures, design principles

## Relationship Guidance

Extract relationships that capture:
- **File-Tool**: Which tools operated on which files
- **Error-File**: Where errors occurred
- **Decision-Concept**: What decisions were based on which concepts
- **Tool-Error**: Which tools produced which errors
- **Concept-File**: Which concepts were implemented in which files

## Template Variables

{context}
{content}
"""

# Template filename mapping
DEFAULT_TEMPLATES = {
    "default-tool-content.md": DEFAULT_TOOL_CONTENT_TEMPLATE,
    "default-user-messages.md": DEFAULT_USER_MESSAGES_TEMPLATE,
    "default-agent-messages.md": DEFAULT_AGENT_MESSAGES_TEMPLATE,
    "default-session-summary.md": DEFAULT_SESSION_SUMMARY_TEMPLATE,
    "default-session-turn.md": DEFAULT_SESSION_TURN_TEMPLATE,
}
