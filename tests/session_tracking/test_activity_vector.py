"""Tests for ActivityVector model.

Tests Story 2 acceptance criteria:
- ActivityVector Pydantic model with 8 dimensions (building, fixing, configuring,
  exploring, refactoring, reviewing, testing, documenting)
- from_signals() class method normalizes raw signals to 0-1 range
- dominant_activities property returns activities above 0.3 threshold
- activity_profile property returns human-readable string
- Unit tests for normalization, dominant activities, edge cases
"""

import json

import pytest
from pydantic import ValidationError

from graphiti_core.session_tracking.activity_vector import ActivityVector


class TestActivityVectorBasics:
    """Test basic ActivityVector creation and properties."""

    def test_default_creation(self):
        """Test creating ActivityVector with all defaults (zeros)."""
        av = ActivityVector()
        assert av.building == 0.0
        assert av.fixing == 0.0
        assert av.configuring == 0.0
        assert av.exploring == 0.0
        assert av.refactoring == 0.0
        assert av.reviewing == 0.0
        assert av.testing == 0.0
        assert av.documenting == 0.0

    def test_explicit_creation(self):
        """Test creating ActivityVector with explicit values."""
        av = ActivityVector(
            fixing=0.8,
            configuring=0.7,
            testing=0.5,
        )
        assert av.fixing == 0.8
        assert av.configuring == 0.7
        assert av.testing == 0.5
        assert av.building == 0.0  # Default

    def test_all_dimensions_exist(self):
        """Test that all 8 dimensions are defined."""
        expected = [
            'building',
            'fixing',
            'configuring',
            'exploring',
            'refactoring',
            'reviewing',
            'testing',
            'documenting',
        ]
        assert expected == ActivityVector.DIMENSIONS
        assert len(ActivityVector.DIMENSIONS) == 8

    def test_value_bounds_validation(self):
        """Test that values must be between 0.0 and 1.0."""
        # Value > 1.0 should fail
        with pytest.raises(ValidationError):
            ActivityVector(fixing=1.5)

        # Value < 0.0 should fail
        with pytest.raises(ValidationError):
            ActivityVector(fixing=-0.1)

    def test_boundary_values(self):
        """Test exact boundary values 0.0 and 1.0 are accepted."""
        av = ActivityVector(fixing=0.0, building=1.0)
        assert av.fixing == 0.0
        assert av.building == 1.0


class TestFromSignals:
    """Test from_signals() class method for normalization."""

    def test_basic_normalization(self):
        """Test that signals are normalized by dividing by max."""
        signals = {'fixing': 0.8, 'configuring': 0.4, 'testing': 0.2}
        av = ActivityVector.from_signals(signals)

        # Max is 0.8, so fixing becomes 1.0
        assert av.fixing == 1.0
        assert av.configuring == 0.5  # 0.4/0.8
        assert av.testing == 0.25  # 0.2/0.8

    def test_already_normalized_signals(self):
        """Test signals that are already in 0-1 range."""
        signals = {'fixing': 1.0, 'configuring': 0.5}
        av = ActivityVector.from_signals(signals)

        assert av.fixing == 1.0
        assert av.configuring == 0.5

    def test_large_values_normalized(self):
        """Test that large values are normalized correctly."""
        signals = {'fixing': 100, 'configuring': 50, 'testing': 25}
        av = ActivityVector.from_signals(signals)

        assert av.fixing == 1.0
        assert av.configuring == 0.5
        assert av.testing == 0.25

    def test_empty_signals(self):
        """Test from_signals with empty dict returns all zeros."""
        av = ActivityVector.from_signals({})
        assert av.fixing == 0.0
        assert av.building == 0.0

    def test_unknown_keys_ignored(self):
        """Test that unknown dimension keys are silently ignored."""
        signals = {'fixing': 0.8, 'unknown_activity': 0.5, 'foo': 0.3}
        av = ActivityVector.from_signals(signals)

        assert av.fixing == 1.0  # Normalized
        assert not hasattr(av, 'unknown_activity')
        assert not hasattr(av, 'foo')

    def test_negative_values_clamped_to_zero(self):
        """Test that negative values are treated as zero."""
        signals = {'fixing': 0.8, 'configuring': -0.5}
        av = ActivityVector.from_signals(signals)

        assert av.fixing == 1.0
        assert av.configuring == 0.0

    def test_all_zero_signals(self):
        """Test from_signals with all zero values."""
        signals = {'fixing': 0, 'configuring': 0, 'testing': 0}
        av = ActivityVector.from_signals(signals)

        assert av.fixing == 0.0
        assert av.configuring == 0.0
        assert av.testing == 0.0

    def test_single_signal(self):
        """Test from_signals with single activity."""
        signals = {'exploring': 0.5}
        av = ActivityVector.from_signals(signals)

        assert av.exploring == 1.0  # Becomes max

    def test_example_from_story(self):
        """Test exact example from Story 2 spec."""
        signals = {'fixing': 0.8, 'configuring': 0.7, 'testing': 0.5}
        av = ActivityVector.from_signals(signals)

        assert av.fixing == 1.0  # Normalized to max
        assert av.configuring == pytest.approx(0.875, abs=0.001)  # 0.7/0.8
        assert av.testing == pytest.approx(0.625, abs=0.001)  # 0.5/0.8


class TestDominantActivities:
    """Test dominant_activities property and get_dominant_activities method."""

    def test_dominant_activities_default_threshold(self):
        """Test dominant_activities returns activities >= 0.3."""
        av = ActivityVector(
            fixing=0.8,
            configuring=0.5,
            testing=0.3,  # Exactly at threshold
            exploring=0.2,  # Below threshold
        )
        dominant = av.dominant_activities

        assert 'fixing' in dominant
        assert 'configuring' in dominant
        assert 'testing' in dominant
        assert 'exploring' not in dominant

    def test_dominant_activities_sorted_by_intensity(self):
        """Test dominant_activities are sorted by intensity (highest first)."""
        av = ActivityVector(
            fixing=0.5,
            configuring=0.8,
            testing=0.6,
        )
        dominant = av.dominant_activities

        assert dominant == ['configuring', 'testing', 'fixing']

    def test_dominant_activities_none_above_threshold(self):
        """Test dominant_activities with all values below threshold."""
        av = ActivityVector(
            fixing=0.2,
            configuring=0.1,
            testing=0.15,
        )
        dominant = av.dominant_activities

        assert dominant == []

    def test_custom_threshold(self):
        """Test get_dominant_activities with custom threshold."""
        av = ActivityVector(
            fixing=0.8,
            configuring=0.5,
            testing=0.3,
        )

        # Higher threshold
        dominant_high = av.get_dominant_activities(threshold=0.6)
        assert dominant_high == ['fixing']

        # Lower threshold
        dominant_low = av.get_dominant_activities(threshold=0.2)
        assert len(dominant_low) == 3


class TestPrimaryActivity:
    """Test primary_activity property."""

    def test_primary_activity_highest(self):
        """Test primary_activity returns highest intensity activity."""
        av = ActivityVector(
            fixing=0.8,
            configuring=0.5,
            testing=0.3,
        )
        assert av.primary_activity == 'fixing'

    def test_primary_activity_mixed(self):
        """Test primary_activity returns 'mixed' when none above threshold."""
        av = ActivityVector(
            fixing=0.2,
            configuring=0.1,
        )
        assert av.primary_activity == 'mixed'

    def test_primary_activity_all_zeros(self):
        """Test primary_activity with all zeros returns 'mixed'."""
        av = ActivityVector()
        assert av.primary_activity == 'mixed'


class TestActivityProfile:
    """Test activity_profile property for human-readable output."""

    def test_activity_profile_format(self):
        """Test activity_profile returns correct format."""
        av = ActivityVector(
            fixing=0.8,
            configuring=0.7,
            testing=0.5,
        )
        profile = av.activity_profile

        assert 'fixing (0.80)' in profile
        assert 'configuring (0.70)' in profile
        assert 'testing (0.50)' in profile
        assert ', ' in profile  # Comma-separated

    def test_activity_profile_order(self):
        """Test activity_profile lists activities in descending order."""
        av = ActivityVector(
            fixing=0.5,
            configuring=0.8,
            testing=0.6,
        )
        profile = av.activity_profile

        # Should be ordered: configuring (0.80), testing (0.60), fixing (0.50)
        assert profile.index('configuring') < profile.index('testing')
        assert profile.index('testing') < profile.index('fixing')

    def test_activity_profile_mixed(self):
        """Test activity_profile when no dominant activities."""
        av = ActivityVector(
            fixing=0.2,
            configuring=0.1,
        )
        profile = av.activity_profile

        assert profile == 'mixed (no dominant activity)'

    def test_activity_profile_single_dominant(self):
        """Test activity_profile with single dominant activity."""
        av = ActivityVector(fixing=0.8)
        profile = av.activity_profile

        assert profile == 'fixing (0.80)'


class TestSerialization:
    """Test serialization and deserialization."""

    def test_to_dict(self):
        """Test to_dict() returns all dimensions."""
        av = ActivityVector(fixing=0.8, configuring=0.5)
        d = av.to_dict()

        assert d['fixing'] == 0.8
        assert d['configuring'] == 0.5
        assert d['building'] == 0.0
        assert len(d) == 8

    def test_model_dump(self):
        """Test Pydantic model_dump() serialization."""
        av = ActivityVector(fixing=0.8, testing=0.5)
        data = av.model_dump()

        assert data['fixing'] == 0.8
        assert data['testing'] == 0.5
        assert data['building'] == 0.0

    def test_model_dump_json(self):
        """Test JSON serialization."""
        av = ActivityVector(fixing=0.8, testing=0.5)
        json_str = av.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed['fixing'] == 0.8
        assert parsed['testing'] == 0.5

    def test_round_trip_serialization(self):
        """Test that serialization round-trips correctly."""
        original = ActivityVector(
            building=0.1,
            fixing=0.8,
            configuring=0.7,
            exploring=0.3,
            refactoring=0.4,
            reviewing=0.2,
            testing=0.5,
            documenting=0.6,
        )
        data = original.model_dump()
        restored = ActivityVector(**data)

        assert restored == original


class TestRepr:
    """Test string representation."""

    def test_repr_empty(self):
        """Test repr for all-zeros vector."""
        av = ActivityVector()
        assert repr(av) == 'ActivityVector()'

    def test_repr_with_values(self):
        """Test repr shows non-zero dimensions."""
        av = ActivityVector(fixing=0.8, configuring=0.5)
        r = repr(av)

        assert 'ActivityVector(' in r
        assert 'fixing=0.80' in r
        assert 'configuring=0.50' in r
        assert 'building' not in r  # Zero, should not appear


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_very_small_values(self):
        """Test handling of very small float values."""
        av = ActivityVector(fixing=0.001, configuring=0.0001)
        assert av.fixing == 0.001
        assert av.configuring == 0.0001
        assert av.dominant_activities == []  # Below threshold

    def test_floating_point_precision(self):
        """Test that floating point precision is handled correctly."""
        signals = {'fixing': 1, 'configuring': 3}
        av = ActivityVector.from_signals(signals)

        # 1/3 = 0.333...
        assert av.fixing == pytest.approx(0.333, abs=0.01)
        assert av.configuring == 1.0

    def test_all_dimensions_at_max(self):
        """Test with all dimensions at 1.0."""
        av = ActivityVector(
            building=1.0,
            fixing=1.0,
            configuring=1.0,
            exploring=1.0,
            refactoring=1.0,
            reviewing=1.0,
            testing=1.0,
            documenting=1.0,
        )
        # All should be dominant
        assert len(av.dominant_activities) == 8
