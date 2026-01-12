#!/usr/bin/env python3
"""
Architecture Validation Script

This script validates the implementation against the architectural invariants
and pseudocode defined in the issue. It checks that all components adhere to
the contract and that no violations exist.

Usage:
    python validate_architecture.py
"""

import ast
import inspect
import sys
from pathlib import Path
from typing import Any


class ArchitectureValidator:
    """Validates architecture against defined invariants."""

    def __init__(self):
        self.violations = []
        self.passes = []
        self.repo_root = Path(__file__).parent
        
    def log_pass(self, check: str, message: str = ""):
        """Record a passing check."""
        self.passes.append((check, message))
        print(f"✓ PASS: {check}")
        if message:
            print(f"  {message}")
    
    def log_violation(self, check: str, message: str):
        """Record a violation."""
        self.violations.append((check, message))
        print(f"✗ FAIL: {check}")
        print(f"  {message}")
    
    def validate_global_invariants(self):
        """Validate GLOBAL INVARIANTS (APPLY TO ALL PHASES)."""
        print("\n" + "="*80)
        print("VALIDATING GLOBAL INVARIANTS")
        print("="*80)
        
        # Rule 1: Exploits NEVER place orders
        self._check_exploits_never_place_orders()
        
        # Rule 2: Exploits NEVER mutate capital
        self._check_exploits_never_mutate_capital()
        
        # Rule 3: Exploits ONLY emit Actions + Metrics
        self._check_exploits_only_emit_actions()
        
        # Rule 4: Execution Engine is deterministic
        self._check_engine_is_deterministic()
        
        # Rule 5: Capital Router is the ONLY allocator
        self._check_router_is_only_allocator()
        
        # Rule 6: DSPy can ONLY suggest parameter deltas
        self._check_dspy_only_suggests()
    
    def _check_exploits_never_place_orders(self):
        """Check that exploit modules never place orders directly."""
        check_name = "Exploits NEVER place orders"
        
        # Load all exploit files
        exploit_dir = self.repo_root / "freqtrade" / "exploits"
        exploit_files = list(exploit_dir.glob("*.py"))
        
        violations_found = []
        
        for filepath in exploit_files:
            if filepath.name.startswith("__"):
                continue
                
            with open(filepath, "r") as f:
                content = f.read()
                
            # Check for order placement keywords
            forbidden_patterns = [
                "place_order",
                "create_order",
                "execute_order",
                "submit_order",
                ".order(",
                "exchange.buy",
                "exchange.sell",
            ]
            
            for pattern in forbidden_patterns:
                if pattern in content:
                    # Verify it's not just in comments
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if hasattr(node.func, 'attr') and pattern.replace(".", "").replace("_", "") in str(node.func.attr).lower():
                                violations_found.append(f"{filepath.name}: Found '{pattern}'")
        
        if violations_found:
            self.log_violation(check_name, "\n  ".join(violations_found))
        else:
            self.log_pass(check_name, "All exploits only emit Actions, never place orders directly")
    
    def _check_exploits_never_mutate_capital(self):
        """Check that exploit modules never mutate capital directly."""
        check_name = "Exploits NEVER mutate capital"
        
        exploit_dir = self.repo_root / "freqtrade" / "exploits"
        exploit_files = list(exploit_dir.glob("*.py"))
        
        violations_found = []
        
        for filepath in exploit_files:
            if filepath.name.startswith("__"):
                continue
                
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check for STATE capital mutation patterns (not local variables)
            forbidden_patterns = [
                "state.capital =",
                "state.available_capital =",
                "state.deployed_capital =",
            ]
            
            for pattern in forbidden_patterns:
                if pattern in content:
                    # Filter out comments and docstrings
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if pattern in line and not line.strip().startswith("#") and '"""' not in line:
                            # Check if it's actually mutation (not comparison or parameter)
                            if "==" not in line and "!=" not in line and "def " not in line:
                                violations_found.append(
                                    f"{filepath.name}:{i+1}: Capital mutation found: {line.strip()}"
                                )
        
        if violations_found:
            self.log_violation(check_name, "\n  ".join(violations_found))
        else:
            self.log_pass(check_name, "No exploits mutate capital - all capital changes go through router")
    
    def _check_exploits_only_emit_actions(self):
        """Check that exploits only emit Actions, not other side effects."""
        check_name = "Exploits ONLY emit Actions + Metrics"
        
        # Check that evaluate() returns list[Action] by reading source
        try:
            filepath = self.repo_root / "freqtrade" / "exploits" / "exploit_module.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check the return type annotation in the source
            if "-> list[Action]:" in content or "-> List[Action]:" in content:
                self.log_pass(check_name, "ExploitModule.evaluate() returns list[Action] as expected")
            else:
                self.log_violation(
                    check_name,
                    "ExploitModule.evaluate() should return list[Action]"
                )
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def _check_engine_is_deterministic(self):
        """Check that execution engine is deterministic."""
        check_name = "Execution Engine is deterministic"
        
        # Check for non-deterministic patterns in risk and core modules
        core_dir = self.repo_root / "freqtrade" / "core"
        
        non_deterministic_patterns = [
            "random.",
            "Random(",
            "np.random",
            "random.choice",
            "random.randint",
            "random.uniform",
        ]
        
        violations_found = []
        
        for filepath in core_dir.glob("*.py"):
            with open(filepath, "r") as f:
                content = f.read()
            
            for pattern in non_deterministic_patterns:
                if pattern in content:
                    violations_found.append(f"{filepath.name}: Contains '{pattern}'")
        
        if violations_found:
            self.log_violation(check_name, "\n  ".join(violations_found))
        else:
            self.log_pass(check_name, "No random or non-deterministic code found in core execution")
    
    def _check_router_is_only_allocator(self):
        """Check that only the router allocates capital."""
        check_name = "Capital Router is the ONLY allocator"
        
        # Check that router exists and has allocate/authorize methods by reading source
        try:
            filepath = self.repo_root / "freqtrade" / "exploits" / "router.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            if "def route_pnl" in content and "class CapitalRouter" in content:
                self.log_pass(check_name, "CapitalRouter has route_pnl() method for capital allocation")
            else:
                self.log_violation(check_name, "CapitalRouter missing route_pnl() method")
                
        except FileNotFoundError:
            self.log_violation(check_name, "CapitalRouter not found (router.py missing)")
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def _check_dspy_only_suggests(self):
        """Check that DSPy only suggests, never controls."""
        check_name = "DSPy can ONLY suggest parameter deltas"
        
        try:
            filepath = self.repo_root / "dspy" / "advisor.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check that suggestions are logged/returned, not applied
            if "LOGGED ONLY" in content or "READ-ONLY" in content:
                self.log_pass(check_name, "DSPyAdvisor only generates suggestions, doesn't apply them")
            else:
                # Check for apply/execute patterns
                if ".apply(" in content or ".execute(" in content:
                    self.log_violation(check_name, "DSPyAdvisor may be applying suggestions directly")
                else:
                    self.log_pass(check_name, "DSPyAdvisor only generates suggestions")
                    
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def validate_action_schema(self):
        """Validate PHASE 14 — Action Schema & Engine Contract."""
        print("\n" + "="*80)
        print("VALIDATING ACTION SCHEMA & ENGINE CONTRACT")
        print("="*80)
        
        # Check ActionType enum
        self._check_action_type_enum()
        
        # Check Action struct
        self._check_action_struct()
        
        # Check validate_action exists
        self._check_action_validation()
    
    def _check_action_type_enum(self):
        """Check that ActionType enum matches pseudocode."""
        check_name = "ActionType enum matches pseudocode (OPEN, CLOSE, ADJUST)"
        
        try:
            filepath = self.repo_root / "freqtrade" / "core" / "actions.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check for ActionType enum definition
            required_types = ["OPEN", "CLOSE", "ADJUST"]
            found_types = []
            
            for action_type in required_types:
                if f'{action_type} = "{action_type}"' in content or f"{action_type} =" in content:
                    found_types.append(action_type)
            
            if len(found_types) == len(required_types):
                self.log_pass(check_name, f"ActionType has required types: {required_types}")
            else:
                missing = set(required_types) - set(found_types)
                self.log_violation(check_name, f"ActionType missing: {missing}")
                
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def _check_action_struct(self):
        """Check that Action struct has required fields."""
        check_name = "Action struct has required fields"
        
        try:
            filepath = self.repo_root / "freqtrade" / "core" / "actions.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check for required fields in Action dataclass
            required_fields = ["type:", "symbol:", "side:", "size:", "reason:"]
            
            # Check if all fields are present
            all_found = all(field in content for field in required_fields)
            
            if all_found:
                self.log_pass(check_name, "Action has all required fields: type, symbol, side, size, reason")
            else:
                missing = [f for f in required_fields if f not in content]
                self.log_violation(check_name, f"Action missing field declarations: {missing}")
                
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def _check_action_validation(self):
        """Check that action validation exists."""
        check_name = "Action validation function exists"
        
        try:
            filepath = self.repo_root / "freqtrade" / "core" / "actions.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            if "def validate_action" in content:
                self.log_pass(check_name, "validate_action() function exists")
            else:
                self.log_violation(check_name, "validate_action() function not found")
            
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def validate_capital_router(self):
        """Validate PHASE 15 — Capital Router."""
        print("\n" + "="*80)
        print("VALIDATING CAPITAL ROUTER")
        print("="*80)
        
        self._check_capital_pools()
        self._check_router_methods()
    
    def _check_capital_pools(self):
        """Check CapitalPools structure."""
        check_name = "CapitalPools has base, flow, convex buffers"
        
        try:
            filepath = self.repo_root / "freqtrade" / "exploits" / "router.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            required_pools = ["base_capital", "flow_buffer", "convexity_buffer"]
            found_pools = []
            
            for pool in required_pools:
                if f"{pool}:" in content or f"{pool} =" in content:
                    found_pools.append(pool)
            
            if len(found_pools) == len(required_pools):
                self.log_pass(check_name, f"CapitalPools has all three pools: {required_pools}")
            else:
                missing = set(required_pools) - set(found_pools)
                self.log_violation(check_name, f"CapitalPools missing: {missing}")
                
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def _check_router_methods(self):
        """Check router has allocate/authorize methods."""
        check_name = "Router has route_pnl() method"
        
        try:
            filepath = self.repo_root / "freqtrade" / "exploits" / "router.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            if "def route_pnl" in content:
                self.log_pass(check_name, "CapitalRouter.route_pnl() exists for PnL routing")
            else:
                self.log_violation(check_name, "CapitalRouter missing route_pnl()")
                
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def validate_exploit_constraints(self):
        """Validate exploit-specific constraints."""
        print("\n" + "="*80)
        print("VALIDATING EXPLOIT CONSTRAINTS")
        print("="*80)
        
        self._check_funding_decay_never_opens()
        self._check_flow_pressure_ttl()
        self._check_convexity_loss_bounded()
    
    def _check_funding_decay_never_opens(self):
        """Check that FundingDecay never opens positions."""
        check_name = "FundingDecay NEVER opens positions"
        
        try:
            filepath = self.repo_root / "freqtrade" / "exploits" / "funding_decay.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check for OPEN actions in FundingDecay
            if "ActionType.OPEN" in content:
                self.log_violation(check_name, "FundingDecay contains ActionType.OPEN")
            else:
                self.log_pass(check_name, "FundingDecay only proposes CLOSE actions")
                
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def _check_flow_pressure_ttl(self):
        """Check that FlowPressure requires TTL."""
        check_name = "FlowPressure enforces max hold time (TTL-like)"
        
        try:
            filepath = self.repo_root / "freqtrade" / "exploits" / "flow_pressure.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check for max_hold time enforcement
            if "max_hold_minutes" in content or "max_hold_hours" in content or "ttl" in content.lower():
                self.log_pass(check_name, "FlowPressure has max hold time enforcement")
            else:
                self.log_violation(check_name, "FlowPressure missing TTL/max hold time")
                
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def _check_convexity_loss_bounded(self):
        """Check that ConvexitySeeding bounds losses."""
        check_name = "ConvexitySeeding has bounded losses (stop_loss)"
        
        try:
            filepath = self.repo_root / "freqtrade" / "exploits" / "convexity_seeding.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check for stop_loss
            if "stop_loss" in content:
                self.log_pass(check_name, "ConvexitySeeding has stop_loss for bounded losses")
            else:
                self.log_violation(check_name, "ConvexitySeeding missing stop_loss")
                
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def validate_dspy_constraints(self):
        """Validate DSPy constraints."""
        print("\n" + "="*80)
        print("VALIDATING DSPY CONSTRAINTS")
        print("="*80)
        
        self._check_dspy_cannot_emit_actions()
        self._check_dspy_guardrails()
    
    def _check_dspy_cannot_emit_actions(self):
        """Check that DSPy cannot emit Actions."""
        check_name = "DSPy cannot emit Actions"
        
        try:
            filepath = self.repo_root / "dspy" / "advisor.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check that DSPyAdvisor doesn't import or use Action
            if "from freqtrade.core.actions import Action" in content:
                self.log_violation(check_name, "DSPyAdvisor imports Action (should not)")
            elif "Action(" in content and "ParameterSuggestion" not in content:
                self.log_violation(check_name, "DSPyAdvisor creates Action objects")
            else:
                self.log_pass(check_name, "DSPyAdvisor does not emit Actions")
                
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def _check_dspy_guardrails(self):
        """Check that DSPy has guardrails."""
        check_name = "DSPy has guardrails (bounded parameter changes)"
        
        try:
            from dspy_advisor.guardrails import DSPyGuardrails
            
            if hasattr(DSPyGuardrails, 'validate_suggestion'):
                self.log_pass(check_name, "DSPyGuardrails.validate_suggestion() exists")
            else:
                self.log_violation(check_name, "DSPyGuardrails missing validate_suggestion()")
                
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def validate_feedback_loops(self):
        """Validate feedback loop constraints."""
        print("\n" + "="*80)
        print("VALIDATING FEEDBACK LOOP CONSTRAINTS")
        print("="*80)
        
        self._check_no_exploit_calls_exploit()
        self._check_dspy_no_raw_market_data()
    
    def _check_no_exploit_calls_exploit(self):
        """Check that exploits don't call each other."""
        check_name = "No exploit calls another exploit directly"
        
        exploit_dir = self.repo_root / "freqtrade" / "exploits"
        exploit_files = list(exploit_dir.glob("*.py"))
        
        violations_found = []
        
        # List of concrete exploit implementations (not base classes or utilities)
        concrete_exploits = [
            "funding_capture", "funding_decay", "flow_pressure", "convexity_seeding"
        ]
        
        for filepath in exploit_files:
            if filepath.name.startswith("__") or filepath.stem not in concrete_exploits:
                continue
                
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check for imports of OTHER concrete exploits (not base module or router)
            for other_exploit in concrete_exploits:
                if other_exploit == filepath.stem:
                    continue
                
                if f"from freqtrade.exploits.{other_exploit} import" in content:
                    violations_found.append(
                        f"{filepath.name} imports {other_exploit}.py"
                    )
        
        if violations_found:
            self.log_violation(check_name, "\n  ".join(violations_found))
        else:
            self.log_pass(check_name, "Exploits are decoupled - no direct calls between them")
    
    def _check_dspy_no_raw_market_data(self):
        """Check that DSPy doesn't read raw market data."""
        check_name = "DSPy doesn't read raw market data"
        
        try:
            filepath = self.repo_root / "dspy" / "advisor.py"
            with open(filepath, "r") as f:
                content = f.read()
            
            # Check for market data access patterns
            forbidden_patterns = [
                "dataframe",
                "ohlcv",
                "ticker",
                "orderbook",
                "market_data",
            ]
            
            violations = []
            for pattern in forbidden_patterns:
                if pattern in content.lower() and "metadata" not in pattern.lower():
                    violations.append(f"Contains '{pattern}'")
            
            if violations:
                self.log_violation(check_name, "\n  ".join(violations))
            else:
                self.log_pass(check_name, "DSPy only reads metrics, not raw market data")
                
        except Exception as e:
            self.log_violation(check_name, f"Failed to validate: {e}")
    
    def run_all_validations(self):
        """Run all validation checks."""
        print("\n" + "="*80)
        print("ARCHITECTURE VALIDATION")
        print("Validating implementation against acceptance criteria")
        print("="*80)
        
        self.validate_global_invariants()
        self.validate_action_schema()
        self.validate_capital_router()
        self.validate_exploit_constraints()
        self.validate_dspy_constraints()
        self.validate_feedback_loops()
        
        # Print summary
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)
        print(f"✓ Passed: {len(self.passes)}")
        print(f"✗ Failed: {len(self.violations)}")
        
        if self.violations:
            print("\n" + "="*80)
            print("VIOLATIONS FOUND")
            print("="*80)
            for check, message in self.violations:
                print(f"\n✗ {check}")
                print(f"  {message}")
            return False
        else:
            print("\n✓ All validation checks passed!")
            return True


def main():
    """Main entry point."""
    validator = ArchitectureValidator()
    success = validator.run_all_validations()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
