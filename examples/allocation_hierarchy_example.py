"""
Example: Dynamic Allocation and Activation Hierarchy

This example demonstrates how to use the regime detector, allocation hierarchy,
and module activation coordinator together to implement dynamic capital allocation
based on market conditions.

The system implements the allocation hierarchy from the issue:
- Neutral/low-vol: 60-80% funding strategies (skew_arb + capture)
- Funding spike: shift 30-50% to funding_decay
- Flow aligned: add 1.5-3x leverage multiplier
- Vol expansion: divert 10-20% to convexity_seeding
- High regret: flatten everything
"""

import pandas as pd
import numpy as np

from freqtrade.exploits.regime_detector import (
    RegimeDetector,
    RegimeDetectorConfig,
    MarketRegime,
)
from freqtrade.exploits.allocation_hierarchy import (
    AllocationHierarchy,
    AllocationHierarchyConfig,
)
from freqtrade.exploits.module_activation_coordinator import (
    ModuleActivationCoordinator,
    ModuleActivationCoordinatorConfig,
)


def create_sample_market_data(scenario: str) -> pd.DataFrame:
    """
    Create sample market data for different scenarios.
    
    Args:
        scenario: One of 'neutral', 'high_vol', 'low_vol'
        
    Returns:
        DataFrame with OHLCV data
    """
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
    
    if scenario == 'neutral':
        # Normal volatility
        df = pd.DataFrame({
            'date': dates,
            'open': 100.0 + np.random.randn(100) * 1.0,
            'high': 101.0 + np.random.randn(100) * 1.0,
            'low': 99.0 + np.random.randn(100) * 1.0,
            'close': 100.0 + np.random.randn(100) * 1.0,
            'volume': 1000.0 + np.random.randn(100) * 100,
        })
    elif scenario == 'high_vol':
        # High volatility
        df = pd.DataFrame({
            'date': dates,
            'open': 100.0 + np.random.randn(100) * 5.0,
            'high': 105.0 + np.random.randn(100) * 5.0,
            'low': 95.0 + np.random.randn(100) * 5.0,
            'close': 100.0 + np.random.randn(100) * 5.0,
            'volume': 1000.0 + np.random.randn(100) * 200,
        })
    else:  # low_vol
        # Low volatility
        df = pd.DataFrame({
            'date': dates,
            'open': 100.0 + np.random.randn(100) * 0.1,
            'high': 100.1 + np.random.randn(100) * 0.1,
            'low': 99.9 + np.random.randn(100) * 0.1,
            'close': 100.0 + np.random.randn(100) * 0.1,
            'volume': 1000.0 + np.random.randn(100) * 50,
        })
    
    # Ensure high >= low
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


def demonstrate_scenario(
    scenario_name: str,
    dataframe: pd.DataFrame,
    funding_rate: float = 0.01,
    flow_pressure: float = 0.0,
    current_capital: float = 10000.0,
):
    """
    Demonstrate the allocation system for a specific scenario.
    
    Args:
        scenario_name: Name of the scenario
        dataframe: Market data
        funding_rate: Current funding rate
        flow_pressure: Current flow pressure
        current_capital: Current total capital
    """
    print(f"\n{'=' * 80}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'=' * 80}")
    
    # Step 1: Detect market regime
    print("\n1. Detecting Market Regime...")
    
    regime_config = RegimeDetectorConfig()
    detector = RegimeDetector(regime_config)
    
    regime_metrics = detector.detect_regime(
        dataframe=dataframe,
        current_funding_rate=funding_rate,
        flow_pressure=flow_pressure,
        current_capital=current_capital,
    )
    
    print(f"   Regime: {regime_metrics.regime.value}")
    print(f"   Confidence: {regime_metrics.confidence:.1%}")
    if regime_metrics.current_atr_pct:
        print(f"   ATR%: {regime_metrics.current_atr_pct:.2%}")
    if regime_metrics.current_funding_rate:
        print(f"   Funding Rate: {regime_metrics.current_funding_rate:.2%}")
    if regime_metrics.flow_pressure:
        print(f"   Flow Pressure: {regime_metrics.flow_pressure:.4f}")
    
    # Step 2: Calculate capital allocation
    print("\n2. Calculating Capital Allocation...")
    
    alloc_config = AllocationHierarchyConfig()
    hierarchy = AllocationHierarchy(alloc_config)
    
    allocations = hierarchy.calculate_allocations(
        regime_metrics=regime_metrics,
        available_capital=current_capital,
    )
    
    print("\n" + hierarchy.get_allocation_summary(allocations))
    
    # Step 3: Determine active modules
    print("\n3. Determining Active Modules...")
    
    coord_config = ModuleActivationCoordinatorConfig()
    coordinator = ModuleActivationCoordinator(coord_config, hierarchy)
    
    active_status = coordinator.determine_active_modules(
        regime_metrics=regime_metrics,
        current_drawdown=0.0,  # No drawdown in this example
    )
    
    print("\n" + coordinator.get_activation_summary(regime_metrics, active_status))
    
    # Step 4: Summary
    print("\n4. Execution Summary:")
    print(f"   Regime: {regime_metrics.regime.value}")
    print(f"   Active Modules: {', '.join(k for k, v in active_status.items() if v)}")
    
    total_effective = sum(a.effective_allocation for a in allocations.values())
    print(f"   Total Effective Allocation: {total_effective:.1%}")


def main():
    """Run all demonstration scenarios."""
    print("\n" + "=" * 80)
    print("DYNAMIC ALLOCATION AND ACTIVATION HIERARCHY DEMONSTRATION")
    print("=" * 80)
    
    # Scenario 1: Neutral/Low-Vol Regime
    demonstrate_scenario(
        scenario_name="Neutral/Low-Vol Regime (Base Allocation)",
        dataframe=create_sample_market_data('low_vol'),
        funding_rate=0.01,  # Normal funding
        flow_pressure=0.0,
        current_capital=10000.0,
    )
    
    # Scenario 2: Funding Spike Regime
    demonstrate_scenario(
        scenario_name="Funding Spike Regime (Shift to Funding Decay)",
        dataframe=create_sample_market_data('neutral'),
        funding_rate=0.20,  # 20% funding spike
        flow_pressure=0.0,
        current_capital=10000.0,
    )
    
    # Scenario 3: Flow Aligned Regime
    demonstrate_scenario(
        scenario_name="Flow Aligned Regime (Add Leverage Multiplier)",
        dataframe=create_sample_market_data('neutral'),
        funding_rate=0.01,
        flow_pressure=0.008,  # Strong positive flow aligned with funding
        current_capital=10000.0,
    )
    
    # Scenario 4: Volatility Expansion Regime
    demonstrate_scenario(
        scenario_name="Volatility Expansion Regime (Activate Convexity)",
        dataframe=create_sample_market_data('high_vol'),
        funding_rate=0.01,
        flow_pressure=0.0,
        current_capital=10000.0,
    )
    
    # Scenario 5: High Regret Regime
    print("\n" + "=" * 80)
    print("SCENARIO: High Regret Regime (Flatten Everything)")
    print("=" * 80)
    
    print("\nSimulating high regret condition...")
    
    detector = RegimeDetector(RegimeDetectorConfig())
    
    # Simulate consecutive losses
    for _ in range(5):
        detector.record_trade_result(profitable=False)
    
    # Set high peak capital to create drawdown
    detector.peak_capital = 10000.0
    
    regime_metrics = detector.detect_regime(
        dataframe=create_sample_market_data('neutral'),
        current_capital=8000.0,  # 20% drawdown
    )
    
    print(f"   Regime: {regime_metrics.regime.value}")
    print(f"   Drawdown: {regime_metrics.current_drawdown:.1%}")
    print(f"   Consecutive Losses: {regime_metrics.consecutive_losses}")
    
    coord_config = ModuleActivationCoordinatorConfig()
    alloc_hierarchy = AllocationHierarchy(AllocationHierarchyConfig())
    coordinator = ModuleActivationCoordinator(coord_config, alloc_hierarchy)
    
    active_status = coordinator.determine_active_modules(regime_metrics)
    
    print(f"\n   Active Modules: {', '.join(k for k, v in active_status.items() if v) or 'NONE'}")
    print("   → All modules deactivated due to high regret")
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    
    print("\nKey Takeaways:")
    print("1. Regime detector identifies market conditions automatically")
    print("2. Allocation hierarchy adjusts capital distribution per regime")
    print("3. Module activator controls which strategies run")
    print("4. System protects capital during high regret conditions")
    print("5. All components work together seamlessly")


if __name__ == "__main__":
    main()
