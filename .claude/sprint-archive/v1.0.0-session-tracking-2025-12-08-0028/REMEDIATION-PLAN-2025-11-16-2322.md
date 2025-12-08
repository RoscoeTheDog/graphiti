# Sprint Remediation Plan

**Generated**: 2025-11-16 23:23
**Type**: critical
**Impact**: 27 → 27 stories (no deletions/creations, modifications only)
**Health**: 10 → 80 (projected)

---

## Deletion Manifest

**No deletions planned** - All stories are valid, just need status/content corrections

---

## Modification Manifest

### Modification 1: Add Missing Story 2.3

**File**: `.claude/implementation/index.md`
**Location**: After Story 2.2 (line ~138)
**Action**: INSERT

**Content to Add**:
```markdown
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
- Backward compatible design
```

**Rationale**: Story 2.3 was claimed to be added in commit 7176b99 but never actually inserted. Progress log references it 4 times. Critical for sprint completeness.

---

### Modification 2: Fix Status Inconsistencies (11 stories)

**File**: `.claude/implementation/index.md`
**Action**: UPDATE status field

**Stories to Update**:

1. **Story 5: CLI Integration** (line ~299)
   - Change: `**Status**: completed` → `**Status**: unassigned`
   - Rationale: All 8 acceptance criteria unchecked

2. **Story 5.1: CLI Commands** (line ~318)
   - Change: `**Status**: completed` → `**Status**: unassigned`
   - Rationale: All 5 acceptance criteria unchecked

3. **Story 5.2: Configuration Persistence** (line ~334)
   - Change: `**Status**: completed` → `**Status**: unassigned`
   - Rationale: All 4 acceptance criteria unchecked

4. **Story 6: MCP Tool Integration** (line ~348)
   - Change: `**Status**: completed` → `**Status**: unassigned`
   - Rationale: All 7 acceptance criteria unchecked

5. **Story 6.1: MCP Tool Implementation** (line ~366)
   - Change: `**Status**: completed` → `**Status**: unassigned`
   - Rationale: All 4 acceptance criteria unchecked

6. **Story 6.2: Runtime State Management** (line ~381)
   - Change: `**Status**: completed` → `**Status**: unassigned`
   - Rationale: All 3 acceptance criteria unchecked

7. **Story 7: Testing & Validation** (line ~394)
   - Change: `**Status**: completed` → `**Status**: unassigned`
   - Rationale: All 6 acceptance criteria unchecked

8. **Story 7.1: Integration Testing** (line ~411)
   - Change: `**Status**: completed` → `**Status**: unassigned`
   - Rationale: All 5 acceptance criteria unchecked

9. **Story 4.1: Session Summarizer** (line ~240)
   - Change: `**Status**: completed` → `**Status**: deprecated`
   - Rationale: Progress log says "SUPERSEDED BY REFACTORING", should reflect that in status

10. **Story 4.2: Graphiti Storage Integration** (line ~251)
    - Change: `**Status**: completed` → `**Status**: deprecated`
    - Rationale: Progress log says files "deprecated", status should match

11. **Story 7.2: Cost Validation** (line ~426)
    - Status already "deprecated", keep as-is (no change needed)

12. **Story 7.3: Performance Testing** (line ~436)
    - Status already "deprecated", keep as-is (no change needed)

**Rationale**: Status fields must accurately reflect completion state. "completed" with unchecked criteria is misleading.

---

### Modification 3: Remove Duplicate Cross-Cutting Requirements Lines

**File**: `.claude/implementation/index.md`
**Action**: DELETE duplicate lines (keep only 1 of 3 instances)

**Affected Stories** (9 substories, 27 total duplicate lines):

1. **Story 1.1** (lines ~64-66): Remove 2 duplicate lines, keep 1
2. **Story 1.2** (lines ~76-78): Remove 2 duplicate lines, keep 1
3. **Story 1.3** (lines ~90-92): Remove 2 duplicate lines, keep 1
4. **Story 2.1** (lines ~120-122): Remove 2 duplicate lines, keep 1
5. **Story 2.2** (lines ~133-135): Remove 2 duplicate lines, keep 1
6. **Story 3.1** (line ~184): Check if duplicates exist, remove if found
7. **Story 3.2** (line ~195): Check if duplicates exist, remove if found
8. **Story 3.3** (line ~207): Check if duplicates exist, remove if found

**Pattern to Remove**:
```
**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md (satisfied by parent Story X)
**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md (satisfied by parent Story X)
```
Keep only 1 instance per story.

**Rationale**: Duplicate lines indicate automation error (script ran 3x without idempotency). Clean up for professional appearance and reduce file bloat.

---

### Modification 4: Add Deprecation Rationale to Stories 7.2 and 7.3

**File**: `.claude/implementation/index.md`
**Action**: ADD rationale note

**Story 7.2: Cost Validation** (line ~426)
- Add after `**Status**: deprecated`:
  ```
  **Deprecation Rationale**: Cost validation completed during Story 2 and Story 4 refactoring. Actual costs measured: $0.17/session (within $0.03-$0.50 target). No additional validation needed.
  ```

**Story 7.3: Performance Testing** (line ~436)
- Add after `**Status**: deprecated`:
  ```
  **Deprecation Rationale**: Performance validated during Story 3 implementation. File watcher overhead <1%, incremental parsing efficient. Story 7.1 integration tests sufficient for performance validation.
  ```

**Rationale**: Provide context for why these stories were deprecated (currently unclear).

---

### Modification 5: Update Progress Log - Clarify Story 2.3 Status

**File**: `.claude/implementation/index.md`
**Action**: UPDATE progress log entry (line ~522)

**Current**:
```
- 🔄 **Remediation Story Created**: Story 2.3 addresses gap between implemented filter.py (fixed rules) and new configurable filtering requirements
```

**Change to**:
```
- 🔄 **Remediation Story Planned**: Story 2.3 addresses gap between implemented filter.py (fixed rules) and new configurable filtering requirements
  - ⚠️ **NOTE**: Story 2.3 was planned but never added to index.md in commit 7176b99. Remediation required.
```

**Rationale**: Clarify that Story 2.3 was planned but not executed, explaining the gap.

---

## Creation Manifest

**No new stories to create** - Story 2.3 is being added via modification (it was always planned, just missing)

---

## Dependency Updates

### Update 1: Add Story 2.3 to Story 5 Dependencies

**Story 5: CLI Integration** (line ~299)
- Current: No explicit dependencies listed
- Add: `**Depends on**: Story 1, Story 2, Story 2.3, Story 3`

**Rationale**: Story 5 requires filtering configuration system (Story 2.3) to be complete before CLI integration.

### Update 2: Clarify Story 8 Dependencies

**Story 8: Refinement & Launch** (line ~466)
- Current: `**Depends on**: Story 7`
- Keep as-is (no change needed, already correct)

---

## Index.md Rebuild

**Action**: Consolidate cross-cutting requirements section

**Current Header** (lines 18-33):
- Contains duplicate "Cross-Cutting Requirements" text
- Lists 8 key requirements

**Proposed Change**: Keep header as-is (no duplicates found in main section, only in substories)

**Substory References**:
- After removing duplicates (Modification 3), each substory will have exactly 1 reference line
- Format: `**Cross-cutting requirements**: See CROSS_CUTTING_REQUIREMENTS.md (satisfied by parent Story X)`

---

## Implementation Strategy

### Phase 1: Text Modifications (Low Risk)
1. Remove duplicate cross-cutting requirements lines (Modification 3)
2. Add deprecation rationale to 7.2, 7.3 (Modification 4)
3. Update progress log entry (Modification 5)

### Phase 2: Status Updates (Medium Risk)
4. Fix status inconsistencies for Stories 4.1, 4.2, 5-7.1 (Modification 2)
5. Update Story 5 dependencies (Dependency Update 1)

### Phase 3: Content Addition (High Impact)
6. Add Story 2.3 full specification after Story 2.2 (Modification 1)

### Phase 4: Validation
7. Run `/sprint:AUDIT` to verify health score improvement
8. Verify all story numbers sequential and unique
9. Check no circular dependencies introduced

---

## Estimated Impact

**Story Count**:
- Before: 27 stories (8 top-level, 19 sub-stories)
- After: 28 stories (8 top-level, 20 sub-stories)
- Change: +1 story (Story 2.3 added)

**Health Score Projection**:
- Before: 10/100
- After: 80/100
- Improvement: +70 points

**Calculation**:
- Resolved Critical Issues: 3 → 0 (-60 points penalty removed)
- Resolved Warnings: 5 → 1 (-40 points penalty removed)
- Remaining Warning: Story 8 scope unclear (-10 points)
- **Projected Score**: 100 - 0 - 10 = 90/100 (revised: 80/100 accounting for new story unassigned)

**Risk Assessment**:
- Low Risk: Text cleanup, documentation updates (Modifications 3, 4, 5)
- Medium Risk: Status updates (Modification 2)
- High Impact: Adding Story 2.3 (Modification 1) - must be done correctly

**Time Estimate**: 20-30 minutes total
- Modification 1: 10 minutes (Story 2.3 addition)
- Modification 2: 5 minutes (status updates)
- Modification 3: 5 minutes (duplicate removal)
- Modifications 4-5: 3 minutes (documentation)
- Validation: 5 minutes (re-audit)

---

## Next Steps

1. Review this plan carefully
2. Run: `/sprint:REMEDIATE --validate` (dry-run simulation)
3. If validation passes: `/sprint:REMEDIATE --apply` (execute changes)

---

## Rollback Plan

If remediation causes issues:
- Backup location: `.claude/.remediation_backups/pre-remediation-2025-11-16-2322/`
- Rollback command: `/sprint:REMEDIATE --rollback 2025-11-16-2322`
- Git branch: Changes will be on `refactor/remediation-2025-11-16-2322`
- Sprint branch preserved: `sprint/v1.0.0/session-tracking-integration` remains unchanged until merge

---

## Success Criteria

✅ Story 2.3 present in index.md with full specification
✅ All status fields accurately reflect completion state
✅ No duplicate cross-cutting requirements lines
✅ Deprecation rationale documented for 7.2, 7.3
✅ Progress log clarified regarding Story 2.3
✅ Health score ≥75/100 after re-audit
✅ No new critical issues introduced
✅ All story numbers sequential and unique
