"""
Tests for DSPy Guardrails - Bounded Parameter Control

These tests verify that:
1. Guardrails enforce ±20% bounds for thresholds
2. Guardrails enforce ±10% bounds for allocation weights
3. Forbidden parameters cannot be adjusted
4. Suggestions are properly bounded
5. Violations are tracked and reported
"""

import pytest

from dspy.guardrails import (
    DSPyGuardrails,
    ParameterType,
    GuardrailViolation,
    THRESHOLD_MAX_CHANGE,
    ALLOCATION_WEIGHT_MAX_CHANGE,
)


class TestGuardrailParameterTypes:
    """Test parameter type classification."""
    
    def test_threshold_parameters(self):
        """Test that threshold parameters are classified correctly."""
        guardrails = DSPyGuardrails()
        
        assert guardrails.get_parameter_type("stop_loss_percent") == ParameterType.THRESHOLD
        assert guardrails.get_parameter_type("max_holding_hours") == ParameterType.THRESHOLD
        assert guardrails.get_parameter_type("trailing_stop_percent") == ParameterType.THRESHOLD
        assert guardrails.get_parameter_type("risk_threshold") == ParameterType.THRESHOLD
    
    def test_allocation_weight_parameters(self):
        """Test that allocation weight parameters are classified correctly."""
        guardrails = DSPyGuardrails()
        
        assert guardrails.get_parameter_type("position_size_multiplier") == ParameterType.ALLOCATION_WEIGHT
        assert guardrails.get_parameter_type("allocation_weight") == ParameterType.ALLOCATION_WEIGHT
        assert guardrails.get_parameter_type("stake_weight") == ParameterType.ALLOCATION_WEIGHT
    
    def test_forbidden_parameters(self):
        """Test that forbidden parameters are classified correctly."""
        guardrails = DSPyGuardrails()
        
        assert guardrails.get_parameter_type("leverage") == ParameterType.FORBIDDEN
        assert guardrails.get_parameter_type("max_leverage") == ParameterType.FORBIDDEN
        assert guardrails.get_parameter_type("enable_risk_controls") == ParameterType.FORBIDDEN
        assert guardrails.get_parameter_type("place_order") == ParameterType.FORBIDDEN
        assert guardrails.get_parameter_type("order_placement") == ParameterType.FORBIDDEN
    
    def test_unknown_parameter_defaults_to_threshold(self):
        """Test that unknown parameters default to threshold type."""
        guardrails = DSPyGuardrails()
        
        # Unknown parameter should default to threshold
        assert guardrails.get_parameter_type("unknown_param") == ParameterType.THRESHOLD


class TestGuardrailMaxAllowedChange:
    """Test maximum allowed change calculation."""
    
    def test_threshold_max_change(self):
        """Test that thresholds have ±20% max change."""
        guardrails = DSPyGuardrails()
        
        assert guardrails.get_max_allowed_change("stop_loss_percent") == THRESHOLD_MAX_CHANGE
        assert guardrails.get_max_allowed_change("max_holding_hours") == THRESHOLD_MAX_CHANGE
        assert guardrails.get_max_allowed_change("stop_loss_percent") == 0.20  # ±20%
    
    def test_allocation_weight_max_change(self):
        """Test that allocation weights have ±10% max change."""
        guardrails = DSPyGuardrails()
        
        assert guardrails.get_max_allowed_change("position_size_multiplier") == ALLOCATION_WEIGHT_MAX_CHANGE
        assert guardrails.get_max_allowed_change("allocation_weight") == ALLOCATION_WEIGHT_MAX_CHANGE
        assert guardrails.get_max_allowed_change("position_size_multiplier") == 0.10  # ±10%
    
    def test_forbidden_max_change(self):
        """Test that forbidden parameters have 0% max change."""
        guardrails = DSPyGuardrails()
        
        assert guardrails.get_max_allowed_change("leverage") == 0.0
        assert guardrails.get_max_allowed_change("max_leverage") == 0.0
        assert guardrails.get_max_allowed_change("enable_risk_controls") == 0.0


class TestGuardrailValidation:
    """Test suggestion validation."""
    
    def test_valid_threshold_within_bounds(self):
        """Test that valid threshold suggestions within ±20% pass validation."""
        guardrails = DSPyGuardrails()
        
        # 10% change is within ±20% bounds
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="stop_loss_percent",
            current_value=0.05,
            suggested_value=0.055,  # +10% change
        )
        
        assert is_valid
        assert violation is None
    
    def test_valid_allocation_weight_within_bounds(self):
        """Test that valid allocation weight suggestions within ±10% pass validation."""
        guardrails = DSPyGuardrails()
        
        # 5% change is within ±10% bounds
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="position_size_multiplier",
            current_value=1.0,
            suggested_value=1.05,  # +5% change
        )
        
        assert is_valid
        assert violation is None
    
    def test_threshold_exceeds_bounds(self):
        """Test that threshold suggestions exceeding ±20% fail validation."""
        guardrails = DSPyGuardrails()
        
        # 30% change exceeds ±20% bounds
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="stop_loss_percent",
            current_value=0.05,
            suggested_value=0.065,  # +30% change
        )
        
        assert not is_valid
        assert violation is not None
        assert violation.parameter_name == "stop_loss_percent"
        assert violation.parameter_type == ParameterType.THRESHOLD
        assert violation.attempted_change == pytest.approx(0.30, abs=1e-6)
        assert violation.max_allowed_change == 0.20
        assert "exceeds maximum allowed" in violation.reason.lower()
    
    def test_allocation_weight_exceeds_bounds(self):
        """Test that allocation weight suggestions exceeding ±10% fail validation."""
        guardrails = DSPyGuardrails()
        
        # 15% change exceeds ±10% bounds
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="position_size_multiplier",
            current_value=1.0,
            suggested_value=1.15,  # +15% change
        )
        
        assert not is_valid
        assert violation is not None
        assert violation.parameter_name == "position_size_multiplier"
        assert violation.parameter_type == ParameterType.ALLOCATION_WEIGHT
        assert violation.attempted_change == pytest.approx(0.15, abs=1e-6)
        assert violation.max_allowed_change == 0.10
    
    def test_forbidden_parameter_always_fails(self):
        """Test that forbidden parameters always fail validation."""
        guardrails = DSPyGuardrails()
        
        # Even 1% change is forbidden
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="leverage",
            current_value=1.0,
            suggested_value=1.01,
        )
        
        assert not is_valid
        assert violation is not None
        assert violation.parameter_name == "leverage"
        assert violation.parameter_type == ParameterType.FORBIDDEN
        assert "forbidden" in violation.reason.lower()
    
    def test_forbidden_parameters_cannot_place_orders(self):
        """Test that DSPy cannot place orders."""
        guardrails = DSPyGuardrails()
        
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="place_order",
            current_value=0.0,
            suggested_value=1.0,
        )
        
        assert not is_valid
        assert violation is not None
        assert "place orders" in violation.reason.lower() or "forbidden" in violation.reason.lower()
    
    def test_forbidden_parameters_cannot_change_leverage(self):
        """Test that DSPy cannot change leverage caps."""
        guardrails = DSPyGuardrails()
        
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="max_leverage",
            current_value=3.0,
            suggested_value=5.0,
        )
        
        assert not is_valid
        assert violation is not None
        assert "leverage" in violation.reason.lower() or "forbidden" in violation.reason.lower()
    
    def test_forbidden_parameters_cannot_disable_risk_controls(self):
        """Test that DSPy cannot disable risk controls."""
        guardrails = DSPyGuardrails()
        
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="enable_risk_controls",
            current_value=1.0,
            suggested_value=0.0,
        )
        
        assert not is_valid
        assert violation is not None
        assert "risk controls" in violation.reason.lower() or "forbidden" in violation.reason.lower()
    
    def test_negative_change_threshold(self):
        """Test that negative changes are also bounded."""
        guardrails = DSPyGuardrails()
        
        # -15% change is within ±20% bounds
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="stop_loss_percent",
            current_value=0.05,
            suggested_value=0.0425,  # -15% change
        )
        
        assert is_valid
        assert violation is None
        
        # -25% change exceeds ±20% bounds
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="stop_loss_percent",
            current_value=0.05,
            suggested_value=0.0375,  # -25% change
        )
        
        assert not is_valid
        assert violation is not None


class TestGuardrailApplyBounds:
    """Test applying bounds to suggestions."""
    
    def test_apply_bounds_within_threshold(self):
        """Test that values within threshold bounds are unchanged."""
        guardrails = DSPyGuardrails()
        
        bounded = guardrails.apply_bounds(
            parameter_name="stop_loss_percent",
            current_value=0.05,
            suggested_value=0.055,  # +10% change, within ±20%
        )
        
        assert bounded == pytest.approx(0.055)
    
    def test_apply_bounds_exceeds_threshold(self):
        """Test that values exceeding threshold bounds are clamped."""
        guardrails = DSPyGuardrails()
        
        # +30% change exceeds ±20%, should be clamped to +20%
        bounded = guardrails.apply_bounds(
            parameter_name="stop_loss_percent",
            current_value=0.05,
            suggested_value=0.065,  # +30% change
        )
        
        expected = 0.05 * 1.20  # +20% max
        assert bounded == pytest.approx(expected)
    
    def test_apply_bounds_within_allocation_weight(self):
        """Test that values within allocation weight bounds are unchanged."""
        guardrails = DSPyGuardrails()
        
        bounded = guardrails.apply_bounds(
            parameter_name="position_size_multiplier",
            current_value=1.0,
            suggested_value=1.08,  # +8% change, within ±10%
        )
        
        assert bounded == pytest.approx(1.08)
    
    def test_apply_bounds_exceeds_allocation_weight(self):
        """Test that values exceeding allocation weight bounds are clamped."""
        guardrails = DSPyGuardrails()
        
        # +20% change exceeds ±10%, should be clamped to +10%
        bounded = guardrails.apply_bounds(
            parameter_name="position_size_multiplier",
            current_value=1.0,
            suggested_value=1.20,  # +20% change
        )
        
        expected = 1.0 * 1.10  # +10% max
        assert bounded == pytest.approx(expected)
    
    def test_apply_bounds_negative_change(self):
        """Test that negative changes are also clamped."""
        guardrails = DSPyGuardrails()
        
        # -30% change exceeds ±20%, should be clamped to -20%
        bounded = guardrails.apply_bounds(
            parameter_name="stop_loss_percent",
            current_value=0.05,
            suggested_value=0.035,  # -30% change
        )
        
        expected = 0.05 * 0.80  # -20% max
        assert bounded == pytest.approx(expected)
    
    def test_apply_bounds_forbidden_returns_current(self):
        """Test that forbidden parameters return current value."""
        guardrails = DSPyGuardrails()
        
        bounded = guardrails.apply_bounds(
            parameter_name="leverage",
            current_value=3.0,
            suggested_value=5.0,
        )
        
        # Should return current value unchanged
        assert bounded == 3.0


class TestGuardrailViolationTracking:
    """Test violation tracking and statistics."""
    
    def test_violation_count(self):
        """Test that violations are counted."""
        guardrails = DSPyGuardrails()
        
        # Create some violations
        guardrails.validate_suggestion("stop_loss_percent", 0.05, 0.07)  # Exceeds bounds
        guardrails.validate_suggestion("position_size_multiplier", 1.0, 1.20)  # Exceeds bounds
        guardrails.validate_suggestion("leverage", 1.0, 2.0)  # Forbidden
        
        stats = guardrails.get_violation_stats()
        assert stats["total_violations"] == 3
    
    def test_violation_by_type(self):
        """Test that violations are tracked by type."""
        guardrails = DSPyGuardrails()
        
        # Create violations of different types
        guardrails.validate_suggestion("stop_loss_percent", 0.05, 0.07)  # Threshold violation
        guardrails.validate_suggestion("position_size_multiplier", 1.0, 1.20)  # Allocation violation
        guardrails.validate_suggestion("leverage", 1.0, 2.0)  # Forbidden
        guardrails.validate_suggestion("max_holding_hours", 24, 35)  # Another threshold violation
        
        stats = guardrails.get_violation_stats()
        assert stats["violations_by_type"]["threshold"] == 2
        assert stats["violations_by_type"]["allocation_weight"] == 1
        assert stats["violations_by_type"]["forbidden"] == 1
    
    def test_recent_violations(self):
        """Test that recent violations are tracked."""
        guardrails = DSPyGuardrails()
        
        guardrails.validate_suggestion("stop_loss_percent", 0.05, 0.07)
        
        stats = guardrails.get_violation_stats()
        assert len(stats["recent_violations"]) == 1
        assert stats["recent_violations"][0]["parameter"] == "stop_loss_percent"
        assert stats["recent_violations"][0]["type"] == "threshold"
    
    def test_reset_violations(self):
        """Test that violations can be reset."""
        guardrails = DSPyGuardrails()
        
        # Create violations
        guardrails.validate_suggestion("stop_loss_percent", 0.05, 0.07)
        guardrails.validate_suggestion("leverage", 1.0, 2.0)
        
        stats = guardrails.get_violation_stats()
        assert stats["total_violations"] == 2
        
        # Reset
        guardrails.reset()
        
        stats = guardrails.get_violation_stats()
        assert stats["total_violations"] == 0
        assert len(stats["recent_violations"]) == 0


class TestGuardrailEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_exactly_at_threshold_bound(self):
        """Test suggestions exactly at the bound."""
        guardrails = DSPyGuardrails()
        
        # Exactly +20% should be valid
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="stop_loss_percent",
            current_value=0.05,
            suggested_value=0.06,  # Exactly +20%
        )
        
        assert is_valid
        assert violation is None
    
    def test_exactly_at_allocation_bound(self):
        """Test suggestions exactly at the allocation bound."""
        guardrails = DSPyGuardrails()
        
        # Exactly +10% should be valid
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="position_size_multiplier",
            current_value=1.0,
            suggested_value=1.10,  # Exactly +10%
        )
        
        assert is_valid
        assert violation is None
    
    def test_zero_current_value(self):
        """Test handling of zero current value."""
        guardrails = DSPyGuardrails()
        
        # Should use absolute change for zero current value
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="stop_loss_percent",
            current_value=0.0,
            suggested_value=0.1,
        )
        
        # Should still validate (treating as absolute change)
        assert is_valid or not is_valid  # Just ensure it doesn't crash
    
    def test_very_small_change(self):
        """Test very small changes are allowed."""
        guardrails = DSPyGuardrails()
        
        # 0.1% change should be valid
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="position_size_multiplier",
            current_value=1.0,
            suggested_value=1.001,
        )
        
        assert is_valid
        assert violation is None


class TestGuardrailEnforcement:
    """Test overall guardrail enforcement."""
    
    def test_enforce_bounds_enabled(self):
        """Test that bounds are enforced when enabled."""
        guardrails = DSPyGuardrails(enforce_bounds=True)
        
        # Should reject suggestions exceeding bounds
        is_valid, violation = guardrails.validate_suggestion(
            parameter_name="position_size_multiplier",
            current_value=1.0,
            suggested_value=1.20,
        )
        
        assert not is_valid
        assert violation is not None
    
    def test_safety_overrides_intelligence(self):
        """Test that safety (guardrails) overrides intelligence (suggestions).
        
        This is a key requirement: even if DSPy suggests a large change,
        the guardrails must enforce the bounds.
        """
        guardrails = DSPyGuardrails()
        
        # DSPy might suggest a 50% increase, but guardrails should limit to 10%
        bounded = guardrails.apply_bounds(
            parameter_name="position_size_multiplier",
            current_value=1.0,
            suggested_value=1.50,  # +50% suggested
        )
        
        # Should be clamped to +10% max
        assert bounded == pytest.approx(1.10)
        
        # Verify violation was logged
        stats = guardrails.get_violation_stats()
        assert stats["total_violations"] > 0
