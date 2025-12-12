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

from typing import ClassVar

from pydantic import BaseModel, Field


class ActivityVector(BaseModel):
    """8-dimensional activity vector representing session activities.

    Each dimension is a continuous 0.0-1.0 value representing the intensity
    of that activity type in a session. Activities are NOT mutually exclusive -
    a session can score high on multiple dimensions simultaneously.

    Example:
        A debugging session might score:
        - fixing: 0.8 (primary activity)
        - configuring: 0.7 (config-related bug)
        - testing: 0.5 (verification)
    """

    # The 8 activity dimensions
    building: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description='Creating new features or functionality',
    )
    fixing: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description='Debugging and resolving errors',
    )
    configuring: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description='Setting up or modifying configuration',
    )
    exploring: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description='Investigating codebase or learning',
    )
    refactoring: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description='Restructuring code without changing behavior',
    )
    reviewing: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description='Code review or analysis',
    )
    testing: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description='Writing or running tests',
    )
    documenting: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description='Writing documentation or comments',
    )

    # Class-level constants
    DIMENSIONS: ClassVar[list[str]] = [
        'building',
        'fixing',
        'configuring',
        'exploring',
        'refactoring',
        'reviewing',
        'testing',
        'documenting',
    ]
    DEFAULT_THRESHOLD: ClassVar[float] = 0.3

    @classmethod
    def from_signals(cls, signals: dict[str, float]) -> 'ActivityVector':
        """Create an ActivityVector from raw signal values.

        Normalizes signals by dividing by the maximum value, so the highest
        signal becomes 1.0 and others are scaled proportionally.

        Args:
            signals: Dictionary mapping activity names to raw signal values.
                     Unknown keys are ignored. Values can be any non-negative float.

        Returns:
            ActivityVector with normalized 0.0-1.0 values.

        Example:
            >>> signals = {"fixing": 0.8, "configuring": 0.7, "testing": 0.5}
            >>> av = ActivityVector.from_signals(signals)
            >>> av.fixing  # 1.0 (normalized to max)
            >>> av.configuring  # 0.875 (0.7/0.8)
        """
        # Filter to known dimensions and non-negative values
        valid_signals = {
            k: max(0.0, v) for k, v in signals.items() if k in cls.DIMENSIONS
        }

        if not valid_signals:
            return cls()

        # Find max value for normalization
        max_value = max(valid_signals.values())

        if max_value == 0:
            return cls()

        # Normalize all values by dividing by max
        normalized = {k: v / max_value for k, v in valid_signals.items()}

        return cls(**normalized)

    @property
    def dominant_activities(self) -> list[str]:
        """Return activities above the default threshold (0.3).

        Returns:
            List of activity names with intensity >= 0.3, sorted by
            intensity (highest first).
        """
        return self.get_dominant_activities(threshold=self.DEFAULT_THRESHOLD)

    def get_dominant_activities(self, threshold: float = 0.3) -> list[str]:
        """Return activities above the specified threshold.

        Args:
            threshold: Minimum intensity value (0.0-1.0) to consider dominant.

        Returns:
            List of activity names with intensity >= threshold, sorted by
            intensity (highest first).
        """
        activities = [
            (name, getattr(self, name))
            for name in self.DIMENSIONS
            if getattr(self, name) >= threshold
        ]
        # Sort by intensity descending
        activities.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in activities]

    @property
    def primary_activity(self) -> str:
        """Return the highest intensity activity, or 'mixed' if none above threshold.

        Returns:
            Name of the activity with highest intensity if any are above
            the default threshold, otherwise 'mixed'.
        """
        dominant = self.dominant_activities
        if dominant:
            return dominant[0]
        return 'mixed'

    @property
    def activity_profile(self) -> str:
        """Return human-readable string of dominant activities with scores.

        Returns:
            Formatted string like "fixing (0.80), configuring (0.70)"
            or "mixed (no dominant activity)" if none above threshold.

        Example:
            >>> av = ActivityVector(fixing=0.8, configuring=0.7, testing=0.5)
            >>> av.activity_profile
            'fixing (0.80), configuring (0.70), testing (0.50)'
        """
        dominant = self.dominant_activities
        if not dominant:
            return 'mixed (no dominant activity)'

        parts = []
        for name in dominant:
            value = getattr(self, name)
            parts.append(f'{name} ({value:.2f})')

        return ', '.join(parts)

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary with all dimension values.

        Returns:
            Dictionary mapping dimension names to their float values.
        """
        return {name: getattr(self, name) for name in self.DIMENSIONS}

    def __repr__(self) -> str:
        """Return concise representation showing only non-zero dimensions."""
        non_zero = {name: getattr(self, name) for name in self.DIMENSIONS if getattr(self, name) > 0}
        if not non_zero:
            return 'ActivityVector()'
        parts = ', '.join(f'{k}={v:.2f}' for k, v in non_zero.items())
        return f'ActivityVector({parts})'
