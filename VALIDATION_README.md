# Architecture Validation Tools

This directory contains tools for validating the implementation against the architectural invariants and acceptance criteria defined for this project.

## Overview

The validation suite ensures that the codebase adheres to the core architectural principles:
- **Separation of Concerns:** Exploits generate intent, engine executes, router allocates
- **Contract Adherence:** Action schema matches specification
- **Capital Safety:** Only the router manipulates capital
- **Exploit Discipline:** Each exploit follows its specific constraints
- **DSPy Boundaries:** Advisory only, never in control
- **System Resilience:** Components are decoupled and can be removed independently

## Validation Script

### `validate_architecture.py`

Automated validation script that performs static code analysis to verify architectural invariants.

#### Usage

```bash
python validate_architecture.py
```

#### What It Validates

1. **Global Invariants (6 checks)**
   - Exploits never place orders directly
   - Exploits never mutate capital
   - Exploits only emit Actions + Metrics
   - Execution engine is deterministic
   - Capital Router is the only allocator
   - DSPy can only suggest parameter deltas

2. **Action Schema & Engine Contract (3 checks)**
   - ActionType enum matches pseudocode
   - Action struct has required fields
   - Action validation function exists

3. **Capital Router (2 checks)**
   - CapitalPools has base, flow, convex buffers
   - Router has route_pnl() method

4. **Exploit Constraints (3 checks)**
   - Funding Decay never opens positions
   - Flow Pressure enforces max hold time
   - Convexity Seeding has bounded losses

5. **DSPy Constraints (2 checks)**
   - DSPy cannot emit Actions
   - DSPy has guardrails

6. **Feedback Loop Constraints (2 checks)**
   - No exploit calls another exploit directly
   - DSPy doesn't read raw market data

#### Expected Output

```
================================================================================
ARCHITECTURE VALIDATION
Validating implementation against acceptance criteria
================================================================================

================================================================================
VALIDATING GLOBAL INVARIANTS
================================================================================
✓ PASS: Exploits NEVER place orders
✓ PASS: Exploits NEVER mutate capital
✓ PASS: Exploits ONLY emit Actions + Metrics
✓ PASS: Execution Engine is deterministic
✓ PASS: Capital Router is the ONLY allocator
✓ PASS: DSPy can ONLY suggest parameter deltas

[... more validation checks ...]

================================================================================
VALIDATION SUMMARY
================================================================================
✓ Passed: 18
✗ Failed: 0

✓ All validation checks passed!
```

#### Exit Codes

- `0` - All checks passed
- `1` - One or more checks failed

## Reports

### `VALIDATION_REPORT.md`

Comprehensive validation report containing:
- Detailed findings for each validation check
- Evidence of compliance
- Pseudocode alignment verification
- Architecture compliance matrix
- Failure containment tests

### `VALIDATION_SUMMARY.md`

Executive summary of validation results:
- High-level overview
- Key findings
- Files validated
- Conclusion and next steps

## Integration with CI/CD

The validation script can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
name: Architecture Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Architecture Validation
        run: python validate_architecture.py
```

## Extending Validation

To add new validation checks:

1. Add a new validation method to the `ArchitectureValidator` class
2. Call the method from `run_all_validations()`
3. Use `self.log_pass()` for passing checks
4. Use `self.log_violation()` for failing checks

Example:

```python
def _check_new_invariant(self):
    """Check a new architectural invariant."""
    check_name = "New invariant description"
    
    try:
        # Validation logic here
        if condition_met:
            self.log_pass(check_name, "Detailed pass message")
        else:
            self.log_violation(check_name, "Reason for failure")
    except Exception as e:
        self.log_violation(check_name, f"Failed to validate: {e}")
```

## Maintenance

### When to Run Validation

- Before merging any PR that touches core architecture
- After implementing new exploits
- After modifying the Action schema
- After changes to the Capital Router
- After DSPy modifications
- As part of regular code quality checks

### Updating Validation

When architectural requirements change:
1. Update `validate_architecture.py` with new checks
2. Update `VALIDATION_REPORT.md` with new requirements
3. Re-run validation to ensure compliance
4. Update this README if new checks are added

## Troubleshooting

### Import Errors

If you see import errors when running the validation:

```bash
# Install minimal dependencies
pip install pandas sqlalchemy numpy humanize
```

The validation script is designed to work with minimal imports by reading source files directly when possible.

### False Positives

If a check fails incorrectly:
1. Review the validation logic in the corresponding `_check_*` method
2. Update the pattern matching or validation criteria
3. Re-run validation to confirm the fix

### Adding New Patterns

To check for new forbidden patterns:
1. Add the pattern to the relevant `forbidden_patterns` list
2. Ensure the pattern is specific enough to avoid false positives
3. Test against the codebase to verify

## Dependencies

The validation script has minimal dependencies:
- Python 3.10+ (for type hints)
- Standard library modules only (ast, inspect, pathlib)

Optional dependencies for full functionality:
- pandas (for import validation)
- sqlalchemy (for import validation)
- numpy (for import validation)

## Related Documentation

- **ARCHITECTURE.md** - System architecture overview
- **BOUNDED_CONTROL_SUMMARY.md** - DSPy bounded control principles
- **IMPLEMENTATION_SUMMARY.md** - Implementation details
- **PROJECT_STATUS.md** - Current project status

## License

Same as the project license.

## Contact

For questions about validation or to report issues with the validation suite, please open an issue in the repository.
