# Session 016: Research and Specify Preprocessing Prompt Injection

**Status**: ACTIVE
**Created**: 2025-12-12 00:27
**Objective**: Research and specify preprocessing prompt injection for turn-based indexing

---

## Completed

- R2 Research: Analyzed Graphiti source for LLM injection points - discovered `custom_prompt` field exists in upstream
- R1 Research: Investigated turn boundary detection - role transitions (user→assistant) are natural delimiters
- R4 Research: Validated token economics - single-pass saves ~13% tokens by eliminating redundant summarization pass
- Verified `custom_prompt` origin - introduced in upstream Graphiti PR #212 (Nov 2024) by Preston Rasmussen for reflexion mechanism
- Designed preprocessing injection architecture with concatenation approach (prepend to reflexion, not replace)
- Created TURN_BASED_INDEXING_SPEC_v1.0.md specification document with 11 implementation stories

---

## Blocked

None

---

## Next Steps

- Create sprint with 11 implementation stories from spec
- ST-1: Create ExtractionConfig schema in `graphiti_core/extraction_config.py`
- ST-2: Extend GraphitiClients with preprocessing fields
- ST-3: Create default-session-turn.md template
- ST-4: Modify node_operations.py for preprocessing injection
- ST-5: Modify edge_operations.py for preprocessing injection
- ST-6: Add extraction config to unified_config.py
- ST-7: Wire preprocessing in MCP server initialization

---

## Decisions Made

- **Use existing `custom_prompt` field**: It's an upstream Graphiti feature (PR #212), not our addition - no need to modify prompt templates
- **Concatenation over replacement**: Preprocessing prepends to reflexion hints, preserving both functionalities
- **Follow bool|str pattern**: Consistent with FilterConfig - `null`/`false` disables, `"template.md"` loads file, `"inline..."` uses directly
- **Default template approach**: `default-session-turn.md` for session turn preprocessing with template hierarchy (project > global > built-in)
- **Prepend mode default**: Preprocessing instructions come before reflexion hints for better prompt flow

---

## Errors Resolved

None

---

## Context

**Files Modified/Created**:
- `.claude/implementation/TURN_BASED_INDEXING_SPEC_v1.0.md` (created - full implementation spec)

**Documentation Referenced**:
- `graphiti_core/prompts/extract_nodes.py` - Contains `custom_prompt` injection points
- `graphiti_core/prompts/extract_edges.py` - Same injection pattern
- `graphiti_core/utils/maintenance/node_operations.py` - Context building with `custom_prompt`
- `graphiti_core/utils/maintenance/edge_operations.py` - Same pattern
- `mcp_server/unified_config.py` - Config schema patterns
- `graphiti_core/session_tracking/filter_config.py` - bool|str pattern reference
- Upstream Graphiti commit `eba9f40` (PR #212) - Origin of `custom_prompt` feature

---

## Key Research Findings

### R2: LLM Injection Points
- `custom_prompt` field exists at 4 injection points in upstream Graphiti
- Currently only used for reflexion (multi-pass retry for missed entities)
- Empty string on first pass, populated with hints on subsequent passes
- Safe to inject preprocessing on first pass

### R4: Token Economics
- Dual-pass (current): ~34.5k tokens (summarize + extract)
- Single-pass (proposed): ~30k tokens (combined)
- Savings: ~4.5k tokens (13%) by reading content once

### Upstream Verification
- `custom_prompt` introduced: Nov 13, 2024
- Author: Preston Rasmussen (Zep team)
- PR: #212 "add reflexion"
- Purpose: Support reflexion iterations for missed entity extraction

---

**Session Duration**: ~1.5 hours
**Token Usage**: ~50k estimated
