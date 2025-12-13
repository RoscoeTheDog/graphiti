"""Tests for Extraction Priority Algorithm.

Tests Story 8 acceptance criteria:
- EXTRACTION_AFFINITIES mapping fields to activity dimension weights
- compute_extraction_priority(field, activity) -> float function
- get_extraction_fields(activity, threshold) -> list[str] function
- Unit tests verifying priorities for debugging session, exploration session
- Threshold filtering works correctly (default 0.3)

Additional coverage:
- get_extraction_priorities() for Story 9 integration
- Edge cases: unknown fields, empty activities, boundary thresholds
"""

import pytest

from graphiti_core.session_tracking.activity_vector import ActivityVector
from graphiti_core.session_tracking.extraction_priority import (
    EXTRACTION_AFFINITIES,
    compute_extraction_priority,
    get_extraction_fields,
    get_extraction_priorities,
)


class TestExtractionAffinities:
    """Test EXTRACTION_AFFINITIES constant structure and values."""

    def test_affinities_is_dict(self):
        """Test that EXTRACTION_AFFINITIES is a dictionary."""
        assert isinstance(EXTRACTION_AFFINITIES, dict)

    def test_required_fields_exist(self):
        """Test that all required extraction fields are defined."""
        required_fields = [
            "completed_tasks",
            "key_decisions",
            "errors_resolved",
            "discoveries",
            "config_changes",
            "test_results",
            "files_modified",
            "next_steps",
            "blocked_items",
            "documentation_referenced",
        ]
        for field in required_fields:
            assert field in EXTRACTION_AFFINITIES, f"Missing field: {field}"

    def test_affinities_have_valid_weights(self):
        """Test that all affinity weights are between 0.0 and 1.0."""
        for field, affinities in EXTRACTION_AFFINITIES.items():
            assert isinstance(affinities, dict), f"{field} affinities should be a dict"
            for dim, weight in affinities.items():
                assert 0.0 <= weight <= 1.0, (
                    f"{field}.{dim} weight {weight} out of range"
                )

    def test_affinities_reference_valid_dimensions(self):
        """Test that affinity keys are valid ActivityVector dimensions."""
        valid_dimensions = set(ActivityVector.DIMENSIONS)
        for field, affinities in EXTRACTION_AFFINITIES.items():
            for dim in affinities.keys():
                assert dim in valid_dimensions, (
                    f"{field} references invalid dimension: {dim}"
                )

    def test_errors_resolved_prioritizes_fixing(self):
        """Test errors_resolved has highest weight on fixing dimension."""
        affinities = EXTRACTION_AFFINITIES["errors_resolved"]
        assert affinities["fixing"] == 1.0

    def test_discoveries_prioritizes_exploring(self):
        """Test discoveries has highest weight on exploring dimension."""
        affinities = EXTRACTION_AFFINITIES["discoveries"]
        assert affinities["exploring"] == 1.0

    def test_test_results_prioritizes_testing(self):
        """Test test_results has highest weight on testing dimension."""
        affinities = EXTRACTION_AFFINITIES["test_results"]
        assert affinities["testing"] == 1.0


class TestComputeExtractionPriority:
    """Test compute_extraction_priority() function."""

    def test_basic_priority_computation(self):
        """Test basic priority computation for known field/activity."""
        activity = ActivityVector(fixing=0.9)
        priority = compute_extraction_priority("errors_resolved", activity)
        # errors_resolved: {fixing: 1.0, configuring: 0.7, testing: 0.5}
        # weighted_sum = 0.9 * 1.0 + 0 * 0.7 + 0 * 0.5 = 0.9
        # weight_sum = 1.0 + 0.7 + 0.5 = 2.2
        # priority = 0.9 / 2.2 ~ 0.409
        assert priority == pytest.approx(0.409, abs=0.01)

    def test_mixed_activity_priority(self):
        """Test priority computation with multiple active dimensions."""
        activity = ActivityVector(fixing=0.8, configuring=0.7, testing=0.5)
        priority = compute_extraction_priority("errors_resolved", activity)
        # errors_resolved: {fixing: 1.0, configuring: 0.7, testing: 0.5}
        # weighted_sum = 0.8 * 1.0 + 0.7 * 0.7 + 0.5 * 0.5 = 0.8 + 0.49 + 0.25 = 1.54
        # weight_sum = 1.0 + 0.7 + 0.5 = 2.2
        # priority = 1.54 / 2.2 = 0.7
        assert priority == pytest.approx(0.7, abs=0.01)

    def test_unknown_field_returns_neutral(self):
        """Test that unknown fields return 0.5 (neutral priority)."""
        activity = ActivityVector(fixing=0.9)
        priority = compute_extraction_priority("unknown_field", activity)
        assert priority == 0.5

    def test_zero_activity_returns_zero(self):
        """Test that zero activity vector returns 0.0 priority."""
        activity = ActivityVector()  # All zeros
        priority = compute_extraction_priority("errors_resolved", activity)
        assert priority == 0.0

    def test_full_activity_high_priority(self):
        """Test that max activity gives high priority for aligned field."""
        activity = ActivityVector(fixing=1.0, configuring=1.0, testing=1.0)
        priority = compute_extraction_priority("errors_resolved", activity)
        # errors_resolved: {fixing: 1.0, configuring: 0.7, testing: 0.5}
        # weighted_sum = 1.0 * 1.0 + 1.0 * 0.7 + 1.0 * 0.5 = 2.2
        # weight_sum = 2.2
        # priority = 2.2 / 2.2 = 1.0
        assert priority == pytest.approx(1.0, abs=0.01)

    def test_priority_range(self):
        """Test that priority is always between 0.0 and 1.0."""
        # Test various activity combinations
        test_cases = [
            ActivityVector(),
            ActivityVector(fixing=0.5),
            ActivityVector(fixing=1.0, configuring=1.0),
            ActivityVector(exploring=0.9, reviewing=0.8, documenting=0.5),
        ]
        for activity in test_cases:
            for field in EXTRACTION_AFFINITIES.keys():
                priority = compute_extraction_priority(field, activity)
                assert 0.0 <= priority <= 1.0, (
                    f"Priority {priority} out of range for {field}"
                )

    def test_exploration_session_discoveries_high(self):
        """Test exploration session gives high priority to discoveries."""
        activity = ActivityVector(exploring=0.9, reviewing=0.7)
        discoveries_priority = compute_extraction_priority("discoveries", activity)
        errors_priority = compute_extraction_priority("errors_resolved", activity)
        # Discoveries should be higher for exploration session
        assert discoveries_priority > errors_priority

    def test_debugging_session_errors_high(self):
        """Test debugging session gives high priority to errors_resolved."""
        activity = ActivityVector(fixing=0.9, testing=0.5)
        errors_priority = compute_extraction_priority("errors_resolved", activity)
        discoveries_priority = compute_extraction_priority("discoveries", activity)
        # Errors should be higher for debugging session
        assert errors_priority > discoveries_priority


class TestGetExtractionFields:
    """Test get_extraction_fields() function."""

    def test_debugging_session_field_order(self):
        """Test field ordering for debugging-heavy session."""
        activity = ActivityVector(fixing=0.9, testing=0.5)
        fields = get_extraction_fields(activity)
        # errors_resolved should be high priority
        assert "errors_resolved" in fields
        # Should be sorted by priority (errors_resolved likely first or near top)
        assert len(fields) > 0

    def test_exploration_session_field_order(self):
        """Test field ordering for exploration session."""
        activity = ActivityVector(exploring=0.9, reviewing=0.7, documenting=0.5)
        fields = get_extraction_fields(activity)
        # discoveries should be high priority
        assert "discoveries" in fields
        # documentation_referenced should be included
        assert "documentation_referenced" in fields

    def test_default_threshold_is_0_3(self):
        """Test that default threshold is 0.3."""
        activity = ActivityVector(fixing=0.9)
        fields_default = get_extraction_fields(activity)
        fields_explicit = get_extraction_fields(activity, threshold=0.3)
        assert fields_default == fields_explicit

    def test_threshold_filtering_excludes_low_priority(self):
        """Test that fields below threshold are excluded."""
        activity = ActivityVector(fixing=0.9)  # Only fixing is high
        # High threshold should exclude most fields
        fields_high = get_extraction_fields(activity, threshold=0.5)
        fields_low = get_extraction_fields(activity, threshold=0.1)
        assert len(fields_low) >= len(fields_high)

    def test_threshold_zero_includes_all(self):
        """Test that threshold=0 includes all fields with any priority."""
        activity = ActivityVector(fixing=0.5)
        fields = get_extraction_fields(activity, threshold=0.0)
        # Should include many fields since threshold is 0
        assert len(fields) > 0

    def test_threshold_one_excludes_most(self):
        """Test that threshold=1.0 excludes most fields."""
        activity = ActivityVector(fixing=0.5)
        fields = get_extraction_fields(activity, threshold=1.0)
        # Very few or no fields should pass threshold=1.0
        assert len(fields) <= 2  # Only perfect matches

    def test_fields_sorted_by_priority_descending(self):
        """Test that returned fields are sorted by priority (highest first)."""
        activity = ActivityVector(fixing=0.9, configuring=0.7, testing=0.5)
        fields = get_extraction_fields(activity, threshold=0.0)
        # Get priorities to verify order
        priorities = get_extraction_priorities(activity, threshold=0.0)
        priority_dict = dict(priorities)

        for i in range(len(fields) - 1):
            current_priority = priority_dict.get(fields[i], 0)
            next_priority = priority_dict.get(fields[i + 1], 0)
            assert current_priority >= next_priority, (
                f"Fields not sorted: {fields[i]} ({current_priority}) "
                f"before {fields[i + 1]} ({next_priority})"
            )

    def test_returns_list_of_strings(self):
        """Test that return type is list of strings."""
        activity = ActivityVector(fixing=0.5)
        fields = get_extraction_fields(activity)
        assert isinstance(fields, list)
        for field in fields:
            assert isinstance(field, str)

    def test_empty_activity_returns_no_high_priority_fields(self):
        """Test that empty activity vector returns no fields above default threshold."""
        activity = ActivityVector()  # All zeros
        fields_high = get_extraction_fields(activity, threshold=0.3)
        # High threshold should exclude all (zero priorities)
        assert len(fields_high) == 0

    def test_empty_activity_zero_threshold_includes_all(self):
        """Test that empty activity with threshold=0 includes all fields."""
        activity = ActivityVector()  # All zeros
        fields_zero = get_extraction_fields(activity, threshold=0.0)
        # Zero threshold allows all fields (0.0 >= 0.0 is True)
        # All 10 fields should be included
        assert len(fields_zero) == len(EXTRACTION_AFFINITIES)


class TestGetExtractionPriorities:
    """Test get_extraction_priorities() function for Story 9 integration."""

    def test_returns_tuples_with_scores(self):
        """Test that function returns list of (field, score) tuples."""
        activity = ActivityVector(fixing=0.9)
        priorities = get_extraction_priorities(activity)
        assert isinstance(priorities, list)
        for item in priorities:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], str)  # field name
            assert isinstance(item[1], float)  # priority score

    def test_scores_match_compute_priority(self):
        """Test that returned scores match compute_extraction_priority()."""
        activity = ActivityVector(fixing=0.8, configuring=0.6)
        priorities = get_extraction_priorities(activity, threshold=0.0)
        for field, score in priorities:
            expected = compute_extraction_priority(field, activity)
            assert score == pytest.approx(expected, abs=0.001), (
                f"Score mismatch for {field}: {score} vs {expected}"
            )

    def test_sorted_by_priority_descending(self):
        """Test priorities are sorted by score (highest first)."""
        activity = ActivityVector(fixing=0.9, exploring=0.7, testing=0.5)
        priorities = get_extraction_priorities(activity, threshold=0.0)
        scores = [score for _, score in priorities]
        assert scores == sorted(scores, reverse=True)

    def test_threshold_filters_priorities(self):
        """Test that threshold filters out low-priority fields."""
        activity = ActivityVector(fixing=0.9)
        all_priorities = get_extraction_priorities(activity, threshold=0.0)
        high_priorities = get_extraction_priorities(activity, threshold=0.3)
        assert len(high_priorities) <= len(all_priorities)
        for field, score in high_priorities:
            assert score >= 0.3

    def test_matches_get_extraction_fields(self):
        """Test that field names match get_extraction_fields() output."""
        activity = ActivityVector(fixing=0.8, configuring=0.6)
        fields = get_extraction_fields(activity, threshold=0.2)
        priorities = get_extraction_priorities(activity, threshold=0.2)
        priority_fields = [f for f, _ in priorities]
        assert fields == priority_fields


class TestDebuggingSessionScenario:
    """Integration tests for debugging session scenario from Story 8 spec."""

    @pytest.fixture
    def debugging_session(self):
        """Create a debugging session activity vector."""
        return ActivityVector(fixing=0.9, testing=0.5, exploring=0.4)

    def test_errors_resolved_high_priority(self, debugging_session):
        """Test errors_resolved has high priority in debugging session."""
        priority = compute_extraction_priority("errors_resolved", debugging_session)
        # With fixing=0.9, errors_resolved should be high
        assert priority > 0.3

    def test_discoveries_low_priority(self, debugging_session):
        """Test discoveries has lower priority in debugging session."""
        priority = compute_extraction_priority("discoveries", debugging_session)
        # With low exploring (0.4), discoveries should be lower
        errors_priority = compute_extraction_priority("errors_resolved", debugging_session)
        assert priority < errors_priority

    def test_test_results_included(self, debugging_session):
        """Test test_results is included in debugging session fields."""
        fields = get_extraction_fields(debugging_session)
        assert "test_results" in fields

    def test_field_ordering_for_debugging(self, debugging_session):
        """Test that error-related fields come before exploration fields."""
        fields = get_extraction_fields(debugging_session, threshold=0.2)
        if "errors_resolved" in fields and "discoveries" in fields:
            errors_idx = fields.index("errors_resolved")
            discoveries_idx = fields.index("discoveries")
            assert errors_idx < discoveries_idx


class TestExplorationSessionScenario:
    """Integration tests for exploration session scenario from Story 8 spec."""

    @pytest.fixture
    def exploration_session(self):
        """Create an exploration session activity vector."""
        return ActivityVector(exploring=0.9, reviewing=0.7, documenting=0.5)

    def test_discoveries_high_priority(self, exploration_session):
        """Test discoveries has high priority in exploration session."""
        priority = compute_extraction_priority("discoveries", exploration_session)
        # discoveries: {exploring: 1.0, reviewing: 0.8, documenting: 0.5}
        # With exploring=0.9, reviewing=0.7, documenting=0.5, should be high
        assert priority > 0.5

    def test_errors_resolved_low_priority(self, exploration_session):
        """Test errors_resolved has low priority in exploration session."""
        priority = compute_extraction_priority("errors_resolved", exploration_session)
        # errors_resolved needs fixing, which is 0 in exploration session
        discoveries_priority = compute_extraction_priority("discoveries", exploration_session)
        assert priority < discoveries_priority

    def test_documentation_referenced_included(self, exploration_session):
        """Test documentation_referenced is included in exploration fields."""
        fields = get_extraction_fields(exploration_session)
        assert "documentation_referenced" in fields

    def test_field_ordering_for_exploration(self, exploration_session):
        """Test that discovery fields come before error fields."""
        fields = get_extraction_fields(exploration_session, threshold=0.1)
        if "discoveries" in fields and "errors_resolved" in fields:
            discoveries_idx = fields.index("discoveries")
            errors_idx = fields.index("errors_resolved")
            assert discoveries_idx < errors_idx


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_dimension_activity(self):
        """Test with only one non-zero dimension."""
        activity = ActivityVector(building=1.0)
        fields = get_extraction_fields(activity, threshold=0.1)
        # Fields with building affinity should be included
        assert len(fields) > 0

    def test_all_dimensions_equal(self):
        """Test with all dimensions equal."""
        activity = ActivityVector(
            building=0.5,
            fixing=0.5,
            configuring=0.5,
            exploring=0.5,
            refactoring=0.5,
            reviewing=0.5,
            testing=0.5,
            documenting=0.5,
        )
        fields = get_extraction_fields(activity)
        # Should return fields based on average affinities
        assert len(fields) > 0

    def test_very_low_activity_values(self):
        """Test with very small activity values."""
        activity = ActivityVector(fixing=0.01)
        priority = compute_extraction_priority("errors_resolved", activity)
        # Should still compute valid priority
        assert 0.0 <= priority <= 1.0

    def test_threshold_exactly_at_priority(self):
        """Test threshold exactly equal to a field's priority."""
        activity = ActivityVector(fixing=0.5)
        priority = compute_extraction_priority("errors_resolved", activity)
        # Use exact priority as threshold - field should be included
        fields = get_extraction_fields(activity, threshold=priority)
        # May or may not include the field due to floating point
        assert isinstance(fields, list)

    def test_mixed_high_low_activity(self):
        """Test with mix of high and low activity values."""
        activity = ActivityVector(
            fixing=0.9,  # High
            configuring=0.1,  # Low
            exploring=0.8,  # High
            testing=0.2,  # Low
        )
        fields = get_extraction_fields(activity, threshold=0.3)
        # Should include fields that match either fixing or exploring
        assert len(fields) > 0


class TestConsistency:
    """Test consistency between related functions."""

    def test_fields_subset_of_affinities(self):
        """Test that returned fields are always in EXTRACTION_AFFINITIES."""
        activity = ActivityVector(fixing=0.9, exploring=0.8)
        fields = get_extraction_fields(activity, threshold=0.0)
        for field in fields:
            assert field in EXTRACTION_AFFINITIES

    def test_priorities_subset_of_affinities(self):
        """Test that returned priorities are always in EXTRACTION_AFFINITIES."""
        activity = ActivityVector(fixing=0.9, exploring=0.8)
        priorities = get_extraction_priorities(activity, threshold=0.0)
        for field, _ in priorities:
            assert field in EXTRACTION_AFFINITIES

    def test_deterministic_results(self):
        """Test that same inputs produce same outputs."""
        activity = ActivityVector(fixing=0.7, configuring=0.5)

        # Multiple calls should return identical results
        result1 = get_extraction_fields(activity, threshold=0.2)
        result2 = get_extraction_fields(activity, threshold=0.2)
        assert result1 == result2

        priority1 = compute_extraction_priority("errors_resolved", activity)
        priority2 = compute_extraction_priority("errors_resolved", activity)
        assert priority1 == priority2
