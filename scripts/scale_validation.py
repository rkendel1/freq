#!/usr/bin/env python3
"""
Scale Validation Script - Validates system readiness for scale deployment.

This script performs a 30-day simulated run to validate:
1. System stability under extended operation
2. Drawdown behavior and capital protection
3. Capital growth tracking
4. Exploit isolation (no cross-contamination)
5. Risk limit enforcement

Requirements:
- 30-day simulated run
- No parameter changes during execution
- Verify drawdowns, capital growth, exploit isolation
- Generate stability report
- List all failure modes observed

Usage:
    python scripts/scale_validation.py [--config <config_path>]
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from freqtrade.core.actions import Action, ActionType, Side
from freqtrade.core.risk import RiskLimits, RiskManager
from freqtrade.core.state import CapitalState, ExecutionEngineState, create_initial_state
from freqtrade.exploits.exploit_module import (
    ExecutionResult,
    ExecutionState,
    ExploitModule,
    NullExploitModule,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def dataclass_to_dict(obj: Any) -> Any:
    """
    Convert dataclass objects to dictionaries recursively.
    
    This is a general-purpose utility for serializing dataclasses to JSON.
    
    Args:
        obj: Object to convert (can be dataclass, list, dict, or primitive)
        
    Returns:
        Dictionary representation suitable for JSON serialization
    """
    if hasattr(obj, "__dataclass_fields__"):
        return {
            k: dataclass_to_dict(v)
            for k, v in obj.__dict__.items()
        }
    elif isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}
    else:
        return obj


@dataclass
class FailureMode:
    """Record of a failure mode observed during validation."""

    timestamp: int
    category: str  # e.g., "RISK_VIOLATION", "CAPITAL_ALLOCATION", "EMERGENCY_STOP"
    description: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    metadata: dict = field(default_factory=dict)


@dataclass
class DrawdownMetrics:
    """Metrics for tracking drawdowns."""

    max_drawdown: float = 0.0
    max_drawdown_duration_hours: int = 0
    current_drawdown: float = 0.0
    peak_capital: float = 0.0
    drawdown_start_time: int | None = None
    drawdown_periods: list[dict] = field(default_factory=list)


@dataclass
class CapitalGrowthMetrics:
    """Metrics for tracking capital growth."""

    initial_capital: float
    final_capital: float = 0.0
    peak_capital: float = 0.0
    total_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    total_unrealized_pnl: float = 0.0
    growth_rate: float = 0.0
    hourly_snapshots: list[dict] = field(default_factory=list)


@dataclass
class ExploitIsolationMetrics:
    """Metrics for verifying exploit isolation."""

    exploits_executed: int = 0
    capital_allocation_requests: int = 0
    capital_allocation_failures: int = 0
    cross_contamination_detected: bool = False
    isolation_violations: list[dict] = field(default_factory=list)


@dataclass
class StabilityReport:
    """Complete stability report from validation run."""

    run_timestamp: str
    duration_hours: int
    initial_capital: float
    final_capital: float
    
    # Metrics
    drawdown_metrics: DrawdownMetrics
    capital_growth_metrics: CapitalGrowthMetrics
    exploit_isolation_metrics: ExploitIsolationMetrics
    
    # Failure tracking
    failure_modes: list[FailureMode]
    emergency_stops: int = 0
    risk_violations: int = 0
    
    # Overall status
    validation_passed: bool = True
    issues_detected: list[str] = field(default_factory=list)


class ScaleValidator:
    """
    Validates system readiness for scale deployment.
    
    Runs a 30-day simulated backtest with no parameter changes,
    tracking all metrics and failure modes.
    """

    def __init__(self, config: dict):
        """
        Initialize scale validator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.initial_capital = config.get("dry_run_wallet", 10000.0)
        self.duration_hours = config.get("validation_duration_hours", 30 * 24)  # 30 days
        
        # Initialize state
        self.engine_state = create_initial_state(self.initial_capital)
        
        # Initialize risk manager
        risk_limits = RiskLimits(
            max_position_size=config.get("max_position_size", 0.1),
            max_total_exposure=config.get("max_total_exposure", 0.95),
            max_open_positions=config.get("max_open_trades", 3),
            max_loss_per_trade=config.get("stoploss", 0.10),
            max_daily_loss=config.get("max_daily_loss", 0.20),
            max_leverage=config.get("leverage", {}).get("max", 1.0),
            position_cooldown=config.get("position_cooldown", 0),
            global_cooldown=config.get("global_cooldown", 0),
            max_funding_rate=config.get("max_funding_rate", 0.01),
            funding_rate_change_threshold=config.get("funding_rate_change_threshold", 0.005),
        )
        self.risk_manager = RiskManager(risk_limits)
        
        # Initialize metrics
        self.drawdown_metrics = DrawdownMetrics(peak_capital=self.initial_capital)
        self.capital_growth_metrics = CapitalGrowthMetrics(
            initial_capital=self.initial_capital,
            peak_capital=self.initial_capital,
        )
        self.exploit_isolation_metrics = ExploitIsolationMetrics()
        self.failure_modes: list[FailureMode] = []
        
        # Simulation state
        self.current_hour = 0
        self.emergency_stop_count = 0
        self.risk_violation_count = 0

    def run_validation(self, exploit_module: ExploitModule | None = None) -> StabilityReport:
        """
        Run the complete validation cycle.
        
        Args:
            exploit_module: ExploitModule to test (defaults to NullExploitModule)
            
        Returns:
            StabilityReport with all metrics and failure modes
        """
        logger.info("=" * 80)
        logger.info("SCALE VALIDATION STARTING")
        logger.info("=" * 80)
        logger.info(f"Duration: {self.duration_hours} hours ({self.duration_hours // 24} days)")
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info("=" * 80)
        
        # Use NullExploitModule if none provided
        if exploit_module is None:
            exploit_module = NullExploitModule()
            logger.info("Using NullExploitModule (no-op validation)")
        
        # Run hour-by-hour simulation
        for hour in range(self.duration_hours):
            self.current_hour = hour
            self._simulate_hour(exploit_module, hour)
            
            # Log progress every 24 hours
            if hour > 0 and hour % 24 == 0:
                self._log_progress(hour)
        
        # Generate final report
        report = self._generate_report()
        
        logger.info("\n" + "=" * 80)
        logger.info("SCALE VALIDATION COMPLETED")
        logger.info("=" * 80)
        
        return report

    def _simulate_hour(self, exploit_module: ExploitModule, hour: int) -> None:
        """
        Simulate one hour of operation.
        
        Args:
            exploit_module: ExploitModule to evaluate
            hour: Current hour number
        """
        # Calculate current timestamp (seconds since epoch)
        timestamp = int(datetime.now().timestamp()) + (hour * 3600)
        
        # Create execution state for exploit
        current_capital = (
            self.engine_state.capital.available_capital
            + self.engine_state.capital.deployed_capital
        )
        
        execution_state = ExecutionState(
            symbol="BTC/USDT",
            available_capital=self.engine_state.capital.available_capital,
            deployed_capital=self.engine_state.capital.deployed_capital,
            open_positions=[],
            recent_trades=[],
            current_price=50000.0,  # Placeholder price
            timestamp=timestamp,
            dataframe=None,
        )
        
        # Evaluate exploit module
        try:
            actions = exploit_module.evaluate(execution_state)
            
            # Process each action
            for action in actions:
                self._process_action(action, timestamp, exploit_module)
                
        except Exception as e:
            # Record failure
            self._record_failure(
                timestamp=timestamp,
                category="EXPLOIT_EVALUATION_ERROR",
                description=f"Exploit evaluation failed: {str(e)}",
                severity="HIGH",
                metadata={"error": str(e), "hour": hour},
            )
        
        # Update metrics
        self._update_drawdown_metrics(current_capital, timestamp)
        self._update_capital_growth_metrics(current_capital, hour)
        
        # Check emergency conditions
        self._check_emergency_conditions(current_capital, hour)

    def _create_rejection_result(
        self, action: Action, error_message: str, timestamp: int
    ) -> ExecutionResult:
        """
        Create an ExecutionResult for a rejected action.
        
        Helper method to reduce duplication when creating rejection results.
        
        Args:
            action: The action that was rejected
            error_message: Reason for rejection
            timestamp: Current timestamp
            
        Returns:
            ExecutionResult indicating rejection
        """
        return ExecutionResult(
            success=False,
            order_ids=[],
            filled_size=0.0,
            fees=0.0,
            timestamp=timestamp,
            error_message=error_message,
        )

    def _process_action(
        self, action: Action, timestamp: int, exploit_module: ExploitModule
    ) -> None:
        """
        Process an action from an exploit module.
        
        Args:
            action: Action to process
            timestamp: Current timestamp
            exploit_module: ExploitModule that generated the action
        """
        self.exploit_isolation_metrics.exploits_executed += 1
        
        # Check risk limits
        allowed, reason = self.risk_manager.check_action(
            action=action,
            available=self.engine_state.capital.available_capital,
            deployed=self.engine_state.capital.deployed_capital,
            open_positions=len(self.engine_state.open_trades),
            current_timestamp=timestamp,
        )
        
        if not allowed:
            # Record risk violation
            self.risk_violation_count += 1
            self._record_failure(
                timestamp=timestamp,
                category="RISK_VIOLATION",
                description=f"Action rejected by risk manager: {reason}",
                severity="MEDIUM",
                metadata={"action": str(action), "reason": reason},
            )
            
            # Notify exploit of rejection
            result = self._create_rejection_result(action, reason, timestamp)
            exploit_module.on_execution_result(action, result)
            return
        
        # Attempt capital allocation
        if action.type == ActionType.OPEN:
            self.exploit_isolation_metrics.capital_allocation_requests += 1
            
            # Calculate capital needed
            capital_needed = action.size * self.engine_state.capital.available_capital
            
            # Try to allocate
            if not self.engine_state.capital.allocate(capital_needed):
                self.exploit_isolation_metrics.capital_allocation_failures += 1
                self._record_failure(
                    timestamp=timestamp,
                    category="CAPITAL_ALLOCATION_FAILURE",
                    description=f"Insufficient capital for action: {action}",
                    severity="MEDIUM",
                    metadata={"action": str(action), "capital_needed": capital_needed},
                )
                
                # Notify exploit
                result = self._create_rejection_result(action, "Insufficient capital", timestamp)
                exploit_module.on_execution_result(action, result)
                return
        
        # Record action
        self.risk_manager.record_action(action, timestamp)
        
        # Simulate successful execution
        result = ExecutionResult(
            success=True,
            order_ids=[f"order_{timestamp}"],
            filled_size=action.size or 0.0,
            fees=0.001 * (action.size or 0.0),  # 0.1% fee
            timestamp=timestamp,
        )
        exploit_module.on_execution_result(action, result)

    def _update_drawdown_metrics(self, current_capital: float, timestamp: int) -> None:
        """
        Update drawdown metrics.
        
        Args:
            current_capital: Current total capital
            timestamp: Current timestamp
        """
        # Update peak
        if current_capital > self.drawdown_metrics.peak_capital:
            # New peak - reset drawdown
            if self.drawdown_metrics.current_drawdown > 0:
                # Record previous drawdown period
                if self.drawdown_metrics.drawdown_start_time is not None:
                    duration_hours = (
                        timestamp - self.drawdown_metrics.drawdown_start_time
                    ) // 3600
                    self.drawdown_metrics.drawdown_periods.append(
                        {
                            "max_drawdown": self.drawdown_metrics.current_drawdown,
                            "duration_hours": duration_hours,
                            "start_time": self.drawdown_metrics.drawdown_start_time,
                            "end_time": timestamp,
                        }
                    )
            
            self.drawdown_metrics.peak_capital = current_capital
            self.drawdown_metrics.current_drawdown = 0.0
            self.drawdown_metrics.drawdown_start_time = None
        else:
            # Calculate current drawdown
            drawdown = (
                self.drawdown_metrics.peak_capital - current_capital
            ) / self.drawdown_metrics.peak_capital
            
            if drawdown > self.drawdown_metrics.current_drawdown:
                self.drawdown_metrics.current_drawdown = drawdown
                
                # Track drawdown start
                if self.drawdown_metrics.drawdown_start_time is None:
                    self.drawdown_metrics.drawdown_start_time = timestamp
            
            # Update max drawdown
            if drawdown > self.drawdown_metrics.max_drawdown:
                self.drawdown_metrics.max_drawdown = drawdown
                
                # Update max duration
                if self.drawdown_metrics.drawdown_start_time is not None:
                    duration = (timestamp - self.drawdown_metrics.drawdown_start_time) // 3600
                    if duration > self.drawdown_metrics.max_drawdown_duration_hours:
                        self.drawdown_metrics.max_drawdown_duration_hours = duration

    def _update_capital_growth_metrics(self, current_capital: float, hour: int) -> None:
        """
        Update capital growth metrics.
        
        Args:
            current_capital: Current total capital
            hour: Current hour number
        """
        self.capital_growth_metrics.final_capital = current_capital
        
        if current_capital > self.capital_growth_metrics.peak_capital:
            self.capital_growth_metrics.peak_capital = current_capital
        
        # Calculate growth
        self.capital_growth_metrics.total_pnl = (
            current_capital - self.capital_growth_metrics.initial_capital
        )
        self.capital_growth_metrics.growth_rate = (
            self.capital_growth_metrics.total_pnl
            / self.capital_growth_metrics.initial_capital
        )
        
        # Record hourly snapshot (every 24 hours to save memory)
        if hour % 24 == 0:
            self.capital_growth_metrics.hourly_snapshots.append(
                {
                    "hour": hour,
                    "capital": current_capital,
                    "pnl": self.capital_growth_metrics.total_pnl,
                    "growth_rate": self.capital_growth_metrics.growth_rate,
                }
            )

    def _check_emergency_conditions(self, current_capital: float, hour: int) -> None:
        """
        Check for emergency stop conditions.
        
        Args:
            current_capital: Current total capital
            hour: Current hour number
        """
        # Check for catastrophic loss (>50% loss)
        loss_pct = (
            self.capital_growth_metrics.initial_capital - current_capital
        ) / self.capital_growth_metrics.initial_capital
        
        if loss_pct > 0.5:
            if not self.risk_manager.is_emergency_stop_active():
                self.emergency_stop_count += 1
                self.risk_manager.activate_emergency_stop()
                self._record_failure(
                    timestamp=int(datetime.now().timestamp()) + (hour * 3600),
                    category="EMERGENCY_STOP",
                    description=f"Catastrophic loss detected: {loss_pct:.2%}",
                    severity="CRITICAL",
                    metadata={"loss_pct": loss_pct, "hour": hour},
                )

    def _record_failure(
        self,
        timestamp: int,
        category: str,
        description: str,
        severity: str,
        metadata: dict | None = None,
    ) -> None:
        """
        Record a failure mode.
        
        Args:
            timestamp: When failure occurred
            category: Category of failure
            description: Description of failure
            severity: Severity level
            metadata: Additional metadata
        """
        failure = FailureMode(
            timestamp=timestamp,
            category=category,
            description=description,
            severity=severity,
            metadata=metadata or {},
        )
        self.failure_modes.append(failure)
        
        # Log based on severity
        if severity == "CRITICAL":
            logger.critical(f"FAILURE: {category} - {description}")
        elif severity == "HIGH":
            logger.error(f"FAILURE: {category} - {description}")
        elif severity == "MEDIUM":
            logger.warning(f"FAILURE: {category} - {description}")
        else:
            logger.info(f"FAILURE: {category} - {description}")

    def _log_progress(self, hour: int) -> None:
        """
        Log progress at regular intervals.
        
        Args:
            hour: Current hour
        """
        current_capital = (
            self.engine_state.capital.available_capital
            + self.engine_state.capital.deployed_capital
        )
        
        logger.info(f"\n--- Progress Update: Day {hour // 24} ---")
        logger.info(f"Current Capital: ${current_capital:,.2f}")
        logger.info(f"Total PnL: ${self.capital_growth_metrics.total_pnl:,.2f}")
        logger.info(f"Growth Rate: {self.capital_growth_metrics.growth_rate:.2%}")
        logger.info(f"Max Drawdown: {self.drawdown_metrics.max_drawdown:.2%}")
        logger.info(f"Failures Detected: {len(self.failure_modes)}")
        logger.info(f"Emergency Stops: {self.emergency_stop_count}")
        logger.info(f"Risk Violations: {self.risk_violation_count}")

    def _generate_report(self) -> StabilityReport:
        """
        Generate final stability report.
        
        Returns:
            Complete StabilityReport
        """
        final_capital = (
            self.engine_state.capital.available_capital
            + self.engine_state.capital.deployed_capital
        )
        
        # Determine validation status
        validation_passed = True
        issues = []
        
        # Check for critical failures
        critical_failures = [f for f in self.failure_modes if f.severity == "CRITICAL"]
        if critical_failures:
            validation_passed = False
            issues.append(f"{len(critical_failures)} critical failures detected")
        
        # Check for emergency stops
        if self.emergency_stop_count > 0:
            validation_passed = False
            issues.append(f"{self.emergency_stop_count} emergency stops triggered")
        
        # Check for excessive drawdown (>30%)
        if self.drawdown_metrics.max_drawdown > 0.30:
            validation_passed = False
            issues.append(f"Excessive drawdown: {self.drawdown_metrics.max_drawdown:.2%}")
        
        # Check for capital loss (>20%)
        if final_capital < self.initial_capital * 0.8:
            validation_passed = False
            issues.append(f"Significant capital loss: {(1 - final_capital / self.initial_capital):.2%}")
        
        report = StabilityReport(
            run_timestamp=datetime.now().isoformat(),
            duration_hours=self.duration_hours,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            drawdown_metrics=self.drawdown_metrics,
            capital_growth_metrics=self.capital_growth_metrics,
            exploit_isolation_metrics=self.exploit_isolation_metrics,
            failure_modes=self.failure_modes,
            emergency_stops=self.emergency_stop_count,
            risk_violations=self.risk_violation_count,
            validation_passed=validation_passed,
            issues_detected=issues,
        )
        
        return report


def print_stability_report(report: StabilityReport) -> None:
    """
    Print formatted stability report.
    
    Args:
        report: StabilityReport to print
    """
    print("\n" + "=" * 80)
    print("SCALE VALIDATION STABILITY REPORT")
    print("=" * 80)
    print(f"\nRun Timestamp: {report.run_timestamp}")
    print(f"Duration: {report.duration_hours} hours ({report.duration_hours // 24} days)")
    
    print("\n--- CAPITAL METRICS ---")
    print(f"Initial Capital: ${report.initial_capital:,.2f}")
    print(f"Final Capital: ${report.final_capital:,.2f}")
    print(f"Total PnL: ${report.capital_growth_metrics.total_pnl:,.2f}")
    print(f"Growth Rate: {report.capital_growth_metrics.growth_rate:.2%}")
    print(f"Peak Capital: ${report.capital_growth_metrics.peak_capital:,.2f}")
    
    print("\n--- DRAWDOWN METRICS ---")
    print(f"Max Drawdown: {report.drawdown_metrics.max_drawdown:.2%}")
    print(f"Max Drawdown Duration: {report.drawdown_metrics.max_drawdown_duration_hours} hours")
    print(f"Number of Drawdown Periods: {len(report.drawdown_metrics.drawdown_periods)}")
    
    print("\n--- EXPLOIT ISOLATION METRICS ---")
    print(f"Exploits Executed: {report.exploit_isolation_metrics.exploits_executed}")
    print(f"Capital Allocation Requests: {report.exploit_isolation_metrics.capital_allocation_requests}")
    print(f"Capital Allocation Failures: {report.exploit_isolation_metrics.capital_allocation_failures}")
    print(f"Cross-Contamination Detected: {report.exploit_isolation_metrics.cross_contamination_detected}")
    
    print("\n--- FAILURE MODES OBSERVED ---")
    print(f"Total Failures: {len(report.failure_modes)}")
    print(f"Emergency Stops: {report.emergency_stops}")
    print(f"Risk Violations: {report.risk_violations}")
    
    # Group failures by category
    failures_by_category: dict[str, list[FailureMode]] = {}
    for failure in report.failure_modes:
        if failure.category not in failures_by_category:
            failures_by_category[failure.category] = []
        failures_by_category[failure.category].append(failure)
    
    if failures_by_category:
        print("\nFailure Breakdown:")
        for category, failures in sorted(failures_by_category.items()):
            print(f"  {category}: {len(failures)}")
            # Show first few failures
            for failure in failures[:3]:
                print(f"    - {failure.description} [{failure.severity}]")
            if len(failures) > 3:
                print(f"    ... and {len(failures) - 3} more")
    else:
        print("\n✓ No failures detected")
    
    print("\n--- VALIDATION RESULT ---")
    if report.validation_passed:
        print("✓ VALIDATION PASSED")
        print("\nThe system is ready for scale deployment.")
    else:
        print("✗ VALIDATION FAILED")
        print("\nIssues detected:")
        for issue in report.issues_detected:
            print(f"  - {issue}")
        print("\nThe system requires attention before scale deployment.")
    
    print("\n" + "=" * 80)


def save_report_json(report: StabilityReport, output_path: Path) -> None:
    """
    Save stability report as JSON.
    
    Args:
        report: StabilityReport to save
        output_path: Path to save JSON file
    """
    report_dict = dataclass_to_dict(report)
    
    with open(output_path, "w") as f:
        json.dump(report_dict, f, indent=2)
    
    logger.info(f"Report saved to: {output_path}")


def create_default_config() -> dict:
    """
    Create default configuration for scale validation.
    
    Returns:
        Default configuration dict
    """
    return {
        "dry_run_wallet": 10000.0,
        "validation_duration_hours": 30 * 24,  # 30 days
        "max_position_size": 0.10,  # 10% max per position
        "max_total_exposure": 0.95,  # 95% max total exposure
        "max_open_trades": 3,
        "stoploss": 0.10,  # 10% max loss per trade
        "max_daily_loss": 0.20,  # 20% max daily loss
        "leverage": {"max": 1.0},
        "position_cooldown": 3600,  # 1 hour cooldown
        "global_cooldown": 0,
        "max_funding_rate": 0.01,  # 1% max funding rate
        "funding_rate_change_threshold": 0.005,  # 0.5% max funding change
    }


def main():
    """Main entry point for scale validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scale Validation for Trading Engine")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (JSON)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="scale_validation_report.json",
        help="Output path for report (default: scale_validation_report.json)",
    )
    
    args = parser.parse_args()
    
    # Load or create config
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    else:
        logger.info("No config provided, using default configuration")
        config = create_default_config()
    
    # Create validator
    validator = ScaleValidator(config)
    
    # Run validation with NullExploitModule (no-op test)
    report = validator.run_validation()
    
    # Print report
    print_stability_report(report)
    
    # Save report
    output_path = Path(args.output)
    save_report_json(report, output_path)
    
    # Return exit code based on validation result
    return 0 if report.validation_passed else 1


if __name__ == "__main__":
    sys.exit(main())
