"""
DSPy Guardrails - Bounded Parameter Control

This module enforces safety constraints on DSPy parameter suggestions:
- Thresholds: ±20% adjustment bounds
- Allocation weights: ±10% adjustment bounds
- Forbidden actions: placing orders, changing leverage, disabling risk controls

These guardrails ensure that DSPy suggestions remain safe and within acceptable bounds.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ParameterType(Enum):
    """Types of parameters that DSPy can suggest adjustments for."""
    
    THRESHOLD = "threshold"  # ±20% bounds (stop_loss, holding_time, etc.)
    ALLOCATION_WEIGHT = "allocation_weight"  # ±10% bounds (position_size_multiplier)
    FORBIDDEN = "forbidden"  # Cannot be adjusted by DSPy


# Parameter type mappings
PARAMETER_TYPE_MAP = {
    # Thresholds - ±20% adjustment bounds
    "stop_loss_percent": ParameterType.THRESHOLD,
    "max_holding_hours": ParameterType.THRESHOLD,
    "trailing_stop_percent": ParameterType.THRESHOLD,
    "risk_threshold": ParameterType.THRESHOLD,
    
    # Allocation weights - ±10% adjustment bounds
    "position_size_multiplier": ParameterType.ALLOCATION_WEIGHT,
    "allocation_weight": ParameterType.ALLOCATION_WEIGHT,
    "stake_weight": ParameterType.ALLOCATION_WEIGHT,
    
    # Forbidden parameters - DSPy cannot adjust these
    "leverage": ParameterType.FORBIDDEN,
    "max_leverage": ParameterType.FORBIDDEN,
    "enable_risk_controls": ParameterType.FORBIDDEN,
    "place_order": ParameterType.FORBIDDEN,
    "order_placement": ParameterType.FORBIDDEN,
}

# Bound constants
THRESHOLD_MAX_CHANGE = 0.20  # ±20%
ALLOCATION_WEIGHT_MAX_CHANGE = 0.10  # ±10%


@dataclass
class GuardrailViolation:
    """
    Represents a guardrail violation.
    
    Attributes:
        parameter_name: Name of the parameter that violated bounds
        parameter_type: Type of parameter
        attempted_change: The change that was attempted (as a fraction/delta)
        max_allowed_change: Maximum allowed change for this parameter type
        reason: Description of why this violates guardrails
    """
    
    parameter_name: str
    parameter_type: ParameterType
    attempted_change: float
    max_allowed_change: float
    reason: str


class DSPyGuardrails:
    """
    Enforces safety bounds on DSPy parameter suggestions.
    
    This class ensures that all DSPy suggestions comply with safety constraints:
    - Thresholds can only be adjusted by ±20%
    - Allocation weights can only be adjusted by ±10%
    - Forbidden parameters cannot be adjusted at all
    
    Example:
        >>> guardrails = DSPyGuardrails()
        >>> 
        >>> # Validate a suggestion
        >>> is_valid, violation = guardrails.validate_suggestion(
        ...     parameter_name="position_size_multiplier",
        ...     current_value=1.0,
        ...     suggested_value=1.05,
        ... )
        >>> 
        >>> if not is_valid:
        ...     print(f"Violation: {violation.reason}")
        ... else:
        ...     print("Suggestion is within bounds")
    """
    
    def __init__(self, enforce_bounds: bool = True):
        """
        Initialize the guardrails.
        
        Args:
            enforce_bounds: Whether to enforce bounds (default: True)
                           Setting to False will only log violations but not reject them
        """
        self.enforce_bounds = enforce_bounds
        self._violation_count = 0
        self._violation_history: list[GuardrailViolation] = []
        
        logger.info(f"DSPy Guardrails initialized (enforce_bounds={enforce_bounds})")
        logger.info(f"  - Thresholds: ±{THRESHOLD_MAX_CHANGE:.0%} bounds")
        logger.info(f"  - Allocation weights: ±{ALLOCATION_WEIGHT_MAX_CHANGE:.0%} bounds")
        logger.info(f"  - Forbidden parameters: Cannot be adjusted")
    
    def get_parameter_type(self, parameter_name: str) -> ParameterType:
        """
        Get the type of a parameter.
        
        Args:
            parameter_name: Name of the parameter
            
        Returns:
            Parameter type (defaults to THRESHOLD if not found)
        """
        return PARAMETER_TYPE_MAP.get(parameter_name, ParameterType.THRESHOLD)
    
    def get_max_allowed_change(self, parameter_name: str) -> float:
        """
        Get the maximum allowed change for a parameter.
        
        Args:
            parameter_name: Name of the parameter
            
        Returns:
            Maximum allowed change as a fraction (e.g., 0.20 for ±20%)
        """
        param_type = self.get_parameter_type(parameter_name)
        
        if param_type == ParameterType.THRESHOLD:
            return THRESHOLD_MAX_CHANGE
        elif param_type == ParameterType.ALLOCATION_WEIGHT:
            return ALLOCATION_WEIGHT_MAX_CHANGE
        else:  # FORBIDDEN
            return 0.0
    
    def validate_suggestion(
        self,
        parameter_name: str,
        current_value: float,
        suggested_value: float,
    ) -> tuple[bool, Optional[GuardrailViolation]]:
        """
        Validate that a parameter suggestion complies with guardrails.
        
        Args:
            parameter_name: Name of the parameter being adjusted
            current_value: Current value of the parameter
            suggested_value: Suggested new value
            
        Returns:
            Tuple of (is_valid, violation)
            - is_valid: True if suggestion is within bounds, False otherwise
            - violation: GuardrailViolation object if invalid, None if valid
        """
        param_type = self.get_parameter_type(parameter_name)
        
        # Check if parameter is forbidden
        if param_type == ParameterType.FORBIDDEN:
            violation = GuardrailViolation(
                parameter_name=parameter_name,
                parameter_type=param_type,
                attempted_change=suggested_value - current_value,
                max_allowed_change=0.0,
                reason=f"Parameter '{parameter_name}' is forbidden from DSPy adjustment "
                       f"(cannot place orders, change leverage, or disable risk controls)",
            )
            self._record_violation(violation)
            return False, violation
        
        # Calculate the change as a fraction of current value
        if current_value == 0:
            # For zero current value, use absolute change
            change_fraction = abs(suggested_value)
        else:
            change_fraction = abs((suggested_value - current_value) / current_value)
        
        max_allowed = self.get_max_allowed_change(parameter_name)
        
        # Check if change exceeds bounds
        if change_fraction > max_allowed:
            violation = GuardrailViolation(
                parameter_name=parameter_name,
                parameter_type=param_type,
                attempted_change=change_fraction,
                max_allowed_change=max_allowed,
                reason=f"Suggested change of {change_fraction:.1%} exceeds "
                       f"maximum allowed {max_allowed:.0%} for {param_type.value}",
            )
            self._record_violation(violation)
            return False, violation
        
        return True, None
    
    def apply_bounds(
        self,
        parameter_name: str,
        current_value: float,
        suggested_value: float,
    ) -> float:
        """
        Apply guardrail bounds to a suggested value.
        
        If the suggested value is within bounds, it's returned unchanged.
        If it exceeds bounds, it's clamped to the maximum allowed change.
        
        Args:
            parameter_name: Name of the parameter
            current_value: Current value of the parameter
            suggested_value: Suggested new value
            
        Returns:
            Bounded suggested value
        """
        param_type = self.get_parameter_type(parameter_name)
        
        # Forbidden parameters cannot be changed at all
        if param_type == ParameterType.FORBIDDEN:
            logger.warning(
                f"Attempted to adjust forbidden parameter '{parameter_name}' - "
                f"returning current value"
            )
            return current_value
        
        max_allowed = self.get_max_allowed_change(parameter_name)
        
        # Calculate allowed range
        if current_value == 0:
            # For zero values, use absolute bounds
            min_value = -max_allowed
            max_value = max_allowed
        else:
            min_value = current_value * (1 - max_allowed)
            max_value = current_value * (1 + max_allowed)
        
        # Clamp to bounds
        bounded_value = max(min_value, min(max_value, suggested_value))
        
        # Log if we had to clamp
        if bounded_value != suggested_value:
            logger.warning(
                f"DSPy suggestion for '{parameter_name}' clamped: "
                f"{suggested_value:.4f} → {bounded_value:.4f} "
                f"(max change: ±{max_allowed:.0%})"
            )
        
        return bounded_value
    
    def _record_violation(self, violation: GuardrailViolation) -> None:
        """Record a guardrail violation."""
        self._violation_count += 1
        self._violation_history.append(violation)
        
        logger.warning(
            f"Guardrail violation #{self._violation_count}: {violation.reason}"
        )
    
    def get_violation_stats(self) -> dict:
        """
        Get statistics about guardrail violations.
        
        Returns:
            Dictionary with violation statistics
        """
        return {
            "total_violations": self._violation_count,
            "violations_by_type": {
                param_type.value: sum(
                    1 for v in self._violation_history if v.parameter_type == param_type
                )
                for param_type in ParameterType
            },
            "recent_violations": [
                {
                    "parameter": v.parameter_name,
                    "type": v.parameter_type.value,
                    "attempted_change": f"{v.attempted_change:.1%}",
                    "max_allowed": f"{v.max_allowed_change:.0%}",
                    "reason": v.reason,
                }
                for v in self._violation_history[-10:]  # Last 10 violations
            ],
        }
    
    def reset(self) -> None:
        """Reset violation tracking."""
        self._violation_count = 0
        self._violation_history.clear()
        logger.info("Guardrail violation tracking reset")
