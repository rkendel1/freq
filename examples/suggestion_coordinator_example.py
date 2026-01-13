"""
Example demonstrating the suggestion coordination system.

This shows how exploit modules can optimize routing through suggestions
while maintaining complete independence.

Run with: python examples/suggestion_coordinator_example.py
"""

from freqtrade.exploits.exploit_module import (
    Action,
    ActionType,
    ExecutionResult,
    ExecutionState,
    ExploitModule,
    Suggestion,
)
from freqtrade.exploits.router import RouterConfig, SuggestionCoordinator


# Example modules that make different suggestions
class HighConfidenceModule(ExploitModule):
    """Module with high confidence - suggests boosting related actions."""
    
    def evaluate(self, state: ExecutionState) -> list[Action]:
        return [
            Action(
                type=ActionType.OPEN_LONG,
                symbol=state.symbol,
                size=0.1,
                reason="high_confidence_signal",
                metadata={"confidence": 0.9},
            )
        ]
    
    def suggest_next(self, state: ExecutionState, my_actions: list[Action]) -> list[Suggestion]:
        # High confidence - suggest boosting flow strategy
        return [
            Suggestion(
                kind="boost_conviction",
                target="flow_strategy",
                payload={"multiplier": 1.3, "reason": "High confidence setup detected"},
                confidence=0.9,
            )
        ]
    
    def on_execution_result(self, action: Action, result: ExecutionResult) -> None:
        pass


class RiskAwareModule(ExploitModule):
    """Module that detects risk - suggests reducing exposure."""
    
    def evaluate(self, state: ExecutionState) -> list[Action]:
        return [
            Action(
                type=ActionType.OPEN_SHORT,
                symbol=state.symbol,
                size=0.05,  # Small position due to risk awareness
                reason="high_risk_detected",
                metadata={"risk_level": "high"},
            )
        ]
    
    def suggest_next(self, state: ExecutionState, my_actions: list[Action]) -> list[Suggestion]:
        # High risk detected - suggest reducing other modules' size
        return [
            Suggestion(
                kind="reduce_size_if",
                target="flow_strategy",
                payload={"reduction": 0.3, "reason": "High risk environment"},
                confidence=0.85,
            ),
            Suggestion(
                kind="reduce_size_if",
                target="funding_strategy",
                payload={"reduction": 0.3, "reason": "High risk environment"},
                confidence=0.85,
            ),
        ]
    
    def on_execution_result(self, action: Action, result: ExecutionResult) -> None:
        pass


class FlowStrategyModule(ExploitModule):
    """Flow strategy that benefits from coordination."""
    
    def evaluate(self, state: ExecutionState) -> list[Action]:
        return [
            Action(
                type=ActionType.OPEN_LONG,
                symbol=state.symbol,
                size=0.15,
                reason="flow_pressure_detected",
            )
        ]
    
    def suggest_next(self, state: ExecutionState, my_actions: list[Action]) -> list[Suggestion]:
        # Flow detected - suggest pairing with funding
        return [
            Suggestion(
                kind="pair_with_action",
                target="funding_strategy",
                payload={"reason": "Flow and funding often correlate"},
                confidence=0.75,
            )
        ]
    
    def on_execution_result(self, action: Action, result: ExecutionResult) -> None:
        pass


class FundingStrategyModule(ExploitModule):
    """Funding strategy that can be paired."""
    
    def evaluate(self, state: ExecutionState) -> list[Action]:
        return [
            Action(
                type=ActionType.OPEN_SHORT,
                symbol=state.symbol,
                size=0.08,
                reason="funding_rate_favorable",
            )
        ]
    
    def on_execution_result(self, action: Action, result: ExecutionResult) -> None:
        pass


def main():
    """Demonstrate the suggestion coordination system."""
    
    print("=" * 80)
    print("Suggestion Coordination System Example")
    print("=" * 80)
    print()
    
    # Create test execution state
    state = ExecutionState(
        symbol="BTC/USDT",
        available_capital=10000.0,
        deployed_capital=0.0,
        open_positions=[],
        recent_trades=[],
        current_price=50000.0,
        timestamp=1000,
    )
    
    # Initialize modules
    high_conf = HighConfidenceModule()
    risk_aware = RiskAwareModule()
    flow_strategy = FlowStrategyModule()
    funding_strategy = FundingStrategyModule()
    
    modules = [
        ("high_confidence", high_conf),
        ("risk_aware", risk_aware),
        ("flow_strategy", flow_strategy),
        ("funding_strategy", funding_strategy),
    ]
    
    print("Scenario 1: Suggestions DISABLED")
    print("-" * 80)
    
    # Scenario 1: Without suggestions
    config_disabled = RouterConfig(enable_suggestions=False)
    coordinator_disabled = SuggestionCoordinator(config_disabled)
    
    actions_before = {
        name: module.evaluate(state)
        for name, module in modules
    }
    
    print("\nOriginal actions (no coordination):")
    for name, actions in actions_before.items():
        for action in actions:
            print(f"  {name}: {action.type.value} size={action.size:.3f}")
    
    actions_no_coord = coordinator_disabled.collect_and_apply_suggestions(
        modules, actions_before, state, 1000
    )
    
    print("\nAfter coordinator (disabled):")
    for name, actions in actions_no_coord.items():
        for action in actions:
            print(f"  {name}: {action.type.value} size={action.size:.3f}")
    
    print(f"\nApplied suggestions: {len(coordinator_disabled.applied_suggestions)}")
    
    print("\n" + "=" * 80)
    print("Scenario 2: Suggestions ENABLED")
    print("-" * 80)
    
    # Scenario 2: With suggestions
    config_enabled = RouterConfig(
        enable_suggestions=True,
        max_conviction_multiplier=1.5,
        max_size_reduction=0.5,
        log_suggestions=False,
    )
    coordinator_enabled = SuggestionCoordinator(config_enabled)
    
    # Reset actions
    actions_before = {
        name: module.evaluate(state)
        for name, module in modules
    }
    
    print("\nOriginal actions (before optimization):")
    for name, actions in actions_before.items():
        for action in actions:
            print(f"  {name}: {action.type.value} size={action.size:.3f}")
    
    actions_optimized = coordinator_enabled.collect_and_apply_suggestions(
        modules, actions_before, state, 1000
    )
    
    print("\nOptimized actions (after coordination):")
    for name, actions in actions_optimized.items():
        for action in actions:
            paired = ""
            if action.metadata and "paired_with" in action.metadata:
                paired = f" [paired with {action.metadata['paired_with']}]"
            print(f"  {name}: {action.type.value} size={action.size:.3f}{paired}")
    
    print(f"\nApplied suggestions: {len(coordinator_enabled.applied_suggestions)}")
    
    print("\nSuggestion details:")
    for s in coordinator_enabled.applied_suggestions:
        print(f"  {s.source_module} → {s.target_action}")
        print(f"    Kind: {s.suggestion_kind}")
        print(f"    Impact: {s.impact}")
        print(f"    Confidence: {s.confidence:.2f}")
    
    stats = coordinator_enabled.get_suggestion_stats()
    print("\nSuggestion statistics:")
    print(f"  Total applied: {stats['total_applied']}")
    print(f"  By kind: {stats['by_kind']}")
    print(f"  By source: {stats['by_source']}")
    
    print("\n" + "=" * 80)
    print("Key observations:")
    print("-" * 80)
    print("1. flow_strategy size was BOOSTED by high_confidence (high conviction)")
    print("2. flow_strategy size was REDUCED by risk_aware (high risk)")
    print("3. funding_strategy size was REDUCED by risk_aware (high risk)")
    print("4. funding_strategy was PAIRED with flow_strategy (correlation)")
    print()
    print("The net effect optimizes routing through modules:")
    print("  - Flow gets boost from confidence, but moderated by risk")
    print("  - Funding is reduced for safety and paired for coordination")
    print("  - All modules remain completely independent!")
    print("=" * 80)


if __name__ == "__main__":
    main()
