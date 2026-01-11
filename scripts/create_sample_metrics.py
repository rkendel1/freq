"""
Create sample metrics for testing dspy_insights.py

This script creates a sample metrics.parquet file for demonstration purposes.
"""

import pandas as pd
from pathlib import Path

# Create sample metrics data
data = {
    'deployed_capital_pct': [45.0, 52.0, 58.0, 62.0, 55.0, 48.0, 67.0, 72.0, 65.0, 59.0] * 10,
    'pnl_gain_pct': [2.5, 3.2, 1.8, 4.1, 2.9, 1.5, 3.8, 4.5, 2.1, 3.0] * 10,
    'win_rate': [65.0, 68.0, 62.0, 70.0, 66.0, 64.0, 72.0, 75.0, 68.0, 67.0] * 10,
    'sharpe_ratio': [1.2, 1.4, 1.1, 1.6, 1.3, 1.0, 1.5, 1.7, 1.3, 1.4] * 10,
}

df = pd.DataFrame(data)

# Create exports directory if it doesn't exist
exports_dir = Path('exports')
exports_dir.mkdir(exist_ok=True)

# Save to parquet
output_path = exports_dir / 'metrics.parquet'
df.to_parquet(output_path)

print(f"✓ Created sample metrics file: {output_path}")
print(f"  - Records: {len(df)}")
print(f"  - Average Deployed Capital: {df['deployed_capital_pct'].mean():.2f}%")
print(f"  - Average PnL Gain: {df['pnl_gain_pct'].mean():.2f}%")
print(f"  - Average Win Rate: {df['win_rate'].mean():.2f}%")
print(f"  - Average Sharpe Ratio: {df['sharpe_ratio'].mean():.2f}")
print(f"\nYou can now run: python analysis/dspy_insights.py")
