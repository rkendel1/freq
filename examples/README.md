# Examples

This directory contains example code showing how to use the execution engine.

## Running Examples

### Attribution Example
Shows how PnL attribution works across different positions:

```bash
python examples/attribution_example.py
```

### Convexity Seeding Example
Demonstrates position management with convexity considerations:

```bash
python examples/convexity_seeding_example.py
```

### Router Example
Shows how to route orders across different execution venues:

```bash
python examples/router_example.py
```

## Running the Trading Bot Backend

To run the actual trading bot in dry-run mode (no real trades):

### 1. Create User Directory

```bash
python -m freqtrade create-userdir --userdir user_data
```

### 2. Create Configuration

```bash
# Copy example config
cp config_examples/config_quickstart.example.json user_data/config.json

# Or create interactively
python -m freqtrade new-config --config user_data/config.json
```

### 3. Create or Use a Strategy

The example config references `SampleStrategy`. You can create your own:

```bash
python -m freqtrade new-strategy --strategy MyStrategy --userdir user_data
```

Or use the NullExploitModule for testing (does nothing, just proves the engine works):

Edit your `user_data/config.json` and add:
```json
{
  "exploit_module": "freqtrade.exploits.exploit_module.NullExploitModule",
  ...
}
```

### 4. Run the Bot

```bash
# Dry run (no real trading)
python -m freqtrade trade --config user_data/config.json --strategy SampleStrategy

# For backtesting instead
python -m freqtrade backtesting --config user_data/config.json --strategy SampleStrategy
```

## Important Notes

- **Always use dry_run: true in config for testing**
- The bot requires exchange API keys even in dry-run mode (for market data)
- For local development without exchange connectivity, use the demo UI instead

## Demo UI

For a visual demonstration without needing exchange setup:

```bash
./start_demo.sh      # Linux/Mac
./start_demo.ps1     # Windows
```

See [LOCAL_DEVELOPMENT.md](../LOCAL_DEVELOPMENT.md) for complete setup instructions.
