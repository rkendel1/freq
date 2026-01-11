# Demo Categories and Time-Based Features Guide

This guide explains the new **Category Presets** and **Time-Based Demo** features added to the execution engine demo.

## Overview

The demo now supports two major enhancements:

1. **Category Presets**: Pre-configured risk profiles (Conservative, Moderate, Aggressive)
2. **Time-Based Demos**: Simulate different time horizons (3 months to 10 years)

These features help you understand how different trading approaches and timeframes affect capital deployment and performance.

---

## Category Presets

Category presets allow you to quickly configure the demo with different risk profiles that represent different trading approaches.

### Available Categories

#### 🛡️ Conservative

**Best for**: Risk-averse approach, capital preservation

**Configuration**:
- Position Size: **8%** per trade
- Profit Target: **8%** (higher threshold, more patient)
- Stop Loss: **5%** (wider, more room for movement)
- Trade Cooldown: **10 ticks** (wait longer between trades)

**Impact**:
- ✅ Uses less capital per trade
- ✅ More room for price fluctuations
- ✅ Better protection against losses
- ⚠️ Slower capital deployment
- ⚠️ Takes longer to reach profit targets

**Use Case**: When you want to minimize risk and are willing to wait longer for results. Good for volatile or uncertain market conditions.

---

#### ⚖️ Moderate (Default)

**Best for**: Balanced approach, standard trading

**Configuration**:
- Position Size: **15%** per trade
- Profit Target: **5%** (balanced threshold)
- Stop Loss: **3%** (standard protection)
- Trade Cooldown: **5 ticks** (normal frequency)

**Impact**:
- ✅ Balanced risk/reward ratio
- ✅ Moderate capital deployment
- ✅ Good for most scenarios
- 📊 Industry-standard approach

**Use Case**: Default configuration suitable for most trading scenarios. Good balance between risk and reward.

---

#### ⚡ Aggressive

**Best for**: Fast capital deployment, higher risk tolerance

**Configuration**:
- Position Size: **25%** per trade
- Profit Target: **3%** (lower threshold, take profits faster)
- Stop Loss: **2%** (tighter, less tolerance for adverse movement)
- Trade Cooldown: **2 ticks** (more frequent trading)

**Impact**:
- ✅ Deploys capital faster
- ✅ Takes profits quickly
- ✅ More trading opportunities
- ⚠️ Higher sensitivity to market movements
- ⚠️ Hits stop losses more frequently
- ⚠️ Potentially higher drawdowns

**Use Case**: When you want to maximize capital efficiency and can tolerate higher risk. Good for trending markets with clear direction.

---

### How to Use Categories

1. **Switch to Automated Mode**: Select "🤖 Automated (Realistic Bot)" from the Mode dropdown
2. **Select a Category**: Choose Conservative, Moderate, or Aggressive from the Strategy dropdown
3. **Click "Apply"**: The system will apply the preset configuration
4. **Review Confirmation**: A popup will show the category description and impact
5. **Start Trading**: Click "▶️ Start Auto" to begin automated trading with the selected category

### Comparing Categories

| Aspect | Conservative | Moderate | Aggressive |
|--------|-------------|----------|-----------|
| Position Size | 8% | 15% | 25% |
| Profit Target | 8% | 5% | 3% |
| Stop Loss | 5% | 3% | 2% |
| Trade Frequency | Low | Medium | High |
| Capital Usage | Slow | Medium | Fast |
| Risk Level | Low | Medium | High |
| Best Market | Volatile/Uncertain | Most Conditions | Strong Trends |

---

## Time-Based Demos

Time-based demos allow you to simulate different investment horizons by scaling how ticks correspond to real-world time.

### Available Time Presets

#### 📅 3 Months

**Configuration**:
- Target Ticks: 1,000
- Time Scale: ~7,776 seconds per tick (~2.16 hours)
- Simulates: Approximately 3 months of trading

**Use Case**: Short-term trading evaluation, quarterly performance assessment

---

#### 📅 6 Months

**Configuration**:
- Target Ticks: 2,000
- Time Scale: ~7,776 seconds per tick (~2.16 hours)
- Simulates: Approximately 6 months of trading

**Use Case**: Semi-annual performance review, medium-term strategy testing

---

#### 📅 1 Year (Default)

**Configuration**:
- Target Ticks: 4,000
- Time Scale: ~7,884 seconds per tick (~2.19 hours)
- Simulates: Approximately 1 year of trading

**Use Case**: Annual performance projection, standard backtesting period

---

#### 📅 5 Years

**Configuration**:
- Target Ticks: 20,000
- Time Scale: ~7,884 seconds per tick (~2.19 hours)
- Simulates: Approximately 5 years of trading

**Use Case**: Long-term strategy validation, retirement planning scenarios

---

#### 📅 10 Years

**Configuration**:
- Target Ticks: 40,000
- Time Scale: ~7,884 seconds per tick (~2.19 hours)
- Simulates: Approximately 10 years of trading

**Use Case**: Very long-term projections, generational wealth building scenarios

---

### How to Use Time-Based Demos

1. **Switch to Automated Mode**: Select "🤖 Automated (Realistic Bot)" from the Mode dropdown
2. **Select a Duration**: Choose 3 months, 6 months, 1 year, 5 years, or 10 years from the Duration dropdown
3. **Click "Set Duration"**: The system will scale the time appropriately
4. **Monitor Progress**: 
   - **⏱️ Time Elapsed** card shows how much simulated time has passed
   - **🎯 Target Progress** card shows percentage completion of the selected timeframe
5. **Run Demo**: Click "▶️ Start Auto" to begin the simulation

### Understanding Time Metrics

When running a time-based demo, you'll see:

- **Time Elapsed**: Shows simulated time in the most appropriate unit (hours, days, months, or years)
- **Target Progress**: Shows what percentage of your selected timeframe has been completed
- **Trades/Min**: Shows the actual execution rate (ticks per real minute)

**Example**: 
- Selected Duration: 1 Year
- Ticks Completed: 2,000 / 4,000
- Time Elapsed: ~6 months
- Target Progress: 50%

---

## Combining Categories with Time Demos

You can combine category presets with time-based demos to see how different risk profiles perform over various timeframes.

### Example Scenarios

#### Conservative + 10 Years
**Scenario**: Long-term wealth preservation
- Slow but steady capital deployment
- Lower risk of significant losses
- Suitable for retirement accounts

#### Moderate + 1 Year
**Scenario**: Standard annual trading
- Balanced approach for typical investors
- Good for benchmarking against market indices
- Industry-standard evaluation period

#### Aggressive + 3 Months
**Scenario**: Short-term high-frequency trading
- Rapid capital deployment
- Higher potential returns (and losses)
- Suitable for active traders with high risk tolerance

---

## API Reference

### Category Endpoints

#### GET `/api/categories/list`
Returns all available category presets with descriptions and parameters.

**Response**:
```json
{
  "categories": {
    "conservative": {
      "description": "...",
      "impact": "...",
      "parameters": {
        "position_size": 0.08,
        "profit_target": 0.08,
        "stop_loss": 0.05,
        "min_ticks_between_actions": 10
      }
    },
    ...
  },
  "current_category": "moderate"
}
```

#### POST `/api/categories/apply`
Applies a category preset to the automated exploit.

**Request Body**:
```json
{
  "category": "aggressive"
}
```

**Response**:
```json
{
  "status": "applied",
  "category": "aggressive",
  "parameters": {
    "position_size": 0.25,
    "profit_target": 0.03,
    "stop_loss": 0.02,
    "min_ticks_between_actions": 2
  }
}
```

### Time Endpoints

#### GET `/api/time/config`
Returns current time configuration and elapsed time.

**Response**:
```json
{
  "tick_to_time_scale": 60.0,
  "simulation_ticks": 100,
  "elapsed": {
    "seconds": 6000,
    "minutes": 100,
    "hours": 1.67,
    "days": 0.07,
    "months": 0.002,
    "years": 0.0002
  },
  "timeframes": {
    "3_months": {
      "ticks_needed": 1000,
      "completed_pct": 10.0
    },
    ...
  }
}
```

#### POST `/api/time/preset`
Applies a time-based demo preset.

**Request Body**:
```json
{
  "preset": "1_year"
}
```

**Response**:
```json
{
  "status": "applied",
  "preset": "1_year",
  "description": "1-year simulation with ~4000 trading opportunities",
  "target_ticks": 4000,
  "tick_to_time_scale": 7884.0
}
```

---

## Best Practices

### Choosing a Category

1. **Start with Moderate**: Understand the baseline behavior before experimenting
2. **Match Risk Tolerance**: Choose a category that aligns with your real-world risk preferences
3. **Consider Market Conditions**: Use Conservative in volatile markets, Aggressive in trending markets
4. **Experiment**: Try all three categories to understand how parameters affect performance

### Choosing a Time Horizon

1. **Short-term (3-6 months)**: Good for testing new strategies quickly
2. **Medium-term (1 year)**: Standard for most backtesting and evaluation
3. **Long-term (5-10 years)**: Important for retirement planning and long-term wealth building
4. **Run Multiple**: Test the same category across different timeframes to understand long-term vs short-term behavior

### Interpreting Results

- **Capital Deployment Rate**: Compare how quickly different categories deploy capital
- **Win Rate vs Risk**: Aggressive may have lower win rates but faster profit-taking
- **Time to Target**: See how long it takes to reach capital goals under different scenarios
- **Drawdown Tolerance**: Conservative should show smaller drawdowns, Aggressive may show larger ones

---

## Frequently Asked Questions

### Q: Can I manually adjust parameters after applying a category?

**A:** Yes! Categories are starting points. After applying a category, you can manually adjust individual parameters using the DSPy parameter controls.

### Q: How accurate are the time simulations?

**A:** Time simulations are **scaled representations**, not predictions. The actual time to reach targets depends on market conditions, strategy effectiveness, and many other factors. Use these simulations to understand **relative differences** between approaches, not absolute future outcomes.

### Q: What happens if I reset during a time-based demo?

**A:** Reset clears simulation state (ticks, capital, trades) but preserves your category and time preset selections. You can continue with the same configuration.

### Q: Which category should I use for production?

**A:** The automated exploit is a **demonstration only**. Categories show how parameters affect behavior. For production, implement your own exploit module with parameters tuned to your specific strategy and risk tolerance.

### Q: Can I create custom categories?

**A:** Currently, the three presets (Conservative, Moderate, Aggressive) are built-in. You can achieve custom configurations by manually adjusting parameters or by modifying the `CATEGORY_PRESETS` dictionary in `demo_server.py`.

### Q: Why doesn't my simulation reach the exact timeframe?

**A:** The simulation runs until you stop it. Time presets define the **scaling** (how many ticks represent the timeframe) but don't automatically stop the simulation. The "Target Progress" indicator shows how far you've progressed toward that timeframe.

---

## Technical Details

### Time Scaling Formula

```python
tick_to_time_scale = (target_days * 86400) / target_ticks

# Example: 1-year preset
tick_to_time_scale = (365 * 86400) / 4000 = 7884 seconds per tick
```

### Elapsed Time Calculation

```python
elapsed_seconds = simulation_ticks * tick_to_time_scale
elapsed_days = elapsed_seconds / 86400
elapsed_months = elapsed_days / 30
elapsed_years = elapsed_days / 365
```

### Category Application

When you apply a category, the system:
1. Loads preset parameters from `CATEGORY_PRESETS`
2. Updates `automated_exploit` properties
3. Updates `current_category` tracker
4. Returns confirmation with applied parameters

---

## Examples

### Example 1: Conservative Long-term Investment

```
1. Select Mode: Automated
2. Select Strategy: Conservative
3. Click "Apply"
4. Select Duration: 10 Years
5. Click "Set Duration"
6. Click "Start Auto"
7. Monitor: Watch slow but steady growth over simulated 10 years
```

### Example 2: Aggressive Short-term Trading

```
1. Select Mode: Automated
2. Select Strategy: Aggressive
3. Click "Apply"
4. Select Duration: 3 Months
5. Click "Set Duration"
6. Click "Start Auto"
7. Monitor: Watch rapid capital deployment and quick profit-taking
```

### Example 3: Comparing Strategies

```
Test 1: Conservative + 1 Year
- Record final capital
- Note win rate and number of trades

Reset

Test 2: Aggressive + 1 Year
- Record final capital
- Note win rate and number of trades

Compare:
- Which deployed capital faster?
- Which had better risk-adjusted returns?
- Which would you prefer for your goals?
```

---

## Summary

The Category and Time-Based Demo features provide powerful tools for:

✅ **Understanding Risk Profiles**: See how Conservative, Moderate, and Aggressive approaches differ  
✅ **Visualizing Time Impact**: Understand how strategies perform over different horizons  
✅ **Testing Scenarios**: Experiment with combinations of risk and timeframe  
✅ **Making Informed Decisions**: Use simulations to guide real trading parameter selection  

Remember: These are **simulations for educational purposes**. Real market performance depends on many factors beyond these simplified models.

---

**Last Updated**: 2026-01-11  
**Version**: 1.0 - Initial release of Categories and Time-Based Demos
