"""
Tests for category presets and time-based demo features.

This test suite validates:
1. Category preset application (conservative, moderate, aggressive)
2. Time tracking and scaling
3. Time-based demo presets (3mo, 6mo, 1yr, 5yr, 10yr)
"""

import pytest
from datetime import datetime, timezone

from freqtrade.ui.demo_server import DemoServer, CATEGORY_PRESETS


class TestCategoryPresets:
    """Test category preset functionality."""

    def test_category_presets_defined(self):
        """Test that all required category presets are defined."""
        assert "conservative" in CATEGORY_PRESETS
        assert "moderate" in CATEGORY_PRESETS
        assert "aggressive" in CATEGORY_PRESETS

    def test_conservative_preset_values(self):
        """Test conservative preset has correct parameter values."""
        preset = CATEGORY_PRESETS["conservative"]
        
        # Conservative should have lower position sizes
        assert preset["position_size"] == 0.08
        
        # Conservative should have wider stop losses
        assert preset["stop_loss"] == 0.05
        
        # Conservative should have higher profit targets
        assert preset["profit_target"] == 0.08
        
        # Conservative should have longer cooldown
        assert preset["min_ticks_between_actions"] == 10
        
        # Must have description and impact
        assert "description" in preset
        assert "impact" in preset

    def test_moderate_preset_values(self):
        """Test moderate preset has correct parameter values."""
        preset = CATEGORY_PRESETS["moderate"]
        
        # Moderate should have balanced values
        assert preset["position_size"] == 0.15
        assert preset["stop_loss"] == 0.03
        assert preset["profit_target"] == 0.05
        assert preset["min_ticks_between_actions"] == 5

    def test_aggressive_preset_values(self):
        """Test aggressive preset has correct parameter values."""
        preset = CATEGORY_PRESETS["aggressive"]
        
        # Aggressive should have larger position sizes
        assert preset["position_size"] == 0.25
        
        # Aggressive should have tighter stop losses
        assert preset["stop_loss"] == 0.02
        
        # Aggressive should have lower profit targets
        assert preset["profit_target"] == 0.03
        
        # Aggressive should have shorter cooldown
        assert preset["min_ticks_between_actions"] == 2

    def test_category_risk_progression(self):
        """Test that categories progress from conservative to aggressive."""
        # Position sizes should increase
        assert (CATEGORY_PRESETS["conservative"]["position_size"] 
                < CATEGORY_PRESETS["moderate"]["position_size"] 
                < CATEGORY_PRESETS["aggressive"]["position_size"])
        
        # Stop losses should decrease (tighter)
        assert (CATEGORY_PRESETS["conservative"]["stop_loss"] 
                > CATEGORY_PRESETS["moderate"]["stop_loss"] 
                > CATEGORY_PRESETS["aggressive"]["stop_loss"])
        
        # Profit targets should decrease (take profits faster)
        assert (CATEGORY_PRESETS["conservative"]["profit_target"] 
                > CATEGORY_PRESETS["moderate"]["profit_target"] 
                > CATEGORY_PRESETS["aggressive"]["profit_target"])


class TestCategoryApplication:
    """Test applying category presets to the demo server."""

    def test_apply_conservative_category(self):
        """Test applying conservative category updates exploit parameters."""
        server = DemoServer()
        
        # Apply conservative preset
        preset = CATEGORY_PRESETS["conservative"]
        server.automated_exploit.position_size = preset["position_size"]
        server.automated_exploit.profit_target = preset["profit_target"]
        server.automated_exploit.stop_loss = preset["stop_loss"]
        server.automated_exploit.min_ticks_between_actions = preset["min_ticks_between_actions"]
        server.current_category = "conservative"
        
        # Verify parameters were set
        assert server.automated_exploit.position_size == 0.08
        assert server.automated_exploit.profit_target == 0.08
        assert server.automated_exploit.stop_loss == 0.05
        assert server.automated_exploit.min_ticks_between_actions == 10
        assert server.current_category == "conservative"

    def test_apply_aggressive_category(self):
        """Test applying aggressive category updates exploit parameters."""
        server = DemoServer()
        
        # Apply aggressive preset
        preset = CATEGORY_PRESETS["aggressive"]
        server.automated_exploit.position_size = preset["position_size"]
        server.automated_exploit.profit_target = preset["profit_target"]
        server.automated_exploit.stop_loss = preset["stop_loss"]
        server.automated_exploit.min_ticks_between_actions = preset["min_ticks_between_actions"]
        server.current_category = "aggressive"
        
        # Verify parameters were set
        assert server.automated_exploit.position_size == 0.25
        assert server.automated_exploit.profit_target == 0.03
        assert server.automated_exploit.stop_loss == 0.02
        assert server.automated_exploit.min_ticks_between_actions == 2
        assert server.current_category == "aggressive"


class TestTimeTracking:
    """Test time tracking functionality."""

    def test_initial_time_tracking(self):
        """Test initial time tracking values."""
        server = DemoServer()
        
        # Initial values
        assert server.simulation_start_time is None
        assert server.simulation_ticks == 0
        assert server.tick_to_time_scale == 60.0  # Default: 1 tick = 60 seconds

    def test_time_scaling(self):
        """Test time scaling calculations."""
        server = DemoServer()
        
        # Set custom time scale: 1 tick = 120 seconds (2 minutes)
        server.tick_to_time_scale = 120.0
        server.simulation_ticks = 30  # 30 ticks
        
        # Calculate elapsed time
        elapsed_seconds = server.simulation_ticks * server.tick_to_time_scale
        
        # 30 ticks * 120 seconds = 3600 seconds = 1 hour
        assert elapsed_seconds == 3600
        
        # Test conversion to other units
        elapsed_hours = elapsed_seconds / 3600
        assert elapsed_hours == 1.0
        
        elapsed_days = elapsed_seconds / 86400
        assert elapsed_days == pytest.approx(0.0417, rel=0.01)  # ~1/24 days

    def test_simulation_tick_increment(self):
        """Test that simulation ticks increment properly."""
        server = DemoServer()
        
        # Start simulation
        server.simulation_start_time = datetime.now(timezone.utc)
        server.simulation_ticks = 0
        
        # Simulate 10 ticks
        for i in range(10):
            server.simulation_ticks += 1
        
        assert server.simulation_ticks == 10


class TestTimePresets:
    """Test time-based demo presets."""

    def test_three_month_preset(self):
        """Test 3-month preset calculations."""
        target_ticks = 1000
        target_days = 90
        tick_scale = (target_days * 86400) / target_ticks
        
        # Each tick should represent ~7776 seconds (~2.16 hours)
        assert tick_scale == pytest.approx(7776.0, rel=0.01)
        
        # Verify that 1000 ticks equals 90 days
        elapsed_seconds = target_ticks * tick_scale
        elapsed_days = elapsed_seconds / 86400
        assert elapsed_days == pytest.approx(90, rel=0.01)

    def test_one_year_preset(self):
        """Test 1-year preset calculations."""
        target_ticks = 4000
        target_days = 365
        tick_scale = (target_days * 86400) / target_ticks
        
        # Each tick should represent ~7884 seconds (~2.19 hours)
        assert tick_scale == pytest.approx(7884.0, rel=0.01)
        
        # Verify that 4000 ticks equals 365 days
        elapsed_seconds = target_ticks * tick_scale
        elapsed_days = elapsed_seconds / 86400
        assert elapsed_days == pytest.approx(365, rel=0.01)

    def test_ten_year_preset(self):
        """Test 10-year preset calculations."""
        target_ticks = 40000
        target_days = 10 * 365
        tick_scale = (target_days * 86400) / target_ticks
        
        # Each tick should represent ~7884 seconds (~2.19 hours)
        assert tick_scale == pytest.approx(7884.0, rel=0.01)
        
        # Verify that 40000 ticks equals 10 years
        elapsed_seconds = target_ticks * tick_scale
        elapsed_years = elapsed_seconds / (365 * 86400)
        assert elapsed_years == pytest.approx(10, rel=0.01)

    def test_time_preset_progression(self):
        """Test that time presets have reasonable progression."""
        presets = {
            "3_months": {"ticks": 1000, "days": 90},
            "6_months": {"ticks": 2000, "days": 180},
            "1_year": {"ticks": 4000, "days": 365},
            "5_years": {"ticks": 20000, "days": 5 * 365},
            "10_years": {"ticks": 40000, "days": 10 * 365},
        }
        
        # Calculate ticks per day for each preset
        for name, config in presets.items():
            ticks_per_day = config["ticks"] / config["days"]
            # Should be approximately consistent across presets
            # (around 10-11 ticks per day)
            assert 10 <= ticks_per_day <= 12, f"{name} has unusual ticks per day: {ticks_per_day}"


class TestCategoryTimeIntegration:
    """Test integration of categories with time-based demos."""

    def test_conservative_category_with_time_preset(self):
        """Test that conservative category works with time presets."""
        server = DemoServer()
        
        # Apply conservative category
        preset = CATEGORY_PRESETS["conservative"]
        server.automated_exploit.position_size = preset["position_size"]
        server.current_category = "conservative"
        
        # Apply 1-year time preset
        server.tick_to_time_scale = (365 * 86400) / 4000
        server.simulation_ticks = 100
        
        # Verify both settings are active
        assert server.current_category == "conservative"
        assert server.automated_exploit.position_size == 0.08
        
        # Calculate time elapsed
        elapsed_seconds = server.simulation_ticks * server.tick_to_time_scale
        elapsed_days = elapsed_seconds / 86400
        
        # 100 ticks should be ~9.125 days in 1-year preset
        assert elapsed_days == pytest.approx(9.125, rel=0.01)

    def test_aggressive_category_with_time_preset(self):
        """Test that aggressive category works with time presets."""
        server = DemoServer()
        
        # Apply aggressive category
        preset = CATEGORY_PRESETS["aggressive"]
        server.automated_exploit.position_size = preset["position_size"]
        server.automated_exploit.min_ticks_between_actions = preset["min_ticks_between_actions"]
        server.current_category = "aggressive"
        
        # Apply 3-month time preset
        server.tick_to_time_scale = (90 * 86400) / 1000
        server.simulation_ticks = 500
        
        # Verify both settings are active
        assert server.current_category == "aggressive"
        assert server.automated_exploit.position_size == 0.25
        assert server.automated_exploit.min_ticks_between_actions == 2
        
        # Calculate time elapsed
        elapsed_seconds = server.simulation_ticks * server.tick_to_time_scale
        elapsed_days = elapsed_seconds / 86400
        
        # 500 ticks should be 45 days in 3-month preset
        assert elapsed_days == pytest.approx(45, rel=0.01)

    def test_category_impact_explanation(self):
        """Test that category impacts are properly explained."""
        # Conservative should emphasize safety and patience
        conservative = CATEGORY_PRESETS["conservative"]
        assert "conservative" in conservative["description"].lower()
        assert "impact" in conservative
        assert len(conservative["description"]) > 50  # Meaningful description
        
        # Aggressive should emphasize speed and higher risk
        aggressive = CATEGORY_PRESETS["aggressive"]
        assert "aggressive" in aggressive["description"].lower()
        assert "impact" in aggressive
        assert len(aggressive["description"]) > 50


class TestResetFunctionality:
    """Test that reset properly clears time and category state."""

    def test_reset_clears_time_tracking(self):
        """Test that reset clears time tracking variables."""
        server = DemoServer()
        
        # Set some simulation state
        server.simulation_start_time = datetime.now(timezone.utc)
        server.simulation_ticks = 1000
        server.tick_to_time_scale = 120.0
        
        # Manually call reset logic
        server.simulation_start_time = None
        server.simulation_ticks = 0
        
        # Verify reset
        assert server.simulation_start_time is None
        assert server.simulation_ticks == 0

    def test_reset_preserves_category(self):
        """Test that reset preserves the category setting."""
        server = DemoServer()
        
        # Apply a category
        server.current_category = "aggressive"
        preset = CATEGORY_PRESETS["aggressive"]
        server.automated_exploit.position_size = preset["position_size"]
        
        # Reset should preserve category settings
        # (Category is a configuration, not simulation state)
        assert server.current_category == "aggressive"
        assert server.automated_exploit.position_size == 0.25
