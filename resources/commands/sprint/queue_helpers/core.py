"""
Core Queue Management Functions

This module provides core functions for loading, saving, and manipulating the sprint queue.

Functions:
    load_queue: Load queue from .queue.json file
    save_queue: Save queue to .queue.json file
    set_metadata: Set metadata field on a story with validation

Author: Sprint Remediation Test Reconciliation
Created: 2025-12-20
Story: 4 - Reconciliation Application Functions
"""

import json
from pathlib import Path
from typing import Any, Optional
from copy import deepcopy


def load_queue(sprint_dir: str = ".claude/sprint") -> dict[str, Any]:
    """
    Load queue from .queue.json file.

    Args:
        sprint_dir: Sprint directory path (default: .claude/sprint)

    Returns:
        Parsed queue dictionary

    Raises:
        FileNotFoundError: If .queue.json doesn't exist
        ValueError: If .queue.json is invalid JSON
    """
    queue_path = Path(sprint_dir) / ".queue.json"

    if not queue_path.exists():
        raise FileNotFoundError(f"Queue file not found: {queue_path}")

    try:
        with open(queue_path, 'r', encoding='utf-8') as f:
            queue = json.load(f)
        return queue
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in queue file: {e}")


def save_queue(queue: dict[str, Any], sprint_dir: str = ".claude/sprint") -> None:
    """
    Save queue to .queue.json file.

    Args:
        queue: Queue dictionary to save
        sprint_dir: Sprint directory path (default: .claude/sprint)

    Raises:
        ValueError: If queue is invalid
    """
    if not isinstance(queue, dict):
        raise ValueError("Queue must be a dictionary")

    if 'stories' not in queue:
        raise ValueError("Queue must contain 'stories' key")

    queue_path = Path(sprint_dir) / ".queue.json"

    # Ensure directory exists
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with pretty formatting for readability
    with open(queue_path, 'w', encoding='utf-8') as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def set_metadata(
    queue: dict[str, Any],
    story_id: str,
    key: str,
    value: Any
) -> dict[str, Any]:
    """
    Set metadata field on a story.

    Returns a new queue dictionary (immutable pattern for safety).

    Args:
        queue: Queue dictionary
        story_id: Story ID to update
        key: Metadata key to set
        value: Metadata value

    Returns:
        Updated queue dictionary (new copy)

    Raises:
        ValueError: If story doesn't exist or metadata is invalid
    """
    # Create deep copy for immutability
    new_queue = deepcopy(queue)

    # Validate story exists
    if story_id not in new_queue.get('stories', {}):
        raise ValueError(f"Story not found: {story_id}")

    story = new_queue['stories'][story_id]

    # Initialize metadata if it doesn't exist
    if 'metadata' not in story:
        story['metadata'] = {}

    # Set metadata value
    story['metadata'][key] = value

    return new_queue


def get_story(queue: dict[str, Any], story_id: str) -> dict[str, Any]:
    """
    Get story from queue by ID.

    Args:
        queue: Queue dictionary
        story_id: Story ID to retrieve

    Returns:
        Story dictionary

    Raises:
        ValueError: If story doesn't exist
    """
    if story_id not in queue.get('stories', {}):
        raise ValueError(f"Story not found: {story_id}")

    return queue['stories'][story_id]


def update_story_status(
    queue: dict[str, Any],
    story_id: str,
    status: str
) -> dict[str, Any]:
    """
    Update story status.

    Returns a new queue dictionary (immutable pattern for safety).

    Args:
        queue: Queue dictionary
        story_id: Story ID to update
        status: New status value

    Returns:
        Updated queue dictionary (new copy)

    Raises:
        ValueError: If story doesn't exist
    """
    # Create deep copy for immutability
    new_queue = deepcopy(queue)

    # Validate story exists
    if story_id not in new_queue.get('stories', {}):
        raise ValueError(f"Story not found: {story_id}")

    # Update status
    new_queue['stories'][story_id]['status'] = status

    return new_queue


# Module exports
__all__ = [
    'load_queue',
    'save_queue',
    'set_metadata',
    'get_story',
    'update_story_status'
]
