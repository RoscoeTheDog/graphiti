# Session Tracking Validation Protocol

> **Purpose**: Step-by-step guide to validate hardcoded assumptions
> **Audience**: You (the human) + subagents you'll dispatch
> **Time**: ~2-4 hours total across multiple sessions

---

## Quick Start

1. **Enable session tracking** in `graphiti.config.json`
2. **Use Claude Code normally** (session tracking indexes conversations)
3. **Collect logs** from `logs/graphiti_mcp.log`
4. **Run analysis** (copy-paste prompts below)

---

## Phase 1: Enable Session Tracking (One-Time Setup)

### Step 1: Update Configuration

Edit your `graphiti.config.json` (usually in `~/.graphiti/` or project root):

```json
{
  "session_tracking": {
    "enabled": true,
    "keep_length_days": 1,
    "filter": {
      "tool_content": "default-tool-content.md"
    }
  }
}
```

Key settings:
- `enabled: true` - Turns on session tracking
- `keep_length_days: 1` - Only process recent sessions (limits costs)
- `tool_content: "default-tool-content.md"` - **Important**: Keep the template to ensure classifiers run

**Warning**: Do NOT set `tool_content: false` during validation testing - that skips tool classification entirely and you won't get any `ASSUMPTION_GATE` log entries.

### Step 2: Verify MCP Server is Running

The MCP server automatically:
- Logs to `logs/graphiti_mcp.log` (with rotation)
- Sets log level to INFO (captures `ASSUMPTION_GATE` messages)

No additional logging configuration needed.

---

## Phase 2: Collect Data (Passive - Just Use Claude Code)

**Goal**: Accumulate 100+ gate decisions across diverse sessions.

### What Happens Automatically

When session tracking processes a conversation:
1. Tool calls are classified by `tool_classifier.py`
2. Bash commands are classified by `bash_analyzer.py`
3. Each classification logs an `ASSUMPTION_GATE` line

Example log entry:
```
2024-12-13 10:23:45 - graphiti_core.session_tracking.tool_classifier - INFO -
ASSUMPTION_GATE tool_classifier confidence_gate=0.70 tool=Read confidence=1.000
passed=True intent=read domain=filesystem method=heuristic
```

### How to Collect Faster (Existing Sessions)

If you have existing Claude Code sessions to analyze:

```bash
# Sync historical sessions (triggers classification on existing data)
# Via MCP tool: session_tracking_sync_history

# Or via CLI if available:
graphiti-mcp-session-tracking sync --days 7
```

### Minimum Data Needed

| Validation Target | Min Samples |
|-------------------|-------------|
| 0.7 confidence gate | 100 gate decisions |
| 0.3 activity threshold | 20 sessions with activity vectors |
| Token estimates | 10 sessions with before/after token counts |

---

## Phase 3: Analyze Logs (30 minutes)

### 3.1 Extract Gate Decisions

```bash
# Navigate to where logs are stored
cd /path/to/graphiti  # or wherever MCP server runs

# Create analysis directory
mkdir -p .claude/validation

# Extract all ASSUMPTION_GATE lines from MCP server logs
grep "ASSUMPTION_GATE" logs/graphiti_mcp.log > .claude/validation/gate_decisions.raw

# Also check rotated logs if they exist
grep "ASSUMPTION_GATE" logs/graphiti_mcp.log.* >> .claude/validation/gate_decisions.raw 2>/dev/null

# Count samples
wc -l .claude/validation/gate_decisions.raw
# Need at least 100 lines
```

### 3.2 Copy-Paste Analysis Prompt

**Start a new Claude Code session and paste this:**

```
I need to analyze session tracking assumption validation data.

## Context
We have instrumented logging for GATE assumptions in the session tracking framework.
The logs contain lines like:
ASSUMPTION_GATE tool_classifier confidence_gate=0.70 tool=Read confidence=1.000 passed=True intent=read domain=filesystem method=heuristic

## Task
1. Read the file `.claude/validation/gate_decisions.raw`
2. Parse the log lines into structured data
3. Answer these questions:

### Confidence Gate Analysis (0.7 threshold)
- What is the distribution of confidence scores? (min, max, mean, median, std)
- What % of decisions pass the current 0.7 gate?
- What % would pass at alternative thresholds: 0.5, 0.6, 0.8, 0.9?
- Are there any tools that consistently fall just below 0.7? (potential false rejections)
- Are there any tools with confidence just above 0.7 that seem misclassified? (potential false acceptances)

### Recommendation
Based on the data, should the 0.7 threshold be adjusted? Provide evidence.

## Output Format
1. Summary statistics table
2. Distribution histogram (ASCII art is fine)
3. Threshold sensitivity analysis
4. Recommendation with confidence level
```

---

## Phase 4: Token Estimation Validation (20 minutes)

### 4.1 Collect Token Data

Add this to a test session to capture before/after tokens:

```python
# Run this in a Python environment with tiktoken installed
import tiktoken

def validate_token_estimate(text: str) -> dict:
    """Compare chars//4 estimate to actual tokens."""
    estimated = len(text) // 4
    encoder = tiktoken.get_encoding("cl100k_base")
    actual = len(encoder.encode(text))
    error_pct = abs(estimated - actual) / actual * 100 if actual > 0 else 0
    return {
        "chars": len(text),
        "estimated_tokens": estimated,
        "actual_tokens": actual,
        "error_pct": round(error_pct, 1)
    }

# Test with various content types
test_cases = [
    ("Code", "def foo():\n    return bar"),
    ("Prose", "The quick brown fox jumps over the lazy dog."),
    ("JSON", '{"key": "value", "nested": {"a": 1}}'),
    ("Tool output", "[File contents of src/main.py]\n```python\nimport os\n```"),
]

for name, text in test_cases:
    result = validate_token_estimate(text)
    print(f"{name}: est={result['estimated_tokens']}, actual={result['actual_tokens']}, error={result['error_pct']}%")
```

### 4.2 Copy-Paste Token Analysis Prompt

**Start a new session and paste this:**

```
I need to validate token estimation assumptions in the session tracking framework.

## Current Assumption
The code uses `len(text) // 4` to estimate tokens (4 chars per token).

## Task
1. Install tiktoken if needed: `pip install tiktoken`
2. Run the validation script above on real session content
3. Collect samples from:
   - Tool results (Read, Bash, Grep output)
   - User messages
   - Agent responses
   - Code blocks vs prose

## Questions to Answer
1. What is the actual chars-to-tokens ratio across content types?
2. Is `// 4` too aggressive or too conservative?
3. Should we use different ratios for different content types?

## Output Format
Table with columns: content_type, samples, avg_ratio, recommended_divisor
```

---

## Phase 5: Activity Threshold Validation (30 minutes)

### 5.1 Copy-Paste Activity Analysis Prompt

**Start a new session with a coding task, then paste this after:**

```
Analyze the activity vector from this session.

## Task
1. What tools were used in this session?
2. Classify this session type (debugging, building, exploring, etc.)
3. Compute what the activity vector SHOULD be based on your classification
4. Compare to what the system would compute

## Questions
1. At threshold 0.3, which activities would be marked "dominant"?
2. Does that match the actual session character?
3. What threshold would produce the most accurate "dominant" list?

## Try Different Thresholds
For this session, list dominant activities at:
- threshold=0.2
- threshold=0.3
- threshold=0.4
- threshold=0.5

Which produces the best human-interpretable result?
```

---

## Phase 6: A/B Testing (Optional, Advanced)

If you want to test different threshold values in production:

### 6.1 Create Threshold Override Config

Add to `graphiti.config.json`:

```json
{
  "session_tracking": {
    "experimental": {
      "confidence_gate": 0.7,
      "activity_threshold": 0.3,
      "partial_match_penalty": 0.7
    }
  }
}
```

### 6.2 Modify Code to Read Config (Requires Code Change)

This would require modifying the gate code to read from config instead of hardcoded values. Consider this for a future sprint if validation shows current values are wrong.

---

## Analysis Scripts

### Full Analysis Script

Save as `.claude/validation/analyze_gates.py`:

```python
#!/usr/bin/env python3
"""Analyze ASSUMPTION_GATE logs for validation."""

import re
import sys
from collections import defaultdict
from pathlib import Path

def parse_gate_line(line: str) -> dict | None:
    """Parse a single ASSUMPTION_GATE log line."""
    if "ASSUMPTION_GATE" not in line:
        return None

    # Extract key=value pairs
    match = re.search(r"ASSUMPTION_GATE (\w+) (.+)", line)
    if not match:
        return None

    component = match.group(1)
    pairs = match.group(2)

    data = {"component": component}
    for pair in pairs.split():
        if "=" in pair:
            key, value = pair.split("=", 1)
            data[key] = value

    return data

def analyze(log_file: Path):
    """Analyze gate decisions from log file."""
    decisions = []

    with open(log_file) as f:
        for line in f:
            parsed = parse_gate_line(line)
            if parsed:
                decisions.append(parsed)

    if not decisions:
        print("No ASSUMPTION_GATE lines found!")
        return

    print(f"Analyzed {len(decisions)} gate decisions\n")

    # Extract confidence values
    confidences = [float(d.get("confidence", 0)) for d in decisions]

    # Statistics
    print("=== Confidence Distribution ===")
    print(f"Min:    {min(confidences):.3f}")
    print(f"Max:    {max(confidences):.3f}")
    print(f"Mean:   {sum(confidences)/len(confidences):.3f}")

    sorted_conf = sorted(confidences)
    median = sorted_conf[len(sorted_conf)//2]
    print(f"Median: {median:.3f}")

    # Pass rates at different thresholds
    print("\n=== Threshold Sensitivity ===")
    for threshold in [0.5, 0.6, 0.7, 0.8, 0.9]:
        pass_count = sum(1 for c in confidences if c >= threshold)
        pass_rate = pass_count / len(confidences)
        print(f"Threshold {threshold}: {pass_rate:.1%} pass ({pass_count}/{len(decisions)})")

    # Tools near the boundary (0.65-0.75)
    print("\n=== Near Boundary (0.65-0.75) ===")
    boundary = [d for d in decisions if 0.65 <= float(d.get("confidence", 0)) <= 0.75]
    if boundary:
        by_tool = defaultdict(list)
        for d in boundary:
            by_tool[d.get("tool", "unknown")].append(float(d.get("confidence", 0)))
        for tool, confs in sorted(by_tool.items()):
            print(f"  {tool}: {len(confs)} decisions, avg={sum(confs)/len(confs):.3f}")
    else:
        print("  No decisions near boundary")

    # By component
    print("\n=== By Component ===")
    by_component = defaultdict(int)
    for d in decisions:
        by_component[d.get("component", "unknown")] += 1
    for comp, count in sorted(by_component.items()):
        print(f"  {comp}: {count}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_gates.py <log_file>")
        sys.exit(1)

    analyze(Path(sys.argv[1]))
```

Run with:

```bash
python .claude/validation/analyze_gates.py .claude/validation/gate_decisions.raw
```

---

## Success Criteria

### Confidence Gate (0.7)

✅ **Validated** if:
- Pass rate is 70-95% (too low = bad heuristics, too high = threshold too low)
- No obvious false rejections (good heuristics failing at 0.68-0.69)
- No obvious false acceptances (bad heuristics passing at 0.71-0.72)

❌ **Needs Adjustment** if:
- Many decisions cluster just below 0.7 (threshold too high)
- LLM disagrees with heuristics that passed (threshold too low)

### Activity Threshold (0.3)

✅ **Validated** if:
- Dominant activities match human session classification
- 2-4 activities typically marked dominant (not 0, not 8)

❌ **Needs Adjustment** if:
- Sessions consistently get 0 or 7+ dominant activities
- Obvious primary activity is excluded

### Token Estimates

✅ **Validated** if:
- Actual chars-to-tokens ratio is within 20% of 4
- Reduction claims (70%, 90%, 93%) are within 20% of actual

❌ **Needs Adjustment** if:
- Actual ratio differs significantly (e.g., actual is 3 or 5)
- Claimed reductions are off by >50%

---

## After Validation

### If Assumptions are Valid

1. Update this document to mark them as ✅ VALIDATED
2. Add validation date and sample size
3. Consider removing some `[UNVALIDATED]` comments (but keep the documentation)

### If Adjustments Needed

1. Create a story/issue to adjust the value
2. Run A/B test with new value
3. Update code AND documentation together

---

## Questions?

If you need help with validation:

1. Collect your data (Phase 2)
2. Start a new Claude Code session
3. Share the log file and ask for analysis
