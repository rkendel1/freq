"""
Example: Capital Routing Engine

This example demonstrates the capital routing layer in action.
It shows how realized PnL is allocated to different capital pools
with caps and cooldowns enforced.
"""

from freqtrade.exploits.router import CapitalRouter, RouterConfig


def main():
    """Run capital routing example."""
    
    print("=" * 80)
    print("Capital Routing Engine - Example Trace")
    print("=" * 80)
    print()
    
    # Configure router with:
    # - 60% of PnL to base capital
    # - 25% to flow buffer
    # - 15% to convexity buffer
    # - Caps on base and flow buffer
    # - 60 second cooldown between routings
    config = RouterConfig(
        base_capital_allocation=0.60,
        flow_buffer_allocation=0.25,
        convexity_buffer_allocation=0.15,
        base_capital_cap=15000.0,
        flow_buffer_cap=500.0,
        convexity_buffer_cap=None,  # No cap
        routing_cooldown=60,
    )
    
    # Initialize router with $10,000 initial capital
    router = CapitalRouter(config, initial_capital=10000.0)
    
    print("Initial Configuration:")
    print(f"  Starting Capital: $10,000.00")
    print(f"  Allocation Ratios: Base={config.base_capital_allocation:.0%}, "
          f"Flow={config.flow_buffer_allocation:.0%}, "
          f"Convexity={config.convexity_buffer_allocation:.0%}")
    print(f"  Caps: Base=${config.base_capital_cap:,.2f}, "
          f"Flow=${config.flow_buffer_cap:,.2f}, "
          f"Convexity=None")
    print(f"  Routing Cooldown: {config.routing_cooldown}s")
    print()
    
    # Simulate a series of trades with realized PnL
    trades = [
        (1000, 1000.0, "Successful long trade on BTC/USDT"),
        (1100, 1500.0, "Profitable short trade on ETH/USDT"),
        (1200, -300.0, "Stop loss triggered on SOL/USDT"),
        (1300, 800.0, "Funding arbitrage profit"),
        (1500, 2000.0, "Large winning trade on BTC/USDT"),
        (1600, 1200.0, "Volatility arbitrage profit"),
    ]
    
    print("=" * 80)
    print("Executing Trades and Routing PnL")
    print("=" * 80)
    print()
    
    for i, (timestamp, pnl, description) in enumerate(trades, 1):
        print(f"Trade {i}: {description}")
        print(f"  Timestamp: {timestamp}s")
        print(f"  Realized PnL: ${pnl:+,.2f}")
        
        # Check if routing is allowed
        allowed, reason = router.can_route(timestamp)
        if not allowed:
            print(f"  Status: SKIPPED - {reason}")
            print()
            continue
        
        # Route the PnL
        decision = router.route_pnl(pnl, current_timestamp=timestamp)
        
        print(f"  Allocations:")
        print(f"    Base Capital:     ${decision.to_base_capital:>10,.2f}")
        print(f"    Flow Buffer:      ${decision.to_flow_buffer:>10,.2f}")
        print(f"    Convexity Buffer: ${decision.to_convexity_buffer:>10,.2f}")
        if decision.overflow > 0:
            print(f"    Overflow:         ${decision.overflow:>10,.2f} (hit caps)")
        
        print(f"  Pool Balances After:")
        print(f"    Base Capital:     ${decision.base_capital_after:>10,.2f}")
        print(f"    Flow Buffer:      ${decision.flow_buffer_after:>10,.2f}")
        print(f"    Convexity Buffer: ${decision.convexity_buffer_after:>10,.2f}")
        print(f"    Total:            ${decision.base_capital_after + decision.flow_buffer_after + decision.convexity_buffer_after:>10,.2f}")
        print()
    
    # Generate and display the complete flow trace
    print()
    print(router.generate_flow_trace())
    
    # Summary statistics
    print()
    print("=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    
    total_routed = sum(d.realized_pnl for d in router.routing_history)
    total_overflow = sum(d.overflow for d in router.routing_history)
    
    pools = router.get_pools()
    print(f"Total PnL Routed:     ${total_routed:>12,.2f}")
    print(f"Total Overflow:       ${total_overflow:>12,.2f}")
    print(f"Final Pool Total:     ${pools.total():>12,.2f}")
    print(f"Total Routings:       {len(router.routing_history):>12}")
    print()
    
    print("Pool Utilization:")
    if config.base_capital_cap:
        utilization = (pools.base_capital / config.base_capital_cap) * 100
        print(f"  Base Capital:      {utilization:>6.1f}% of cap")
    else:
        print(f"  Base Capital:      No cap")
    
    if config.flow_buffer_cap:
        utilization = (pools.flow_buffer / config.flow_buffer_cap) * 100
        print(f"  Flow Buffer:       {utilization:>6.1f}% of cap")
    else:
        print(f"  Flow Buffer:       No cap")
    
    print(f"  Convexity Buffer:  No cap")
    print()
    
    print("=" * 80)


if __name__ == "__main__":
    main()
