## Content Prioritization

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
