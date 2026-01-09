"""
Example usage of the PnL Attribution module.

This demonstrates how to use the attribution module to analyze trade performance.
"""

from datetime import datetime, timezone, timedelta
from freqtrade.persistence import LocalTrade
from freqtrade.metrics.attribution import attribute_trade


def example_closed_trade_attribution():
    """
    Example: Attributing a closed profitable trade.
    """
    print("=" * 60)
    print("Example 1: Closed Profitable Trade")
    print("=" * 60)
    
    # Create a sample closed trade
    trade = LocalTrade(
        id=1,
        pair="BTC/USDT",
        is_short=False,
        open_rate=50000.0,
        amount=0.1,
        stake_amount=5000.0,
        open_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        close_rate=55000.0,
        close_date=datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
        fee_open=0.001,
        fee_close=0.001,
        fee_open_cost=5.0,
        fee_close_cost=5.5,
        funding_fees=2.0,
        close_profit_abs=489.5,
        close_profit=0.0979,
        is_open=False,
        exit_reason="roi",
        strategy="MomentumExploit",
        enter_tag="strong_momentum",
    )
    
    # Attribute the trade
    attribution = attribute_trade(trade, capital_source="initial")
    
    # Display the attribution
    print(f"\nTrade #{attribution.trade_id}")
    print(f"  Exploit: {attribution.exploit_id}")
    print(f"  Capital Source: {attribution.capital_source}")
    print(f"  Pair: {attribution.pair}")
    print(f"  Position: {'SHORT' if attribution.is_short else 'LONG'}")
    print(f"\nEntry:")
    print(f"  Price: ${attribution.entry_price:,.2f}")
    print(f"  Amount: {attribution.entry_amount}")
    print(f"  Stake: ${attribution.entry_stake:,.2f}")
    print(f"  Date: {attribution.entry_date}")
    print(f"\nExit:")
    print(f"  Price: ${attribution.exit_price:,.2f}")
    print(f"  Date: {attribution.exit_date}")
    print(f"  Reason: {attribution.exit_reason}")
    print(f"\nCosts:")
    print(f"  Entry Fee: {attribution.fee_open * 100:.3f}% (${attribution.fee_open_cost:.2f})")
    print(f"  Exit Fee: {attribution.fee_close * 100:.3f}% (${attribution.fee_close_cost:.2f})")
    print(f"  Total Fees: ${attribution.total_fees:.2f}")
    print(f"  Funding Fees: ${attribution.funding_fees:.2f}")
    print(f"\nPerformance:")
    print(f"  Holding Duration: {attribution.holding_duration_hours:.2f} hours")
    print(f"  Realized Profit: ${attribution.realized_profit:.2f}")
    print(f"  Profit Ratio: {attribution.profit_ratio * 100:.2f}%")
    print()


def example_open_trade_attribution():
    """
    Example: Attributing an open trade (futures short position).
    """
    print("=" * 60)
    print("Example 2: Open Short Position (Futures)")
    print("=" * 60)
    
    # Create a sample open short trade
    trade = LocalTrade(
        id=2,
        pair="ETH/USDT",
        is_short=True,
        open_rate=3000.0,
        amount=1.0,
        stake_amount=3000.0,
        open_date=datetime(2024, 1, 5, 10, 0, 0, tzinfo=timezone.utc),
        close_rate=None,
        close_date=None,
        fee_open=0.0004,
        fee_close=None,
        fee_open_cost=1.2,
        fee_close_cost=None,
        funding_fees=-3.5,  # Negative = paid
        close_profit_abs=None,
        close_profit=None,
        is_open=True,
        exit_reason=None,
        strategy="FundingRateArbitrage",
        enter_tag="negative_funding",
    )
    
    # Attribute the trade
    attribution = attribute_trade(trade, capital_source="borrowed")
    
    # Display the attribution
    print(f"\nTrade #{attribution.trade_id} (OPEN)")
    print(f"  Exploit: {attribution.exploit_id}")
    print(f"  Capital Source: {attribution.capital_source}")
    print(f"  Pair: {attribution.pair}")
    print(f"  Position: {'SHORT' if attribution.is_short else 'LONG'}")
    print(f"\nEntry:")
    print(f"  Price: ${attribution.entry_price:,.2f}")
    print(f"  Amount: {attribution.entry_amount}")
    print(f"  Stake: ${attribution.entry_stake:,.2f}")
    print(f"  Date: {attribution.entry_date}")
    print(f"\nCosts (so far):")
    print(f"  Entry Fee: {attribution.fee_open * 100:.4f}% (${attribution.fee_open_cost:.2f})")
    print(f"  Funding Fees Paid: ${abs(attribution.funding_fees):.2f}")
    print(f"  Total Costs: ${attribution.total_fees + abs(attribution.funding_fees):.2f}")
    print(f"\nStatus:")
    print(f"  Currently Open: {attribution.is_open}")
    print(f"  Holding Duration: {attribution.holding_duration_hours:.2f} hours")
    print(f"  (Profit/loss will be calculated on exit)")
    print()


def example_batch_attribution():
    """
    Example: Batch attributing multiple trades for analysis.
    """
    print("=" * 60)
    print("Example 3: Batch Attribution")
    print("=" * 60)
    
    # Create sample trades from different exploits
    base_date = datetime(2024, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
    
    trades = [
        LocalTrade(
            id=101,
            pair="BTC/USDT",
            open_rate=50000.0,
            amount=0.05,
            stake_amount=2500.0,
            open_date=base_date - timedelta(hours=48),
            close_rate=51000.0,
            close_date=base_date - timedelta(hours=24),
            fee_open=0.001,
            fee_close=0.001,
            fee_open_cost=2.5,
            fee_close_cost=2.55,
            close_profit_abs=44.95,
            close_profit=0.01798,
            is_open=False,
            strategy="ScalpingExploit",
        ),
        LocalTrade(
            id=102,
            pair="ETH/USDT",
            open_rate=2800.0,
            amount=0.5,
            stake_amount=1400.0,
            open_date=base_date - timedelta(hours=72),
            close_rate=2950.0,
            close_date=base_date - timedelta(hours=12),
            fee_open=0.001,
            fee_close=0.001,
            fee_open_cost=1.4,
            fee_close_cost=1.475,
            close_profit_abs=71.125,
            close_profit=0.0508,
            is_open=False,
            strategy="TrendFollowing",
        ),
        LocalTrade(
            id=103,
            pair="ADA/USDT",
            open_rate=0.50,
            amount=2000.0,
            stake_amount=1000.0,
            open_date=base_date - timedelta(hours=120),
            close_rate=0.48,
            close_date=base_date - timedelta(hours=6),
            fee_open=0.001,
            fee_close=0.001,
            fee_open_cost=1.0,
            fee_close_cost=0.96,
            close_profit_abs=-41.96,
            close_profit=-0.04196,
            is_open=False,
            strategy="MeanReversion",
        ),
    ]
    
    # Attribute all trades
    attributions = [attribute_trade(trade, capital_source="reinvested") for trade in trades]
    
    print("\nSummary of Attributed Trades:")
    print(f"{'ID':<6} {'Exploit':<20} {'Pair':<12} {'Duration (h)':<14} {'Fees':<10} {'Profit':<10}")
    print("-" * 80)
    
    for attr in attributions:
        print(
            f"{attr.trade_id:<6} "
            f"{attr.exploit_id:<20} "
            f"{attr.pair:<12} "
            f"{attr.holding_duration_hours:<14.2f} "
            f"${attr.total_fees:<9.2f} "
            f"${attr.realized_profit:<9.2f}"
        )
    
    # Calculate totals
    total_fees = sum(a.total_fees for a in attributions)
    total_profit = sum(a.realized_profit for a in attributions if a.realized_profit)
    
    print("-" * 80)
    print(f"{'TOTAL':<54} ${total_fees:<9.2f} ${total_profit:<9.2f}")
    print()


def example_attribution_to_dict():
    """
    Example: Converting attribution to dictionary for storage/export.
    """
    print("=" * 60)
    print("Example 4: Export Attribution as Dictionary")
    print("=" * 60)
    
    trade = LocalTrade(
        id=200,
        pair="SOL/USDT",
        open_rate=100.0,
        amount=10.0,
        stake_amount=1000.0,
        open_date=datetime(2024, 1, 10, 0, 0, 0, tzinfo=timezone.utc),
        close_rate=105.0,
        close_date=datetime(2024, 1, 10, 6, 0, 0, tzinfo=timezone.utc),
        fee_open=0.001,
        fee_close=0.001,
        fee_open_cost=1.0,
        fee_close_cost=1.05,
        close_profit_abs=47.95,
        close_profit=0.04795,
        is_open=False,
        strategy="BreakoutExploit",
        enter_tag="support_breakout",
    )
    
    attribution = attribute_trade(trade)
    attr_dict = attribution.to_dict()
    
    print("\nAttribution as dictionary (for export/storage):")
    import json
    print(json.dumps(attr_dict, indent=2, default=str))
    print()


if __name__ == "__main__":
    """
    Run all examples to demonstrate PnL attribution.
    """
    example_closed_trade_attribution()
    example_open_trade_attribution()
    example_batch_attribution()
    example_attribution_to_dict()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print("\nNext Steps:")
    print("  - Integrate attribution into your trading loop")
    print("  - Store attribution records for later analysis")
    print("  - Build aggregation/analytics on top of this raw data")
    print()
