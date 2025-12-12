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

"""Extraction priority algorithm for activity-weighted field selection.

This module provides priority-weighted extraction that determines which fields
to include in session summaries based on activity vector intensity. Debugging
sessions prioritize error resolution while exploration sessions prioritize
discoveries.

Example:
    >>> from graphiti_core.session_tracking import ActivityVector
    >>> activity = ActivityVector(fixing=0.9, testing=0.5)
    >>> priority = compute_extraction_priority("errors_resolved", activity)
    >>> priority  # ~0.9 (high priority for debugging session)
    >>> fields = get_extraction_fields(activity, threshold=0.3)
    >>> fields  # ['errors_resolved', 'test_results', ...] (ordered by priority)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .activity_vector import ActivityVector


# Mapping of extraction fields to activity dimension weights
# Each field specifies which activity dimensions contribute to its priority
# and with what weight (0.0-1.0)
EXTRACTION_AFFINITIES: dict[str, dict[str, float]] = {
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
    "discoveries": {
        "exploring": 1.0,
        "reviewing": 0.8,
        "documenting": 0.5,
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
    "files_modified": {
        "building": 0.9,
        "fixing": 0.8,
        "refactoring": 0.9,
        "configuring": 0.6,
    },
    "next_steps": {
        "building": 0.8,
        "exploring": 0.7,
        "fixing": 0.6,
    },
    "blocked_items": {
        "fixing": 0.9,
        "configuring": 0.7,
        "building": 0.5,
    },
    "documentation_referenced": {
        "documenting": 1.0,
        "exploring": 0.7,
        "reviewing": 0.5,
    },
}


def compute_extraction_priority(field: str, activity: 'ActivityVector') -> float:
    """Compute the priority score for a field based on activity vector.

    The priority is calculated as a weighted sum of activity dimension values,
    where weights are defined in EXTRACTION_AFFINITIES. The result is normalized
    by the sum of weights to produce a 0.0-1.0 score.

    Args:
        field: The extraction field name (e.g., "errors_resolved", "discoveries")
        activity: The activity vector representing session activities

    Returns:
        Float priority score between 0.0 and 1.0. Returns 0.5 (neutral priority)
        for unknown fields or fields with empty affinities.

    Example:
        >>> activity = ActivityVector(fixing=0.9, configuring=0.7)
        >>> compute_extraction_priority("errors_resolved", activity)
        0.9  # High priority (fixing=1.0*0.9 + configuring=0.7*0.7 + testing=0.5*0)
    """
    affinities = EXTRACTION_AFFINITIES.get(field, {})

    if not affinities:
        return 0.5  # Neutral priority for unknown fields

    # Compute weighted sum: sum(activity_dimension * affinity_weight)
    weighted_sum = sum(
        getattr(activity, dim, 0.0) * weight for dim, weight in affinities.items()
    )

    # Normalize by sum of weights
    weight_sum = sum(affinities.values())
    if weight_sum == 0:
        return 0.5

    return weighted_sum / weight_sum


def get_extraction_fields(
    activity: 'ActivityVector', threshold: float = 0.3
) -> list[str]:
    """Get extraction fields ordered by priority for the given activity.

    Computes priority for all fields in EXTRACTION_AFFINITIES, filters those
    above the threshold, and returns them sorted by priority (highest first).

    Args:
        activity: The activity vector representing session activities
        threshold: Minimum priority score (0.0-1.0) for inclusion. Default 0.3
                   matches ActivityVector.DEFAULT_THRESHOLD.

    Returns:
        List of field names with priority >= threshold, sorted by priority
        (highest first).

    Example:
        >>> activity = ActivityVector(fixing=0.9, testing=0.5)
        >>> get_extraction_fields(activity, threshold=0.3)
        ['errors_resolved', 'test_results', 'completed_tasks', ...]
    """
    # Compute priorities for all fields
    field_priorities = [
        (field, compute_extraction_priority(field, activity))
        for field in EXTRACTION_AFFINITIES
    ]

    # Filter by threshold and sort by priority descending
    filtered = [(f, p) for f, p in field_priorities if p >= threshold]
    filtered.sort(key=lambda x: x[1], reverse=True)

    return [field for field, _ in filtered]


def get_extraction_priorities(
    activity: 'ActivityVector', threshold: float = 0.3
) -> list[tuple[str, float]]:
    """Get extraction fields with their priority scores.

    Similar to get_extraction_fields() but returns tuples with priority scores,
    useful for prompt building where priority values inform ordering and emphasis.

    Args:
        activity: The activity vector representing session activities
        threshold: Minimum priority score (0.0-1.0) for inclusion. Default 0.3.

    Returns:
        List of (field_name, priority) tuples with priority >= threshold,
        sorted by priority (highest first).

    Example:
        >>> activity = ActivityVector(fixing=0.9, testing=0.5)
        >>> get_extraction_priorities(activity, threshold=0.3)
        [('errors_resolved', 0.9), ('test_results', 0.73), ...]
    """
    # Compute priorities for all fields
    field_priorities = [
        (field, compute_extraction_priority(field, activity))
        for field in EXTRACTION_AFFINITIES
    ]

    # Filter by threshold and sort by priority descending
    filtered = [(f, p) for f, p in field_priorities if p >= threshold]
    filtered.sort(key=lambda x: x[1], reverse=True)

    return filtered
