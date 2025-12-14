# Session Tracking Assumptions Audit

> **Status**: UNVALIDATED - All assumptions require empirical validation
> **Created**: 2024-12-13
> **Last Updated**: 2024-12-13

## Overview

This document catalogs all hardcoded assumptions in the session tracking framework.
These assumptions were identified in an audit and marked with `[UNVALIDATED]` comments
in the source code.

**Why this matters**: Agents reading this code may infer these values as facts.
Until validated, they should be treated as engineering guesses.

---

## GATE Assumptions (Affect Control Flow)

These assumptions **change system behavior**. Wrong values cause incorrect decisions.

### 1. Confidence Gate: 0.7

| Property | Value |
|----------|-------|
| **Location** | `tool_classifier.py:928`, `bash_analyzer.py:808` |
| **Value** | `0.7` |
| **Affects** | Whether to use heuristic or LLM classification |
| **Risk** | Too low: accept bad heuristics. Too high: waste LLM $$ |
| **Validation Status** | ❌ UNVALIDATED |

**Instrumentation**: Logs emitted with prefix `ASSUMPTION_GATE` contain:
- `confidence_gate`: The threshold value (0.7)
- `confidence`: Actual computed confidence
- `passed`: Whether gate was passed (True/False)
- `intent`, `domain`, `method`: Classification details

### 2. Activity Threshold: 0.3

| Property | Value |
|----------|-------|
| **Location** | `activity_vector.py:104` |
| **Value** | `0.3` |
| **Affects** | Which activities are considered "dominant" |
| **Risk** | Too low: everything dominant. Too high: nothing dominant |
| **Validation Status** | ❌ UNVALIDATED |

### 3. Confidence Penalty: 0.7 multiplier

| Property | Value |
|----------|-------|
| **Location** | `tool_classifier.py:493`, `tool_classifier.py:510` |
| **Value** | `* 0.7` |
| **Affects** | Confidence when only intent OR domain matches |
| **Risk** | Wrong penalty = reject good partials or accept bad ones |
| **Validation Status** | ❌ UNVALIDATED |

---

## ESTIMATE Assumptions (Affect Display/Logging Only)

These assumptions affect **what users/agents see**, not system behavior.

### Token Composition Weights

| Property | Value | Location |
|----------|-------|----------|
| Tool results | 60% of tokens | `filter_config.py:158` |
| User messages | 15% of tokens | `filter_config.py:159` |
| Agent messages | 25% of tokens | `filter_config.py:160` |

**Validation Status**: ❌ UNVALIDATED

### Token Reduction Estimates

| Mode | Claimed Reduction | Location |
|------|-------------------|----------|
| Template (tools) | 70% | `filter_config.py:173` |
| Template (messages) | 50% | `filter_config.py:177-178` |
| Omit mode | 95% | `filter_config.py:168` |
| Per tool result | 90% | `filter.py:464` |
| Overall | 93% | `filter.py:8` |

**Validation Status**: ❌ ALL UNVALIDATED

### Activity Signal Weights

All weights in these mappings are unvalidated:

| Mapping | Location | Count |
|---------|----------|-------|
| `EXTRACTION_AFFINITIES` | `extraction_priority.py:53-107` | ~50 weights |
| `INTENT_TO_ACTIVITY` | `tool_classifier.py:336-347` | 10 mappings |
| `DOMAIN_MODIFIERS` | `tool_classifier.py:351-357` | 5 mappings |
| `COMMAND_HEURISTICS` | `bash_analyzer.py:175-646` | ~50 commands |

**Known Issue**: `INTENT_TO_ACTIVITY` is duplicated between `tool_classifier.py`
and `bash_analyzer.py` with a **discrepancy**:
- `tool_classifier.py`: `ToolIntent.VALIDATE: {"testing": 0.6}`
- `bash_analyzer.py`: `ToolIntent.VALIDATE: {"testing": 0.9}`

---

## Instrumentation

### Log Format

Gate decisions are logged at INFO level with this format:

```
ASSUMPTION_GATE {component} confidence_gate={threshold} tool={name} confidence={value} passed={bool} intent={intent} domain={domain} method={method}
```

### How to Collect

```bash
# Collect all gate decisions from logs
grep "ASSUMPTION_GATE" /path/to/logs/*.log > gate_decisions.log

# Parse into CSV for analysis
grep "ASSUMPTION_GATE" logs/*.log | \
  sed 's/.*ASSUMPTION_GATE //' | \
  tr ' ' ',' > gate_decisions.csv
```

### Analysis Queries

```python
import pandas as pd

# Load collected data
df = pd.read_csv("gate_decisions.csv", names=[
    "component", "confidence_gate", "tool", "confidence",
    "passed", "intent", "domain", "method"
])

# Clean up key=value format
for col in df.columns:
    df[col] = df[col].str.split('=').str[-1]

df['confidence'] = df['confidence'].astype(float)
df['passed'] = df['passed'] == 'True'

# Distribution of confidence scores
print(df['confidence'].describe())

# Pass rate at current threshold
print(f"Pass rate: {df['passed'].mean():.1%}")

# What if threshold were different?
for threshold in [0.5, 0.6, 0.7, 0.8, 0.9]:
    pass_rate = (df['confidence'] >= threshold).mean()
    print(f"Threshold {threshold}: {pass_rate:.1%} would pass")
```

---

## Validation Protocol

See [SESSION_TRACKING_VALIDATION_PROTOCOL.md](SESSION_TRACKING_VALIDATION_PROTOCOL.md) for:
- Step-by-step testing procedures
- Copy-paste prompts for validation sessions
- Analysis scripts
- Success criteria

---

## Change Log

| Date | Change |
|------|--------|
| 2024-12-13 | Initial audit complete. Added UNVALIDATED markers to all files. |
