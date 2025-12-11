# Intelligent Session Summarization - Specification v1.0

**Version**: 1.0.0-draft
**Status**: Design Specification
**Authors**: Human + Claude Agent
**Date**: 2025-12-11
**Related**: GLOBAL_SESSION_TRACKING_SPEC_v2.0.md
**Sprint**: v2.0.0/global-session-tracking

---

## Executive Summary

This specification defines an enhancement to Graphiti's session summarization system that replaces discrete session type classification with a **multi-dimensional activity vector** and introduces **LLM-inferred tool classification** for unknown MCP servers and arbitrary bash commands.

### Key Changes

- Replace discrete `SessionType` enum with continuous `ActivityVector` (8 dimensions)
- Add LLM-based tool classification for unknown MCP tools and bash commands
- Implement priority-weighted extraction based on activity intensity
- Add `key_decisions` and `errors_resolved` fields to session summaries
- Support arbitrary tooling ecosystems without hard-coded mappings

### Problem Statement

The current session summarization system has two critical limitations:

1. **Discrete Classification Failure**: Sessions rarely fit one category (e.g., "debugging" vs "configuration" when fixing a config-caused bug)
2. **Hard-Coded Tool Mappings**: Cannot classify unknown MCP servers or user-installed CLI tools

---

## Table of Contents

1. [Design Rationale](#1-design-rationale)
2. [Activity Vector Model](#2-activity-vector-model)
3. [Tool Classification System](#3-tool-classification-system)
4. [Enhanced Session Summary Schema](#4-enhanced-session-summary-schema)
5. [Extraction Priority Algorithm](#5-extraction-priority-algorithm)
6. [Template Enhancements](#6-template-enhancements)
7. [Implementation Requirements](#7-implementation-requirements)
8. [Configuration Schema](#8-configuration-schema)
9. [Testing Requirements](#9-testing-requirements)
10. [Migration Guide](#10-migration-guide)

---

## 1. Design Rationale

### 1.1 Why Discrete Classification Fails

The original proposal used a discrete `SessionType` enum:

```python
class SessionType(Enum):
    IMPLEMENTATION = "implementation"
    DEBUGGING = "debugging"
    CONFIGURATION = "configuration"
    EXPLORATION = "exploration"
    # ...
```

**Problems identified during design review:**

1. **False dichotomies**: A session fixing a config-caused bug is both "debugging" AND "configuration"
2. **Temporal blindness**: Sessions often shift focus mid-conversation
3. **Edge case explosion**: Adding categories for every combination (debug+config, explore+implement) doesn't scale
4. **Misclassification cascades**: Wrong category → wrong extraction priorities → poor summaries

### 1.2 Why Hard-Coded Tool Mappings Fail

Original tool signal detection:

```python
TOOL_SIGNALS = {
    'Write': {'building': 0.3, 'configuring': 0.2},
    'Edit': {'building': 0.2, 'fixing': 0.3},
    # ... hard-coded for known tools
}
```

**Problems:**

1. **MCP server explosion**: Users install unknown MCP servers (serena, context7, gptr-mcp, custom servers)
2. **Bash command diversity**: `pytest`, `npm`, `docker`, `kubectl`, custom scripts, installed CLIs
3. **Maintenance burden**: Every new tool requires code updates
4. **Zero-shot failure**: Unknown tools contribute no signal

### 1.3 Solution: Multi-Dimensional + LLM Inference

**Activity Vector**: Continuous 0.0-1.0 values across 8 dimensions, not mutually exclusive

**LLM Tool Classification**: Classify unknown tools at runtime, cache results for efficiency

This enables:
- Sessions can be 80% fixing + 70% configuring simultaneously
- New MCP servers work automatically
- Arbitrary bash commands are understood
- Self-improving system (cache learns over time)

---

## 2. Activity Vector Model

### 2.1 Core Model

```python
from pydantic import BaseModel, Field
from typing import Literal

class ActivityVector(BaseModel):
    """
    Multi-dimensional representation of session activities.

    Each dimension is 0.0-1.0 indicating intensity of that activity type.
    Dimensions are NOT mutually exclusive - a session can score high on multiple.

    Example: Config-caused bug debugging session
        building=0.1, fixing=0.8, configuring=0.7, exploring=0.4, testing=0.5

    This captures: "Primarily debugging (0.8), heavily involving config (0.7),
    with investigation (0.4) and verification (0.5)"
    """

    # Core activity dimensions
    building: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Creating new functionality, features, files"
    )
    fixing: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Resolving errors, bugs, issues"
    )
    configuring: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Setup, environment, settings, dependencies"
    )
    exploring: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Research, learning, discovery, investigation"
    )
    refactoring: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Restructuring without new features"
    )
    reviewing: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Analysis, code review, audit"
    )
    testing: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Writing/running tests, verification"
    )
    documenting: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Writing docs, comments, READMEs"
    )

    @property
    def dominant_activities(self) -> list[str]:
        """Return activities above threshold (0.3), sorted by intensity."""
        DIMENSIONS = [
            'building', 'fixing', 'configuring', 'exploring',
            'refactoring', 'reviewing', 'testing', 'documenting'
        ]
        activities = [(name, getattr(self, name)) for name in DIMENSIONS]
        return [
            name for name, val
            in sorted(activities, key=lambda x: -x[1])
            if val >= 0.3
        ]

    @property
    def primary_activity(self) -> str:
        """Return the highest-intensity activity."""
        dominant = self.dominant_activities
        return dominant[0] if dominant else "mixed"

    @property
    def activity_profile(self) -> str:
        """Human-readable profile string."""
        dominant = self.dominant_activities
        if not dominant:
            return "mixed activity"
        parts = [f"{name} ({getattr(self, name):.1f})" for name in dominant[:4]]
        return ", ".join(parts)

    def to_dict(self) -> dict[str, float]:
        """Export as dictionary for serialization."""
        return {
            'building': self.building,
            'fixing': self.fixing,
            'configuring': self.configuring,
            'exploring': self.exploring,
            'refactoring': self.refactoring,
            'reviewing': self.reviewing,
            'testing': self.testing,
            'documenting': self.documenting,
        }

    @classmethod
    def from_signals(cls, signals: dict[str, float]) -> "ActivityVector":
        """
        Create from raw signal accumulation, normalizing to 0-1 range.

        Args:
            signals: Raw accumulated signals (may exceed 1.0)

        Returns:
            Normalized ActivityVector
        """
        if not signals:
            return cls()

        max_val = max(signals.values()) or 1.0
        normalized = {k: min(v / max_val, 1.0) for k, v in signals.items()}

        # Ensure all dimensions present
        DIMENSIONS = [
            'building', 'fixing', 'configuring', 'exploring',
            'refactoring', 'reviewing', 'testing', 'documenting'
        ]
        for dim in DIMENSIONS:
            if dim not in normalized:
                normalized[dim] = 0.0

        return cls(**normalized)
```

### 2.2 Activity Vector Detection

Detection uses multiple signal sources combined:

```python
class ActivityDetector:
    """
    Detects session activity vector from message content and tool usage.

    Signal sources:
    1. User intent keywords (what user asked for)
    2. Tool usage patterns (what tools were invoked)
    3. Error patterns (presence of errors/fixes)
    4. File patterns (what types of files were touched)
    """

    # Keyword patterns for user intent detection
    INTENT_KEYWORDS: dict[str, list[str]] = {
        'building': [
            'implement', 'add', 'create', 'build', 'new feature',
            'develop', 'make', 'write'
        ],
        'fixing': [
            'fix', 'bug', 'error', 'broken', 'not working', 'issue',
            'debug', 'resolve', 'problem', 'crash', 'fail'
        ],
        'configuring': [
            'config', 'setup', 'install', 'environment', 'settings',
            '.env', 'dependency', 'package', 'configure'
        ],
        'exploring': [
            'how does', 'what is', 'find', 'search', 'understand',
            'explain', 'where', 'why', 'show me', 'look at'
        ],
        'refactoring': [
            'refactor', 'restructure', 'clean up', 'reorganize',
            'rename', 'move', 'simplify', 'extract'
        ],
        'reviewing': [
            'review', 'check', 'audit', 'analyze', 'examine',
            'inspect', 'evaluate', 'assess'
        ],
        'testing': [
            'test', 'pytest', 'unittest', 'coverage', 'verify',
            'spec', 'assert', 'mock', 'fixture'
        ],
        'documenting': [
            'document', 'readme', 'comment', 'explain', 'docstring',
            'markdown', 'guide', 'tutorial'
        ],
    }

    # File patterns that indicate certain activities
    FILE_PATTERNS: dict[str, list[str]] = {
        'configuring': [
            '.env', 'config.', '.json', '.yaml', '.toml',
            'settings', 'package.json', 'requirements.txt',
            'Dockerfile', 'docker-compose', '.gitignore'
        ],
        'testing': [
            'test_', '_test.', '.spec.', 'conftest.py',
            '__tests__', '.test.ts', '.test.js'
        ],
        'documenting': [
            'README', 'CHANGELOG', 'CONTRIBUTING', '.md',
            'docs/', 'documentation/'
        ],
    }

    def __init__(self, tool_classifier: "UnifiedToolClassifier"):
        self.tool_classifier = tool_classifier

    async def detect(self, messages: list[dict]) -> ActivityVector:
        """
        Detect activity vector from session messages.

        Args:
            messages: List of message dicts with 'role', 'content', etc.

        Returns:
            ActivityVector representing session activity profile
        """
        signals: dict[str, float] = {}

        # Signal 1: User intent keywords
        user_text = " ".join(
            m.get('content', '')
            for m in messages
            if m.get('role') == 'user'
        ).lower()

        for activity, keywords in self.INTENT_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in user_text)
            if matches > 0:
                # Cap contribution at 0.5 from keywords alone
                signals[activity] = signals.get(activity, 0) + min(matches * 0.15, 0.5)

        # Signal 2: Tool usage (via LLM classifier)
        tool_messages = [m for m in messages if m.get('role') == 'tool']
        if tool_messages:
            _, classifications = await self.tool_classifier.classify_session(
                tool_messages
            )
            for cls in classifications:
                for activity, signal in cls.activity_signals.items():
                    signals[activity] = signals.get(activity, 0) + signal * 0.3

        # Signal 3: Error patterns
        all_text = " ".join(m.get('content', '') for m in messages).lower()
        error_indicators = ['error', 'exception', 'failed', 'traceback', 'crash']
        error_count = sum(all_text.count(ind) for ind in error_indicators)
        if error_count > 3:
            signals['fixing'] = signals.get('fixing', 0) + 0.3

        # Signal 4: File patterns
        for activity, patterns in self.FILE_PATTERNS.items():
            pattern_count = sum(1 for p in patterns if p.lower() in all_text)
            if pattern_count > 2:
                signals[activity] = signals.get(activity, 0) + 0.25

        return ActivityVector.from_signals(signals)
```

---

## 3. Tool Classification System

### 3.1 Classification Schema

```python
from enum import Enum

class ToolIntent(str, Enum):
    """What the tool invocation is trying to accomplish."""
    CREATE = "create"           # Making new things
    MODIFY = "modify"           # Changing existing things
    DELETE = "delete"           # Removing things
    READ = "read"               # Inspecting/retrieving information
    SEARCH = "search"           # Finding things
    EXECUTE = "execute"         # Running processes, tests, builds
    CONFIGURE = "configure"     # Setting up environment, config
    COMMUNICATE = "communicate" # External APIs, notifications
    VALIDATE = "validate"       # Checking correctness, linting, testing
    TRANSFORM = "transform"     # Converting formats, processing data


class ToolDomain(str, Enum):
    """What domain/category the tool operates in."""
    FILESYSTEM = "filesystem"
    CODE = "code"
    DATABASE = "database"
    NETWORK = "network"
    PROCESS = "process"
    VERSION_CONTROL = "version_control"
    PACKAGE = "package"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    MEMORY = "memory"
    UNKNOWN = "unknown"


class ToolClassification(BaseModel):
    """LLM-inferred classification of a tool invocation."""

    tool_name: str
    tool_params: dict | None = None

    # Inferred classification
    intent: ToolIntent
    domain: ToolDomain

    # Confidence and reasoning
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

    # Activity signal contributions
    activity_signals: dict[str, float] = Field(default_factory=dict)
```

### 3.2 LLM Classification Prompt

```python
TOOL_CLASSIFICATION_PROMPT = """
Classify these tool invocations by their intent and domain.

For each tool call, determine:

1. **Intent**: What is the tool trying to accomplish?
   - create: Making new things (files, resources, entities)
   - modify: Changing existing things
   - delete: Removing things
   - read: Inspecting/retrieving information
   - search: Finding things
   - execute: Running processes, tests, builds
   - configure: Setting up environment, config
   - communicate: External APIs, notifications
   - validate: Checking correctness, linting, testing
   - transform: Converting formats, processing data

2. **Domain**: What area does it operate in?
   - filesystem, code, database, network, process,
   - version_control, package, documentation, testing, memory, unknown

3. **Activity Signals**: What does this tell us about the session?
   Rate 0.0-1.0 contribution to each activity dimension:
   - building: Creating new functionality
   - fixing: Resolving errors/bugs
   - configuring: Setup, environment, settings
   - exploring: Research, learning, discovery
   - refactoring: Restructuring existing code
   - reviewing: Analysis, audit
   - testing: Writing/running tests
   - documenting: Writing docs

## Tool Invocations to Classify:

{tool_calls_json}

## Response Format (JSON):
```json
{
  "classifications": [
    {
      "tool_name": "mcp__serena__find_symbol",
      "intent": "search",
      "domain": "code",
      "confidence": 0.95,
      "reasoning": "Searching for code symbols by name",
      "activity_signals": {"exploring": 0.4, "reviewing": 0.3, "fixing": 0.2}
    }
  ]
}
```

Focus on:
- Tool name patterns (mcp__*, bash commands, etc.)
- Parameter values (file paths, queries, flags)
- Common tool purposes you can infer
"""
```

### 3.3 Bash Command Analysis

```python
BASH_CLASSIFICATION_PROMPT = """
Analyze this bash command and classify its intent.

Command: {command}

Determine:
1. **Base command**: The primary executable (e.g., "git", "npm", "python")
2. **Subcommand**: If applicable (e.g., "install", "commit", "run")
3. **Intent**: What is this trying to accomplish?
4. **Domain**: What area does it operate in?
5. **Activity signals**: What does this tell us about the session?

Consider:
- This could be a standard Unix command, a package manager, a custom CLI tool,
  a Python/Node script, or any installed software
- Look at the full command including flags and arguments for context
- Common patterns: npm install = configuring, pytest = testing, git commit = version_control

## Response Format (JSON):
```json
{
  "raw_command": "pytest tests/ -v --cov=src",
  "base_command": "pytest",
  "subcommand": null,
  "flags": ["-v", "--cov=src"],
  "targets": ["tests/"],
  "intent": "validate",
  "domain": "testing",
  "confidence": 0.95,
  "reasoning": "pytest with coverage flags indicates test validation",
  "activity_signals": {"testing": 0.8, "fixing": 0.2}
}
```
"""


class BashCommandClassification(BaseModel):
    """Classification of a bash command invocation."""

    raw_command: str

    # Parsed structure
    base_command: str
    subcommand: str | None = None
    flags: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)

    # Classification
    intent: ToolIntent
    domain: ToolDomain
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    activity_signals: dict[str, float] = Field(default_factory=dict)
```

### 3.4 Caching Strategy

```python
class ToolClassifier:
    """
    Classifies tool invocations using LLM inference with multi-level caching.

    Cache hierarchy:
    1. Exact match: tool_name + params hash → cached result
    2. Tool name match: tool_name → base classification
    3. Heuristic: Name pattern → quick classification (no LLM)
    4. LLM inference: Full classification (expensive, cached after)

    Cost efficiency:
    - First session with new MCP server: 1 LLM call per unique tool
    - Subsequent sessions: 0 LLM calls (all cached)
    - Known patterns (git, npm, pytest): 0 LLM calls (heuristic)
    """

    def __init__(
        self,
        llm_client,
        cache_path: Path | None = None,
        heuristic_confidence_threshold: float = 0.7,
    ):
        self.llm_client = llm_client
        self.cache_path = cache_path
        self.heuristic_threshold = heuristic_confidence_threshold

        # In-memory caches
        self._exact_cache: dict[str, ToolClassification] = {}
        self._pattern_cache: dict[str, ToolClassification] = {}

        if cache_path and cache_path.exists():
            self._load_cache()

    def _make_cache_key(self, tool_name: str, params: dict | None) -> str:
        """Create deterministic cache key."""
        import hashlib
        import json

        if params:
            normalized = json.dumps(
                {k: v for k, v in sorted(params.items()) if v is not None},
                sort_keys=True
            )
        else:
            normalized = "{}"

        return f"{tool_name}::{hashlib.md5(normalized.encode()).hexdigest()[:8]}"

    def _try_heuristic(self, tool_name: str) -> ToolClassification | None:
        """
        Quick heuristic classification from tool name patterns.
        Returns None if uncertain (triggers LLM inference).
        """
        name_lower = tool_name.lower()

        # Intent patterns (keyword → (intent, confidence))
        INTENT_PATTERNS = {
            ('read', 'get', 'fetch', 'list', 'show', 'retrieve'):
                (ToolIntent.READ, 0.7),
            ('write', 'create', 'add', 'new', 'insert', 'make'):
                (ToolIntent.CREATE, 0.7),
            ('edit', 'update', 'modify', 'replace', 'patch', 'change'):
                (ToolIntent.MODIFY, 0.7),
            ('delete', 'remove', 'clear', 'drop', 'purge'):
                (ToolIntent.DELETE, 0.8),
            ('search', 'find', 'grep', 'query', 'lookup', 'locate'):
                (ToolIntent.SEARCH, 0.8),
            ('run', 'exec', 'execute', 'invoke', 'call', 'start'):
                (ToolIntent.EXECUTE, 0.7),
            ('test', 'check', 'validate', 'verify', 'lint', 'assert'):
                (ToolIntent.VALIDATE, 0.7),
            ('config', 'setup', 'init', 'install', 'configure'):
                (ToolIntent.CONFIGURE, 0.7),
        }

        # Domain patterns
        DOMAIN_PATTERNS = {
            ('file', 'dir', 'path', 'folder', 'fs'): ToolDomain.FILESYSTEM,
            ('symbol', 'code', 'ast', 'syntax', 'serena'): ToolDomain.CODE,
            ('git', 'commit', 'branch', 'merge', 'push', 'pull'): ToolDomain.VERSION_CONTROL,
            ('db', 'database', 'sql', 'query', 'neo4j', 'graphiti'): ToolDomain.DATABASE,
            ('http', 'api', 'fetch', 'request', 'url', 'web'): ToolDomain.NETWORK,
            ('bash', 'shell', 'process', 'cmd', 'terminal'): ToolDomain.PROCESS,
            ('npm', 'pip', 'cargo', 'package', 'install', 'uv'): ToolDomain.PACKAGE,
            ('test', 'pytest', 'jest', 'spec', 'coverage'): ToolDomain.TESTING,
            ('memory', 'remember', 'episode', 'knowledge', 'graphiti'): ToolDomain.MEMORY,
            ('doc', 'readme', 'comment', 'markdown'): ToolDomain.DOCUMENTATION,
        }

        # Find matches
        intent = None
        intent_conf = 0.5
        for keywords, (int_val, conf) in INTENT_PATTERNS.items():
            if any(kw in name_lower for kw in keywords):
                intent = int_val
                intent_conf = conf
                break

        domain = ToolDomain.UNKNOWN
        for keywords, dom_val in DOMAIN_PATTERNS.items():
            if any(kw in name_lower for kw in keywords):
                domain = dom_val
                break

        if intent and intent_conf >= self.heuristic_threshold:
            return ToolClassification(
                tool_name=tool_name,
                intent=intent,
                domain=domain,
                confidence=intent_conf * 0.8,  # Discount for heuristic
                reasoning=f"Heuristic: name pattern '{tool_name}'",
                activity_signals=self._intent_to_signals(intent, domain),
            )

        return None  # Uncertain - needs LLM

    def _intent_to_signals(
        self,
        intent: ToolIntent,
        domain: ToolDomain
    ) -> dict[str, float]:
        """Convert intent+domain to activity signals (fallback heuristic)."""
        INTENT_SIGNALS = {
            ToolIntent.CREATE: {"building": 0.4, "configuring": 0.2},
            ToolIntent.MODIFY: {"fixing": 0.3, "refactoring": 0.3, "building": 0.2},
            ToolIntent.DELETE: {"refactoring": 0.3, "fixing": 0.2},
            ToolIntent.READ: {"exploring": 0.4, "reviewing": 0.3},
            ToolIntent.SEARCH: {"exploring": 0.5, "fixing": 0.2},
            ToolIntent.EXECUTE: {"testing": 0.3, "building": 0.2},
            ToolIntent.CONFIGURE: {"configuring": 0.6},
            ToolIntent.VALIDATE: {"testing": 0.5, "fixing": 0.2},
            ToolIntent.COMMUNICATE: {"building": 0.2},
            ToolIntent.TRANSFORM: {"building": 0.3, "refactoring": 0.2},
        }

        signals = INTENT_SIGNALS.get(intent, {}).copy()

        # Domain adjustments
        if domain == ToolDomain.TESTING:
            signals["testing"] = signals.get("testing", 0) + 0.3
        elif domain == ToolDomain.DOCUMENTATION:
            signals["documenting"] = signals.get("documenting", 0) + 0.4
        elif domain == ToolDomain.VERSION_CONTROL:
            signals["building"] = signals.get("building", 0) + 0.1

        return signals

    async def classify_batch(
        self,
        tool_calls: list[dict],
        use_cache: bool = True,
    ) -> list[ToolClassification]:
        """
        Classify a batch of tool calls, using cache where possible.
        Falls back to LLM for unknown tools.
        """
        results = []
        needs_llm = []
        needs_llm_indices = []

        for i, call in enumerate(tool_calls):
            name = call.get("name", "")
            params = call.get("params")

            # Level 1: Exact cache
            cache_key = self._make_cache_key(name, params)
            if use_cache and cache_key in self._exact_cache:
                results.append(self._exact_cache[cache_key])
                continue

            # Level 2: Pattern cache (name only)
            if use_cache and name in self._pattern_cache:
                base = self._pattern_cache[name].model_copy()
                base.tool_params = params
                results.append(base)
                continue

            # Level 3: Heuristic
            heuristic = self._try_heuristic(name)
            if heuristic:
                heuristic.tool_params = params
                results.append(heuristic)
                self._pattern_cache[name] = heuristic
                continue

            # Level 4: Need LLM
            results.append(None)  # Placeholder
            needs_llm.append(call)
            needs_llm_indices.append(i)

        # Batch LLM inference for unknowns
        if needs_llm:
            llm_results = await self._llm_classify(needs_llm)
            for idx, (call, classification) in enumerate(zip(needs_llm, llm_results)):
                result_idx = needs_llm_indices[idx]
                results[result_idx] = classification

                # Cache for future
                cache_key = self._make_cache_key(call.get("name", ""), call.get("params"))
                self._exact_cache[cache_key] = classification
                self._pattern_cache[call.get("name", "")] = classification

        return results

    async def _llm_classify(
        self,
        tool_calls: list[dict]
    ) -> list[ToolClassification]:
        """Use LLM to classify unknown tools."""
        import json

        prompt = TOOL_CLASSIFICATION_PROMPT.format(
            tool_calls_json=json.dumps(tool_calls, indent=2)
        )

        response = await self.llm_client.generate_structured(
            prompt=prompt,
            response_model=ToolClassificationBatch,
        )

        return response.classifications

    def save_cache(self):
        """Persist cache to disk."""
        if self.cache_path:
            import json
            cache_data = {
                "exact": {k: v.model_dump() for k, v in self._exact_cache.items()},
                "pattern": {k: v.model_dump() for k, v in self._pattern_cache.items()},
            }
            self.cache_path.write_text(json.dumps(cache_data, indent=2))

    def _load_cache(self):
        """Load cache from disk."""
        import json
        if self.cache_path and self.cache_path.exists():
            data = json.loads(self.cache_path.read_text())
            self._exact_cache = {
                k: ToolClassification(**v) for k, v in data.get("exact", {}).items()
            }
            self._pattern_cache = {
                k: ToolClassification(**v) for k, v in data.get("pattern", {}).items()
            }
```

### 3.5 Unified Classifier

```python
class UnifiedToolClassifier:
    """
    Unified classifier for all tool invocations:
    - MCP tools (known and unknown servers)
    - Bash commands (arbitrary software)
    - Native Claude tools (Read, Write, etc.)
    """

    def __init__(
        self,
        llm_client,
        cache_path: Path | None = None,
    ):
        self.tool_classifier = ToolClassifier(llm_client, cache_path)
        self.bash_analyzer = BashAnalyzer(llm_client)

    async def classify_message(
        self,
        message: dict,
    ) -> ToolClassification | BashCommandClassification:
        """Classify a single tool call message."""
        tool_name = message.get("name", "")
        params = message.get("params", {})

        if tool_name.lower() == "bash":
            command = params.get("command", "")
            return await self.bash_analyzer.classify(command)
        else:
            results = await self.tool_classifier.classify_batch(
                [{"name": tool_name, "params": params}]
            )
            return results[0]

    async def classify_session(
        self,
        messages: list[dict],
    ) -> tuple[ActivityVector, list[ToolClassification | BashCommandClassification]]:
        """
        Classify all tool calls in a session and compute activity vector.

        Returns:
            Tuple of (ActivityVector, list of classifications)
        """
        tool_messages = [m for m in messages if m.get("role") == "tool"]

        classifications = []
        for msg in tool_messages:
            cls = await self.classify_message(msg)
            classifications.append(cls)

        # Aggregate into activity signals
        aggregate: dict[str, float] = {}
        for cls in classifications:
            for activity, signal in cls.activity_signals.items():
                aggregate[activity] = aggregate.get(activity, 0) + signal

        return ActivityVector.from_signals(aggregate), classifications
```

---

## 4. Enhanced Session Summary Schema

### 4.1 New Fields

```python
class DecisionRecord(BaseModel):
    """Structured decision with rationale."""
    decision: str          # "Used RS256 over HS256 for JWT signing"
    rationale: str         # "RS256 is more secure for production"
    alternatives: list[str] | None = None  # ["HS256", "EdDSA"]


class ErrorResolution(BaseModel):
    """Structured error fix record."""
    error: str             # "ImportError: No module named 'foo'"
    root_cause: str        # "Missing dependency in requirements.txt"
    fix: str               # "Added foo==1.2.3 to requirements.txt"
    verification: str      # "Ran tests, all passing"


class ConfigChange(BaseModel):
    """Configuration change record."""
    file: str              # ".env"
    setting: str           # "JWT_EXPIRY"
    old_value: str | None  # "60"
    new_value: str         # "3600"
    reason: str            # "Fix timeout - was minutes, now seconds"


class TestSummary(BaseModel):
    """Test execution summary."""
    framework: str         # "pytest"
    total: int             # 47
    passed: int            # 45
    failed: int            # 2
    skipped: int           # 0
    coverage_pct: float | None = None  # 87.3
    failed_tests: list[str] | None = None  # ["test_auth_timeout"]
```

### 4.2 Enhanced Summary Schema

```python
class EnhancedSessionSummary(BaseModel):
    """
    Session summary with multi-dimensional activity tracking and
    context-aware extraction.
    """

    # === ALWAYS REQUIRED ===
    activity_vector: ActivityVector
    objective: str  # 1-2 sentences
    outcome: Literal["completed", "blocked", "in_progress", "abandoned"]

    # === DYNAMICALLY INCLUDED (based on activity vector) ===

    # High-value across most activities
    completed_tasks: list[str] | None = None
    key_decisions: list[DecisionRecord] | None = None
    next_steps: list[str] | None = None

    # Fixing/debugging specific
    errors_resolved: list[ErrorResolution] | None = None
    root_cause_analysis: str | None = None

    # Configuring specific
    config_changes: list[ConfigChange] | None = None

    # Exploring specific
    discoveries: list[str] | None = None

    # Testing specific
    test_results: TestSummary | None = None

    # Always useful context
    files_modified: list[str] | None = None
    mcp_tools_used: list[str] | None = None

    # Metadata
    session_file: str | None = None
    message_count: int | None = None
    duration_minutes: int | None = None

    def to_markdown(self) -> str:
        """Render summary as markdown."""
        lines = []

        # Header with activity profile
        lines.append(f"# Session Summary")
        lines.append("")
        lines.append(f"**Activity Profile**: {self.activity_vector.activity_profile}")
        lines.append(f"**Outcome**: {self.outcome}")
        lines.append("")

        # Objective
        lines.append("## Objective")
        lines.append(self.objective)
        lines.append("")

        # Completed tasks
        if self.completed_tasks:
            lines.append("## Completed")
            for task in self.completed_tasks:
                lines.append(f"- {task}")
            lines.append("")

        # Key decisions (critical for preventing repeated debates)
        if self.key_decisions:
            lines.append("## Key Decisions")
            for dec in self.key_decisions:
                lines.append(f"- **{dec.decision}**: {dec.rationale}")
                if dec.alternatives:
                    lines.append(f"  - Alternatives considered: {', '.join(dec.alternatives)}")
            lines.append("")

        # Errors resolved (critical for debugging sessions)
        if self.errors_resolved:
            lines.append("## Errors Resolved")
            for err in self.errors_resolved:
                lines.append(f"### {err.error[:60]}...")
                lines.append(f"- **Root cause**: {err.root_cause}")
                lines.append(f"- **Fix**: {err.fix}")
                lines.append(f"- **Verification**: {err.verification}")
            lines.append("")

        # Config changes
        if self.config_changes:
            lines.append("## Configuration Changes")
            lines.append("| File | Setting | Change | Reason |")
            lines.append("|------|---------|--------|--------|")
            for cfg in self.config_changes:
                old = cfg.old_value or "(none)"
                lines.append(f"| {cfg.file} | {cfg.setting} | {old} → {cfg.new_value} | {cfg.reason} |")
            lines.append("")

        # Test results
        if self.test_results:
            tr = self.test_results
            lines.append("## Test Results")
            lines.append(f"- **Framework**: {tr.framework}")
            lines.append(f"- **Results**: {tr.passed}/{tr.total} passed")
            if tr.failed > 0 and tr.failed_tests:
                lines.append(f"- **Failed**: {', '.join(tr.failed_tests)}")
            if tr.coverage_pct:
                lines.append(f"- **Coverage**: {tr.coverage_pct:.1f}%")
            lines.append("")

        # Files modified
        if self.files_modified:
            lines.append("## Files Modified")
            for f in self.files_modified:
                lines.append(f"- `{f}`")
            lines.append("")

        # Next steps
        if self.next_steps:
            lines.append("## Next Steps")
            for step in self.next_steps:
                lines.append(f"- {step}")
            lines.append("")

        return "\n".join(lines)
```

---

## 5. Extraction Priority Algorithm

### 5.1 Field Affinities

Each extraction field has "affinity" weights to activity dimensions:

```python
EXTRACTION_AFFINITIES: dict[str, dict[str, float]] = {
    # Field name → {activity_dimension: affinity_weight}

    "completed_tasks": {
        "building": 1.0,
        "fixing": 0.8,
        "configuring": 0.7,
        "refactoring": 0.9,
        "testing": 0.6,
    },

    "key_decisions": {
        "building": 1.0,
        "configuring": 0.9,
        "refactoring": 0.8,
        "fixing": 0.6,
        "exploring": 0.5,
    },

    "errors_resolved": {
        "fixing": 1.0,
        "configuring": 0.7,
        "testing": 0.5,
    },

    "root_cause_analysis": {
        "fixing": 1.0,
        "exploring": 0.7,
        "reviewing": 0.6,
    },

    "discoveries": {
        "exploring": 1.0,
        "reviewing": 0.8,
        "documenting": 0.5,
    },

    "files_modified": {
        "building": 0.9,
        "fixing": 0.8,
        "configuring": 0.7,
        "refactoring": 0.9,
        "testing": 0.5,
    },

    "config_changes": {
        "configuring": 1.0,
        "fixing": 0.4,
    },

    "test_results": {
        "testing": 1.0,
        "fixing": 0.7,
        "building": 0.6,
    },

    "next_steps": {
        "building": 0.8,
        "fixing": 0.7,
        "configuring": 0.5,
        "exploring": 0.4,
    },

    "mcp_tools_used": {
        "fixing": 0.6,  # Tools used are diagnostic for debugging
        "exploring": 0.7,
        "building": 0.3,  # Less important when building
    },
}
```

### 5.2 Priority Computation

```python
def compute_extraction_priority(
    field: str,
    activity: ActivityVector,
) -> float:
    """
    Compute priority for extracting a field based on session activity mix.

    Returns:
        0.0-1.0 where higher = more important to include in summary
    """
    affinities = EXTRACTION_AFFINITIES.get(field, {})

    if not affinities:
        return 0.5  # Default priority for unknown fields

    # Weighted combination: sum(activity_intensity * field_affinity)
    priority = 0.0
    for dimension, affinity in affinities.items():
        intensity = getattr(activity, dimension, 0.0)
        priority += intensity * affinity

    # Normalize
    max_possible = sum(affinities.values())
    return priority / max_possible if max_possible > 0 else 0.0


def get_extraction_fields(
    activity: ActivityVector,
    threshold: float = 0.3,
) -> list[str]:
    """
    Get list of fields to extract based on activity vector.

    Args:
        activity: Session activity vector
        threshold: Minimum priority to include field

    Returns:
        List of field names to extract, sorted by priority
    """
    priorities = [
        (field, compute_extraction_priority(field, activity))
        for field in EXTRACTION_AFFINITIES.keys()
    ]

    # Filter by threshold and sort by priority
    included = [
        (field, priority)
        for field, priority in priorities
        if priority >= threshold
    ]

    return [field for field, _ in sorted(included, key=lambda x: -x[1])]
```

### 5.3 Dynamic Prompt Generation

```python
def build_extraction_prompt(
    activity: ActivityVector,
    session_content: str,
    threshold: float = 0.3,
) -> str:
    """
    Build extraction prompt dynamically based on activity vector.

    High-priority fields get detailed extraction instructions.
    Low-priority fields are omitted or get minimal instructions.
    """
    fields = get_extraction_fields(activity, threshold)

    # Base prompt
    prompt_parts = [
        "Summarize this session into a structured format.",
        "",
        f"**Session Activity Profile**: {activity.activity_profile}",
        "",
        "Extract the following information (in order of importance):",
        "",
    ]

    # Field-specific instructions
    FIELD_INSTRUCTIONS = {
        "completed_tasks": "List specific tasks that were accomplished",
        "key_decisions": "Capture decisions made WITH rationale (why this choice?)",
        "errors_resolved": "For each error: what was it, root cause, how fixed, verified?",
        "root_cause_analysis": "If debugging, explain the root cause discovered",
        "config_changes": "List config file changes with before/after values",
        "test_results": "Summarize test execution results and failures",
        "discoveries": "Key insights or learnings from exploration",
        "files_modified": "List of files created/modified",
        "next_steps": "What should happen next?",
        "mcp_tools_used": "Which MCP tools were utilized?",
    }

    for i, field in enumerate(fields, 1):
        priority = compute_extraction_priority(field, activity)
        instruction = FIELD_INSTRUCTIONS.get(field, f"Extract {field}")
        prompt_parts.append(f"{i}. **{field}** (priority: {priority:.2f}): {instruction}")

    prompt_parts.extend([
        "",
        "## Session Content",
        "",
        session_content,
        "",
        "## Response Format",
        "Respond with a JSON object matching the EnhancedSessionSummary schema.",
    ])

    return "\n".join(prompt_parts)
```

---

## 6. Template Enhancements

### 6.1 Updated Default Templates

**default-user-messages.md** (updated):
```markdown
Summarize this user message in 1 paragraph or less.

**Context**: {context}

**Focus on**:
- What the user is asking for
- Key requirements or constraints
- Context or background provided

**Original message**:
{content}

**Summary** (preserve user intent, 1 paragraph or less):
```

**default-agent-messages.md** (updated):
```markdown
Summarize this agent response in 1 paragraph or less.

**Context**: {context}

**Focus on**:
- Main explanation or reasoning
- Decisions made or approaches taken
- Important context or caveats
- Follow-up actions planned

**Original response**:
{content}

**Summary** (reasoning and decisions, 1 paragraph or less):
```

### 6.2 New Session Summary Template

**default-session-summary.md** (new):
```markdown
Summarize this coding session into structured format.

**Activity Profile**: {activity_profile}

**Extract based on session activities**:

{dynamic_extraction_instructions}

**Session Content**:
{content}

**Response** (JSON matching EnhancedSessionSummary schema):
```

---

## 7. Implementation Requirements

### 7.1 Files to Create

| File | Purpose |
|------|---------|
| `graphiti_core/session_tracking/activity_vector.py` | ActivityVector model |
| `graphiti_core/session_tracking/tool_classifier.py` | Tool classification system |
| `graphiti_core/session_tracking/extraction_priority.py` | Priority algorithm |
| `graphiti_core/session_tracking/enhanced_summary.py` | EnhancedSessionSummary model |

### 7.2 Files to Modify

| File | Changes |
|------|---------|
| `graphiti_core/session_tracking/summarizer.py` | Use ActivityVector, dynamic prompts |
| `graphiti_core/session_tracking/prompts/*.md` | Update templates |
| `mcp_server/unified_config.py` | Add summarization config options |
| `graphiti.config.schema.json` | Add new config fields |

### 7.3 New Dependencies

```toml
# pyproject.toml additions
[project.optional-dependencies]
session-tracking = [
    "pyyaml>=6.0",  # For YAML frontmatter (already present)
]
```

---

## 8. Configuration Schema

### 8.1 Summarization Config

```python
class SummarizationConfig(BaseModel):
    """Configuration for intelligent session summarization."""

    auto_summarize: bool = Field(
        default=False,
        description="Enable LLM-powered summarization"
    )

    template: str | None = Field(
        default=None,
        description=(
            "Custom summarization template path. "
            "If None, uses dynamic extraction based on activity vector."
        )
    )

    type_detection: Literal["auto", "manual"] = Field(
        default="auto",
        description=(
            "Activity detection mode. "
            "'auto' infers from message content and tool usage. "
            "'manual' requires explicit activity_vector in config."
        )
    )

    extraction_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum priority score to include extraction field"
    )

    include_decisions: bool = Field(
        default=True,
        description="Extract key_decisions (prevents repeated debates)"
    )

    include_errors_resolved: bool = Field(
        default=True,
        description="Extract errors_resolved (debugging continuity)"
    )

    tool_classification_cache: str | None = Field(
        default=None,
        description=(
            "Path to tool classification cache file. "
            "If None, uses ~/.graphiti/tool_classification_cache.json"
        )
    )
```

### 8.2 JSON Example

```json
{
  "session_tracking": {
    "enabled": true,
    "auto_summarize": true,

    "summarization": {
      "template": null,
      "type_detection": "auto",
      "extraction_threshold": 0.3,
      "include_decisions": true,
      "include_errors_resolved": true,
      "tool_classification_cache": null
    },

    "filter": {
      "tool_calls": true,
      "tool_content": "default-tool-content.md",
      "user_messages": true,
      "agent_messages": true
    }
  }
}
```

---

## 9. Testing Requirements

### 9.1 Unit Tests

```python
# Activity Vector tests
def test_activity_vector_from_signals():
    signals = {"fixing": 0.8, "configuring": 0.7, "testing": 0.5}
    av = ActivityVector.from_signals(signals)
    assert av.fixing == 1.0  # Normalized to max
    assert av.configuring == 0.875  # 0.7/0.8
    assert av.primary_activity == "fixing"

def test_activity_vector_dominant_activities():
    av = ActivityVector(fixing=0.8, configuring=0.7, testing=0.5, exploring=0.2)
    dominant = av.dominant_activities
    assert dominant == ["fixing", "configuring", "testing"]
    assert "exploring" not in dominant  # Below 0.3 threshold

# Tool classification tests
async def test_tool_classifier_heuristic():
    classifier = ToolClassifier(llm_client=None)
    result = classifier._try_heuristic("mcp__serena__find_symbol")
    assert result.intent == ToolIntent.SEARCH
    assert result.domain == ToolDomain.CODE
    assert result.confidence >= 0.5

async def test_tool_classifier_caching():
    classifier = ToolClassifier(mock_llm)

    # First call: LLM inference
    await classifier.classify_batch([{"name": "unknown_tool", "params": {}}])
    assert mock_llm.call_count == 1

    # Second call: cached
    await classifier.classify_batch([{"name": "unknown_tool", "params": {}}])
    assert mock_llm.call_count == 1  # No new calls

# Extraction priority tests
def test_extraction_priority_debugging():
    av = ActivityVector(fixing=0.9, exploring=0.4)

    # errors_resolved should be high priority for fixing
    priority = compute_extraction_priority("errors_resolved", av)
    assert priority > 0.7

    # discoveries should be lower priority
    disc_priority = compute_extraction_priority("discoveries", av)
    assert disc_priority < priority

def test_get_extraction_fields():
    av = ActivityVector(fixing=0.9, configuring=0.7)
    fields = get_extraction_fields(av, threshold=0.3)

    assert "errors_resolved" in fields
    assert "config_changes" in fields
    assert "completed_tasks" in fields
```

### 9.2 Integration Tests

```python
async def test_unified_classifier_session():
    classifier = UnifiedToolClassifier(llm_client)

    messages = [
        {"role": "tool", "name": "Read", "params": {"file_path": "/test.py"}},
        {"role": "tool", "name": "Bash", "params": {"command": "pytest tests/"}},
        {"role": "tool", "name": "mcp__unknown__custom_tool", "params": {}},
    ]

    activity, classifications = await classifier.classify_session(messages)

    assert len(classifications) == 3
    assert activity.testing > 0  # pytest detected
    assert activity.exploring > 0  # Read detected

async def test_enhanced_summary_generation():
    summarizer = EnhancedSessionSummarizer(llm_client)

    session = create_test_session(
        messages=[
            {"role": "user", "content": "Fix the authentication bug"},
            {"role": "assistant", "content": "I found the issue..."},
            {"role": "tool", "name": "Edit", "params": {"file": "auth.py"}},
        ]
    )

    summary = await summarizer.summarize(session)

    assert summary.activity_vector.fixing > 0.5
    assert summary.errors_resolved is not None or summary.completed_tasks is not None
```

---

## 10. Migration Guide

### 10.1 From Current System

Current `SessionSummarySchema` fields map to `EnhancedSessionSummary`:

| Current Field | New Field | Notes |
|---------------|-----------|-------|
| `objective` | `objective` | Unchanged |
| `completed_tasks` | `completed_tasks` | Unchanged |
| `blocked_items` | (removed) | Captured in `next_steps` or `errors_resolved` |
| `next_steps` | `next_steps` | Unchanged |
| `files_modified` | `files_modified` | Unchanged |
| `documentation_referenced` | (removed) | Low value, rarely used |
| `key_decisions` | `key_decisions` | **Enhanced**: Now structured with rationale |
| `mcp_tools_used` | `mcp_tools_used` | Unchanged |
| `token_count` | (metadata) | Moved to metadata |
| `duration_estimate` | `duration_minutes` | Renamed, now numeric |
| (new) | `activity_vector` | **New**: Multi-dimensional classification |
| (new) | `errors_resolved` | **New**: Structured error fixes |
| (new) | `config_changes` | **New**: Config change tracking |
| (new) | `test_results` | **New**: Test execution summary |
| (new) | `discoveries` | **New**: Exploration insights |

### 10.2 Configuration Migration

**Old config**:
```json
{
  "session_tracking": {
    "auto_summarize": true
  }
}
```

**New config** (backward compatible):
```json
{
  "session_tracking": {
    "auto_summarize": true,
    "summarization": {
      "type_detection": "auto",
      "extraction_threshold": 0.3,
      "include_decisions": true,
      "include_errors_resolved": true
    }
  }
}
```

Existing configs work without changes. New `summarization` block is optional with sensible defaults.

---

## Appendix A: Example Outputs

### A.1 Config Bug Debugging Session

**Input**: Session where user changed config → caused bug → agent debugged → fixed config

**Activity Vector**:
```
building=0.1, fixing=0.8, configuring=0.7, exploring=0.4, testing=0.5
```

**Output Summary**:
```markdown
# Session Summary

**Activity Profile**: fixing (0.8), configuring (0.7), testing (0.5), exploring (0.4)
**Outcome**: completed

## Objective
Resolve JWT authentication timeout causing 401 errors after config migration

## Errors Resolved

### 401 Unauthorized after ~1 minute
- **Root cause**: `JWT_EXPIRY=60` interpreted as 60 seconds (was meant to be minutes)
- **Fix**: Changed to `JWT_EXPIRY=3600` (explicit seconds)
- **Verification**: Tested token validity over 30 minutes

## Configuration Changes

| File | Setting | Change | Reason |
|------|---------|--------|--------|
| `.env` | `JWT_EXPIRY` | `60` → `3600` | Fix timeout - was ambiguous units |
| `config.py` | `EXPIRY_UNIT` | (none) → `seconds` | Prevent future ambiguity |

## Key Decisions

- **Explicit time units**: Added `EXPIRY_UNIT` setting to prevent unit ambiguity
  - Alternatives considered: Document-only fix, use ISO 8601 duration format

## Test Results

- **Framework**: pytest
- **Results**: 12/12 passed
- **Coverage**: 87.3%

## Files Modified

- `.env`
- `config.py`
- `tests/test_auth.py`

## Next Steps

- Add config schema validation to CI pipeline
- Document time format conventions in CONFIGURATION.md
```

### A.2 Exploration Session

**Input**: Session investigating codebase architecture

**Activity Vector**:
```
building=0.0, fixing=0.1, exploring=0.9, reviewing=0.7, documenting=0.3
```

**Output Summary**:
```markdown
# Session Summary

**Activity Profile**: exploring (0.9), reviewing (0.7), documenting (0.3)
**Outcome**: completed

## Objective
Understand the authentication system architecture

## Discoveries

- JWT tokens are signed with RS256 (asymmetric)
- Token refresh handled by `/api/auth/refresh` endpoint
- Auth middleware in `src/middleware/auth.py` validates all protected routes
- Role-based access control uses decorator pattern

## Key Decisions

- **Architecture documentation**: Will create ARCHITECTURE.md for auth system
  - Rationale: No existing docs, team members asking same questions

## Files Modified

- (none - exploration only)

## Next Steps

- Create ARCHITECTURE.md with auth system documentation
- Diagram the token flow for team reference
```

---

## Appendix B: Cost Analysis

### B.1 Tool Classification Costs

| Scenario | LLM Calls | Notes |
|----------|-----------|-------|
| Known tool (Read, Write, Edit, Grep) | 0 | Heuristic match |
| Known bash (git, npm, pytest, docker) | 0 | Heuristic match |
| New MCP server (first encounter) | 1 per unique tool | Cached after |
| Unknown CLI (first encounter) | 1 per unique command | Cached after |
| Subsequent sessions | ~0 | Everything cached |

### B.2 Token Efficiency

| Feature | Token Savings |
|---------|--------------|
| Activity-based field filtering | ~40% (skip irrelevant fields) |
| Heuristic tool classification | 100% (no LLM needed) |
| Classification caching | 100% after first use |
| Dynamic prompt length | ~20% (shorter prompts for simple sessions) |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0-draft | 2025-12-11 | Human + Claude | Initial specification |

---

## Decision Log

### Conversation Summary

**Initial Problem**: Default summarization templates lacked specificity ("1 paragraph" vs "1 paragraph or less")

**User Question**: How does the agent know how to save data to Graphiti? We want to capture:
- Feature specifications (why/how)
- Implementation status
- Test results and parameters
- Important context without "useless details"

**First Design Iteration**: Discrete `SessionType` enum with type-specific extraction

**User Critique**: What if topics are interwoven? (bug caused by config change)

**Solution**: Replace discrete classification with multi-dimensional `ActivityVector`

**Second User Critique**: Hard-coded tool mappings can't handle:
- Unknown MCP servers
- Arbitrary bash commands (installed CLI tools, scripts)

**Final Solution**: LLM-inferred tool classification with multi-level caching

**Key Design Principles Established**:
1. **No false dichotomies**: Continuous dimensions, not discrete categories
2. **No hard-coding**: LLM inference for unknown tools
3. **Self-improving**: Cache learns from usage
4. **Cost-efficient**: Heuristics first, LLM only when needed
5. **Temporal awareness**: Can compute vectors per-segment if needed
