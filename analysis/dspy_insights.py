"""
DSPy LM-Based Insights Script

This script uses DSPy with a local LLM (via Ollama) to generate
manual insights and parameter adjustment suggestions from trading metrics.

Setup:
1. Install dependencies: pip install dspy-ai ollama
2. Run Ollama locally: ollama run llama3.2
3. Export metrics from QuestDB or use parquet files
4. Run this script: python analysis/dspy_insights.py

Output:
- Manual adjustment suggestions (e.g., "Close 20% positions at 55% deployed")
- Logged to stdout for human review
- NO automatic application to engine

This has ZERO impact on trading execution - suggestions are for manual review only.
"""

import sys
from pathlib import Path

try:
    import dspy
    from dspy.teleprompt import BootstrapFewShot
except ImportError:
    print("ERROR: dspy-ai not installed. Run: pip install dspy-ai")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas not installed. Run: pip install pandas")
    sys.exit(1)


class InsightSignature(dspy.Signature):
    """Generate manual adjustment suggestions from metrics."""
    context: str = dspy.InputField(desc="Metrics data including deployed capital and PnL statistics")
    suggestion: str = dspy.OutputField(desc="Manual tweaks to consider for trading parameters")


def load_metrics_from_parquet(parquet_path: str = "exports/metrics.parquet") -> pd.DataFrame:
    """Load metrics from parquet file."""
    path = Path(parquet_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Metrics file not found at {parquet_path}. "
            "Please export metrics first or check the path."
        )
    
    print(f"Loading metrics from {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    print(f"Loaded {len(df)} metric records")
    return df


def load_metrics_from_questdb(
    host: str = "localhost",
    port: int = 9000,
    query: str = "SELECT * FROM trading_metrics"
) -> pd.DataFrame:
    """Load metrics from QuestDB."""
    try:
        from questdb.ingress import Sender
    except ImportError:
        raise ImportError(
            "QuestDB not installed. Run: pip install questdb\n"
            "Or use parquet export instead."
        )
    
    import psycopg2
    
    print(f"Connecting to QuestDB at {host}:{port}...")
    conn = psycopg2.connect(
        host=host,
        port=8812,  # PostgreSQL wire protocol port
        user='admin',
        password='quest',
        database='qdb'
    )
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"Loaded {len(df)} metric records from QuestDB")
    return df


def prepare_context(df: pd.DataFrame) -> str:
    """Prepare context string from metrics dataframe."""
    # Calculate aggregate statistics
    if 'deployed_capital_pct' in df.columns:
        deployed_avg = df['deployed_capital_pct'].mean()
        deployed_max = df['deployed_capital_pct'].max()
    else:
        deployed_avg = 0.0
        deployed_max = 0.0
    
    if 'pnl_gain_pct' in df.columns:
        pnl_avg = df['pnl_gain_pct'].mean()
        pnl_max = df['pnl_gain_pct'].max()
        pnl_min = df['pnl_gain_pct'].min()
    elif 'realized_pnl' in df.columns:
        pnl_avg = df['realized_pnl'].mean()
        pnl_max = df['realized_pnl'].max()
        pnl_min = df['realized_pnl'].min()
    else:
        pnl_avg = 0.0
        pnl_max = 0.0
        pnl_min = 0.0
    
    if 'win_rate' in df.columns:
        win_rate = df['win_rate'].mean()
    else:
        win_rate = 0.0
    
    if 'sharpe_ratio' in df.columns:
        sharpe = df['sharpe_ratio'].mean()
    else:
        sharpe = 0.0
    
    # Build context string
    context = f"""
Trading Metrics Summary:
- Average Deployed Capital: {deployed_avg:.2f}%
- Maximum Deployed Capital: {deployed_max:.2f}%
- Average PnL Gain: {pnl_avg:.2f}%
- Maximum PnL Gain: {pnl_max:.2f}%
- Minimum PnL Gain: {pnl_min:.2f}%
- Win Rate: {win_rate:.2f}%
- Sharpe Ratio: {sharpe:.2f}
- Total Records: {len(df)}
""".strip()
    
    return context


def generate_insight_simple(context: str) -> str:
    """Generate insight using simple ChainOfThought."""
    print("\n" + "=" * 80)
    print("Generating Insights with DSPy ChainOfThought")
    print("=" * 80 + "\n")
    
    # Create the program
    generate_insight = dspy.ChainOfThought(InsightSignature)
    
    # Generate response
    print("Context provided to LLM:")
    print(context)
    print("\nGenerating suggestion...\n")
    
    response = generate_insight(context=context)
    
    return response.suggestion


def generate_insight_optimized(context: str, examples: list = None) -> str:
    """
    Generate insight using BootstrapFewShot optimization.
    
    This is an optional advanced usage showing how to optimize
    the prompt with few-shot examples.
    """
    if examples is None:
        # Create some example context-suggestion pairs for training
        examples = [
            dspy.Example(
                context="Deployed avg: 75.00%, PnL gain avg: 3.50%",
                suggestion="Consider closing 25% of positions when deployed capital exceeds 70% to reduce risk."
            ).with_inputs('context'),
            dspy.Example(
                context="Deployed avg: 45.00%, PnL gain avg: 8.20%, Win Rate: 65.00%",
                suggestion="Strong performance metrics suggest maintaining current allocation or increasing slightly."
            ).with_inputs('context'),
            dspy.Example(
                context="Deployed avg: 90.00%, PnL gain avg: 1.20%, Sharpe Ratio: 0.50",
                suggestion="High deployment with low returns suggests reducing position sizes by 30-40%."
            ).with_inputs('context'),
        ]
    
    print("\n" + "=" * 80)
    print("Generating Insights with BootstrapFewShot Optimization")
    print("=" * 80 + "\n")
    
    # Define a simple metric function for optimization
    def validate_output(example, pred, trace=None):
        # Simple validation: check if suggestion is non-empty
        return len(pred.suggestion) > 20
    
    # Create base program
    class InsightProgram(dspy.Module):
        def __init__(self):
            super().__init__()
            self.generate = dspy.ChainOfThought(InsightSignature)
        
        def forward(self, context):
            return self.generate(context=context)
    
    # Optimize with BootstrapFewShot
    print("Optimizing with few-shot examples...")
    config = dict(max_bootstrapped_demos=3, max_labeled_demos=3)
    optimizer = BootstrapFewShot(metric=validate_output, **config)
    
    optimized_program = optimizer.compile(
        InsightProgram(),
        trainset=examples
    )
    
    print("\nContext provided to LLM:")
    print(context)
    print("\nGenerating optimized suggestion...\n")
    
    # Generate response
    response = optimized_program(context=context)
    
    return response.suggestion


def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("DSPy LM-Based Insights for Trading Metrics")
    print("=" * 80)
    print("\nThis script generates manual adjustment suggestions using a local LLM.")
    print("Suggestions are for MANUAL REVIEW ONLY and have NO IMPACT on execution.\n")
    
    # Step 1: Configure DSPy with Ollama
    print("Step 1: Configuring DSPy with Ollama (llama3.2)")
    print("-" * 80)
    
    try:
        # Configure Ollama as the LM
        ollama = dspy.OllamaLocal(model='llama3.2')
        dspy.settings.configure(lm=ollama)
        print("✓ DSPy configured with Ollama (llama3.2)")
    except Exception as e:
        print(f"✗ ERROR: Failed to configure Ollama: {e}")
        print("\nMake sure Ollama is running:")
        print("  1. Install Ollama: https://ollama.ai/")
        print("  2. Run: ollama run llama3.2")
        print("  3. Verify: ollama list")
        sys.exit(1)
    
    # Step 2: Load metrics
    print("\nStep 2: Loading metrics")
    print("-" * 80)
    
    # Try to load from parquet first, fallback to QuestDB if needed
    metrics_path = "exports/metrics.parquet"
    
    try:
        df = load_metrics_from_parquet(metrics_path)
    except FileNotFoundError:
        print(f"Metrics file not found at {metrics_path}")
        print("\nTrying to load from QuestDB...")
        try:
            df = load_metrics_from_questdb()
        except Exception as e:
            print(f"✗ ERROR: Could not load from QuestDB: {e}")
            print("\nPlease either:")
            print("  1. Export metrics to exports/metrics.parquet, or")
            print("  2. Ensure QuestDB is running with trading metrics")
            sys.exit(1)
    
    # Step 3: Prepare context
    print("\nStep 3: Preparing context from metrics")
    print("-" * 80)
    context = prepare_context(df)
    print("✓ Context prepared")
    
    # Step 4: Generate insights
    print("\nStep 4: Generating insights")
    print("-" * 80)
    
    # Simple ChainOfThought approach
    suggestion = generate_insight_simple(context)
    
    print("\n" + "=" * 80)
    print("GENERATED SUGGESTION (Manual Review Only)")
    print("=" * 80)
    print(suggestion)
    print("=" * 80)
    
    # Optional: Show optimized approach
    print("\n" + "=" * 80)
    print("Optional: BootstrapFewShot Optimization Example")
    print("=" * 80)
    print("\nTo use few-shot optimization, uncomment the following:")
    print("# suggestion_optimized = generate_insight_optimized(context)")
    print("#")
    print("# This approach uses example pairs to improve suggestions.")
    print("# See the code for details on how to customize examples.")
    
    print("\n" + "=" * 80)
    print("IMPORTANT: Suggestions above are for MANUAL REVIEW ONLY")
    print("They are NOT automatically applied to the trading engine.")
    print("Review suggestions and manually adjust configuration if appropriate.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
