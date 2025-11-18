#!/usr/bin/env python3
"""
Analyze JSONL session to estimate token savings from filtering tool outputs.

This script:
1. Parses a Claude Code JSONL session file
2. Categorizes content by type (user, assistant, tool calls, tool results)
3. Estimates token counts for each category
4. Calculates savings from filtering tool outputs
5. Estimates OpenAI cost for Graphiti processing
"""
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict
from collections import defaultdict


@dataclass
class ContentStats:
    """Statistics for different content types."""
    user_messages: int = 0
    assistant_messages: int = 0
    tool_calls: int = 0
    tool_results: int = 0

    user_chars: int = 0
    assistant_chars: int = 0
    tool_call_chars: int = 0  # Parameters/structure only
    tool_result_chars: int = 0  # Full output content

    tool_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def total_chars(self) -> int:
        return (self.user_chars + self.assistant_chars +
                self.tool_call_chars + self.tool_result_chars)

    @property
    def estimated_tokens(self) -> int:
        """Rough estimate: 1 token ≈ 4 chars for English text."""
        return self.total_chars // 4

    @property
    def filtered_chars(self) -> int:
        """Chars if we filter tool outputs (keep structure only)."""
        # Keep: user + assistant + tool call structure
        # Omit: tool result content (replace with 1-line summary)
        tool_result_summaries = self.tool_results * 100  # ~100 chars per summary
        return (self.user_chars + self.assistant_chars +
                self.tool_call_chars + tool_result_summaries)

    @property
    def filtered_tokens(self) -> int:
        return self.filtered_chars // 4

    @property
    def token_savings(self) -> int:
        return self.estimated_tokens - self.filtered_tokens

    @property
    def savings_percent(self) -> float:
        if self.estimated_tokens == 0:
            return 0.0
        return (self.token_savings / self.estimated_tokens) * 100


def parse_jsonl_session(file_path: Path) -> ContentStats:
    """Parse JSONL session and categorize content."""
    stats = ContentStats()

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
                entry_type = entry.get('type')

                # User messages
                if entry_type == 'user':
                    message = entry.get('message', {})
                    content = message.get('content', '')

                    # Check if this is a tool result (not a user message)
                    if isinstance(content, list):
                        for item in content:
                            if item.get('type') == 'tool_result':
                                stats.tool_results += 1
                                result_content = str(item.get('content', ''))
                                stats.tool_result_chars += len(result_content)
                    elif isinstance(content, str) and content:
                        stats.user_messages += 1
                        stats.user_chars += len(content)

                # Assistant messages
                elif entry_type == 'assistant':
                    message = entry.get('message', {})
                    content = message.get('content', [])

                    if isinstance(content, list):
                        for item in content:
                            item_type = item.get('type')

                            # Text responses
                            if item_type == 'text':
                                stats.assistant_messages += 1
                                text = item.get('text', '')
                                stats.assistant_chars += len(text)

                            # Tool calls
                            elif item_type == 'tool_use':
                                stats.tool_calls += 1
                                tool_name = item.get('name', 'unknown')
                                stats.tool_types[tool_name] += 1

                                # Count structure (name + params)
                                tool_structure = json.dumps({
                                    'name': tool_name,
                                    'input': item.get('input', {})
                                })
                                stats.tool_call_chars += len(tool_structure)

            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Warning: Error parsing line: {e}", file=sys.stderr)
                continue

    return stats


def estimate_openai_cost(tokens: int, model: str = "gpt-4o-mini") -> Dict[str, float]:
    """
    Estimate OpenAI API cost for processing tokens through Graphiti.

    Graphiti uses LLM for:
    1. Entity extraction
    2. Edge creation
    3. Summary generation

    Rough estimate: 2.5x input tokens for processing overhead
    """
    # OpenAI pricing per 1M tokens (as of 2025)
    pricing = {
        "gpt-4o-mini": {"input": 0.150, "output": 0.600},  # $0.15/$0.60 per 1M
        "gpt-4o": {"input": 2.50, "output": 10.00},  # $2.50/$10 per 1M
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},  # $10/$30 per 1M
    }

    rates = pricing.get(model, pricing["gpt-4o-mini"])

    # Graphiti processing overhead
    input_tokens = tokens * 2.5  # 2.5x for context + prompts
    output_tokens = tokens * 0.3  # ~30% output (entities, edges, summaries)

    input_cost = (input_tokens / 1_000_000) * rates["input"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]

    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": input_cost + output_cost,
    }


def print_report(stats: ContentStats, file_path: Path):
    """Generate comprehensive cost analysis report."""
    print("=" * 80)
    print(f"JSONL SESSION FILTERING ANALYSIS")
    print("=" * 80)
    print(f"\nFile: {file_path.name}")
    print(f"Size: {file_path.stat().st_size / 1024:.1f} KB")
    print()

    # Content breakdown
    print("[Content Breakdown]")
    print(f"  User messages:     {stats.user_messages:>8,}  ({stats.user_chars:>12,} chars)")
    print(f"  Assistant messages:{stats.assistant_messages:>8,}  ({stats.assistant_chars:>12,} chars)")
    print(f"  Tool calls:        {stats.tool_calls:>8,}  ({stats.tool_call_chars:>12,} chars)")
    print(f"  Tool results:      {stats.tool_results:>8,}  ({stats.tool_result_chars:>12,} chars)")
    print(f"  {'-' * 60}")
    print(f"  TOTAL:             {stats.user_messages + stats.assistant_messages:>8,}  ({stats.total_chars:>12,} chars)")
    print()

    # Tool usage breakdown
    print("[Tool Usage - Top 10]")
    sorted_tools = sorted(stats.tool_types.items(), key=lambda x: x[1], reverse=True)[:10]
    for tool_name, count in sorted_tools:
        print(f"  {tool_name:<40} {count:>6,} calls")
    print()

    # Token estimates
    print("[Token Estimates]")
    print(f"  Unfiltered (full content):      {stats.estimated_tokens:>12,} tokens")
    print(f"  Filtered (structure only):      {stats.filtered_tokens:>12,} tokens")
    print(f"  {'-' * 60}")
    print(f"  TOKEN SAVINGS:                  {stats.token_savings:>12,} tokens")
    print(f"  Savings percentage:             {stats.savings_percent:>12.1f}%")
    print()

    # OpenAI cost estimates (Graphiti backend)
    print("[OpenAI Cost Estimates - Graphiti Processing]")
    print()

    for model in ["gpt-4o-mini", "gpt-4o"]:
        # Unfiltered cost
        unfiltered_cost = estimate_openai_cost(stats.estimated_tokens, model)
        filtered_cost = estimate_openai_cost(stats.filtered_tokens, model)

        print(f"  {model.upper()}:")
        print(f"    Unfiltered session:")
        print(f"      Input tokens:   {unfiltered_cost['input_tokens']:>12,}")
        print(f"      Output tokens:  {unfiltered_cost['output_tokens']:>12,}")
        print(f"      Cost:           ${unfiltered_cost['total_cost']:>10.2f}")
        print()
        print(f"    Filtered session:")
        print(f"      Input tokens:   {filtered_cost['input_tokens']:>12,}")
        print(f"      Output tokens:  {filtered_cost['output_tokens']:>12,}")
        print(f"      Cost:           ${filtered_cost['total_cost']:>10.2f}")
        print()
        print(f"    SAVINGS:          ${unfiltered_cost['total_cost'] - filtered_cost['total_cost']:>10.2f}")
        print(f"    Savings %:        {((unfiltered_cost['total_cost'] - filtered_cost['total_cost']) / unfiltered_cost['total_cost'] * 100):>10.1f}%")
        print()

    # Monthly projections
    print("[Monthly Projections - 60 sessions/month]")
    filtered_mini = estimate_openai_cost(stats.filtered_tokens, "gpt-4o-mini")
    filtered_4o = estimate_openai_cost(stats.filtered_tokens, "gpt-4o")

    print(f"  gpt-4o-mini (filtered):")
    print(f"    Per session:       ${filtered_mini['total_cost']:>10.2f}")
    print(f"    Monthly (60 sess): ${filtered_mini['total_cost'] * 60:>10.2f}")
    print()
    print(f"  gpt-4o (filtered):")
    print(f"    Per session:       ${filtered_4o['total_cost']:>10.2f}")
    print(f"    Monthly (60 sess): ${filtered_4o['total_cost'] * 60:>10.2f}")
    print()

    # Recommendation
    print("[Recommendation]")
    if filtered_mini['total_cost'] < 1.0:
        print(f"  [OK] FEASIBLE - gpt-4o-mini costs ${filtered_mini['total_cost']:.2f}/session")
        print(f"       Monthly cost: ${filtered_mini['total_cost'] * 60:.2f} (60 sessions)")
        print(f"       This is VERY affordable for institutional agent memory!")
    elif filtered_mini['total_cost'] < 2.0:
        print(f"  [WARN] ACCEPTABLE - gpt-4o-mini costs ${filtered_mini['total_cost']:.2f}/session")
        print(f"         Monthly cost: ${filtered_mini['total_cost'] * 60:.2f} (60 sessions)")
        print(f"         Consider more aggressive filtering if cost is concern.")
    else:
        print(f"  [ERROR] EXPENSIVE - gpt-4o-mini costs ${filtered_mini['total_cost']:.2f}/session")
        print(f"          Monthly cost: ${filtered_mini['total_cost'] * 60:.2f} (60 sessions)")
        print(f"          Need more aggressive filtering or batching strategy.")

    print()
    print("=" * 80)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze JSONL session for token savings from filtering"
    )
    parser.add_argument(
        "jsonl_file",
        type=str,
        help="Path to JSONL session file"
    )

    args = parser.parse_args()

    file_path = Path(args.jsonl_file)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    # Parse and analyze
    stats = parse_jsonl_session(file_path)

    # Generate report
    print_report(stats, file_path)


if __name__ == "__main__":
    main()
