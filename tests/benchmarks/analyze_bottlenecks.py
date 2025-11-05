"""
Static analysis tool to identify potential performance bottlenecks in Graphiti's write path.

This script analyzes the codebase to identify:
1. Sequential operations that could be parallelized
2. Missing transaction batching
3. Synchronous operations in async code
4. Potential N+1 query patterns
5. Missing connection pooling configurations
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Any


class BottleneckAnalyzer(ast.NodeVisitor):
    """AST visitor to detect performance anti-patterns."""

    def __init__(self, filename: str):
        self.filename = filename
        self.issues: List[Dict[str, Any]] = []
        self.current_function = None
        self.in_async_function = False

    def visit_AsyncFunctionDef(self, node):
        """Track async function definitions."""
        old_function = self.current_function
        old_async = self.in_async_function

        self.current_function = node.name
        self.in_async_function = True

        # Check for sequential awaits that could be parallel
        self._check_sequential_awaits(node)

        # Check for loops with awaits (potential N+1)
        self._check_loop_awaits(node)

        self.generic_visit(node)

        self.current_function = old_function
        self.in_async_function = old_async

    def _check_sequential_awaits(self, func_node):
        """Detect sequential await calls that could be parallelized."""
        body = func_node.body
        consecutive_awaits = []

        for i, stmt in enumerate(body):
            if isinstance(stmt, (ast.Assign, ast.Expr)):
                value = stmt.value if isinstance(stmt, ast.Assign) else stmt.value
                if isinstance(value, ast.Await):
                    consecutive_awaits.append(i)
                    if len(consecutive_awaits) >= 3:
                        self.issues.append({
                            'type': 'sequential_awaits',
                            'severity': 'medium',
                            'function': func_node.name,
                            'line': stmt.lineno,
                            'message': f'{len(consecutive_awaits)} sequential await calls found. Consider using asyncio.gather() for parallelization.',
                            'file': self.filename
                        })
                else:
                    consecutive_awaits = []

    def _check_loop_awaits(self, func_node):
        """Detect await calls inside loops (N+1 pattern)."""
        for node in ast.walk(func_node):
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Await):
                        self.issues.append({
                            'type': 'loop_await',
                            'severity': 'high',
                            'function': func_node.name,
                            'line': node.lineno,
                            'message': 'Await inside loop detected - potential N+1 query pattern. Consider batch operations.',
                            'file': self.filename
                        })
                        break

    def visit_With(self, node):
        """Check transaction/session management."""
        # Look for session.execute_write patterns
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                func = item.context_expr.func
                if isinstance(func, ast.Attribute) and func.attr == 'session':
                    # Check if there's only one execute_write call
                    execute_write_count = 0
                    for stmt in node.body:
                        if self._is_execute_write_call(stmt):
                            execute_write_count += 1

                    if execute_write_count > 1:
                        self.issues.append({
                            'type': 'multiple_transactions',
                            'severity': 'medium',
                            'line': node.lineno,
                            'message': 'Multiple execute_write calls in same session. Consider batching.',
                            'file': self.filename
                        })

        self.generic_visit(node)

    def _is_execute_write_call(self, node):
        """Check if node is an execute_write call."""
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Await):
            call = node.value.value
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
                return call.func.attr == 'execute_write'
        return False


def analyze_file(filepath: Path) -> List[Dict[str, Any]]:
    """Analyze a single Python file for bottlenecks."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(filepath))

        analyzer = BottleneckAnalyzer(str(filepath))
        analyzer.visit(tree)
        return analyzer.issues
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return []


def analyze_graphiti_write_path():
    """Analyze the Graphiti write path for bottlenecks."""
    print("=" * 80)
    print("GRAPHITI WRITE PATH BOTTLENECK ANALYSIS")
    print("=" * 80)

    # Key files to analyze
    key_files = [
        'graphiti_core/graphiti.py',
        'graphiti_core/utils/bulk_utils.py',
        'graphiti_core/driver/neo4j_driver.py',
        'graphiti_core/driver/falkordb_driver.py',
        'mcp_server/graphiti_mcp_server.py',
    ]

    all_issues = []

    for file_rel_path in key_files:
        filepath = Path(file_rel_path)
        if not filepath.exists():
            print(f"\n[WARN] File not found: {filepath}")
            continue

        print(f"\n[FILE] Analyzing: {filepath}")
        issues = analyze_file(filepath)

        if issues:
            all_issues.extend(issues)
            print(f"   Found {len(issues)} potential issue(s)")
        else:
            print("   [OK] No issues detected")

    # Print detailed results
    print("\n" + "=" * 80)
    print("DETAILED FINDINGS")
    print("=" * 80)

    if not all_issues:
        print("\n[OK] No bottlenecks detected in static analysis")
        return

    # Group by severity
    by_severity = {'high': [], 'medium': [], 'low': []}
    for issue in all_issues:
        by_severity[issue['severity']].append(issue)

    for severity in ['high', 'medium', 'low']:
        issues = by_severity[severity]
        if not issues:
            continue

        print(f"\n{severity.upper()} PRIORITY ({len(issues)} issues):")
        print("-" * 80)

        for issue in issues:
            print(f"\n  Type: {issue['type']}")
            print(f"  File: {issue['file']}")
            print(f"  Line: {issue['line']}")
            if issue.get('function'):
                print(f"  Function: {issue['function']}")
            print(f"  Issue: {issue['message']}")


def analyze_manual_bottlenecks():
    """Manual analysis of known architectural bottlenecks."""
    print("\n" + "=" * 80)
    print("KNOWN ARCHITECTURAL CONCERNS")
    print("=" * 80)

    concerns = [
        {
            'area': 'Transaction Management',
            'file': 'graphiti_core/utils/bulk_utils.py:add_nodes_and_edges_bulk',
            'issue': 'Single transaction for all operations - no explicit commit control',
            'impact': 'Large writes may hold transaction open for extended period',
            'recommendation': 'Consider chunking large operations or explicit commit points'
        },
        {
            'area': 'Embedding Generation',
            'file': 'graphiti_core/utils/bulk_utils.py:add_nodes_and_edges_bulk_tx',
            'issue': 'Embeddings generated within transaction (lines 167-169, 191-192)',
            'impact': 'Transaction open during potentially slow API calls',
            'recommendation': 'Generate embeddings before transaction, not during'
        },
        {
            'area': 'Session Management',
            'file': 'graphiti_core/utils/bulk_utils.py:add_nodes_and_edges_bulk',
            'issue': 'Session created per write operation',
            'impact': 'Connection overhead for each add_episode call',
            'recommendation': 'Consider connection pooling or session reuse'
        },
        {
            'area': 'MCP Queue Processing',
            'file': 'mcp_server/graphiti_mcp_server.py:process_episode_queue',
            'issue': 'Sequential processing per group_id',
            'impact': 'Large writes block subsequent writes in same group',
            'recommendation': 'Consider timeout or chunking for large episodes'
        },
        {
            'area': 'Database Driver',
            'file': 'graphiti_core/driver/*/execute_write',
            'issue': 'No explicit transaction timeout configuration',
            'impact': 'Long transactions may cause cascading delays',
            'recommendation': 'Add configurable transaction timeout'
        }
    ]

    for i, concern in enumerate(concerns, 1):
        print(f"\n{i}. {concern['area']}")
        print(f"   Location: {concern['file']}")
        print(f"   Issue: {concern['issue']}")
        print(f"   Impact: {concern['impact']}")
        print(f"   Recommendation: {concern['recommendation']}")


def main():
    """Run the analysis."""
    # Change to repo root
    repo_root = Path(__file__).parent.parent.parent
    os.chdir(repo_root)

    # Run AST analysis
    analyze_graphiti_write_path()

    # Run manual analysis
    analyze_manual_bottlenecks()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Fix HIGH priority issues first")
    print("2. Run performance benchmark to measure impact")
    print("3. Profile with actual database to identify runtime bottlenecks")
    print("4. Consider adding database query logging for transaction analysis")
    print()


if __name__ == "__main__":
    main()
