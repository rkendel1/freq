"""
ML Model Training Script for Pattern Detection.

This script trains a RandomForest model on historical trading metrics
to predict PnL gain from deployed capital percentage and other features.

Usage:
    python ml/train.py

Requirements:
    - Historical data in exports/metrics.parquet (or from QuestDB)
    - scikit-learn and joblib installed
    - Data must include: deployed_capital_pct, open_positions, pnl_gain_pct

The trained model is saved to ml/model.pkl and can be loaded by
ExploitModule instances when ml_enabled: true in config.
"""

import logging
import sys
from pathlib import Path

try:
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    import joblib
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Install required packages with: pip install scikit-learn joblib pandas")
    sys.exit(1)


logger = logging.getLogger(__name__)


def load_data(data_path: str = 'exports/metrics.parquet') -> pd.DataFrame:
    """
    Load historical metrics data.
    
    Args:
        data_path: Path to parquet file with historical metrics
        
    Returns:
        DataFrame with historical trading metrics
        
    Raises:
        FileNotFoundError: If data file doesn't exist
        ValueError: If required columns are missing
    """
    if not Path(data_path).exists():
        raise FileNotFoundError(
            f"Data file not found: {data_path}\n"
            "Please export historical metrics first or specify a different path."
        )
    
    df = pd.read_parquet(data_path)
    
    # Verify required columns exist
    required_columns = ['deployed_capital_pct', 'open_positions', 'pnl_gain_pct']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}\n"
            f"Available columns: {list(df.columns)}"
        )
    
    return df


def train_model(df: pd.DataFrame, n_estimators: int = 100, test_size: float = 0.2) -> tuple:
    """
    Train RandomForest model on historical data.
    
    Args:
        df: DataFrame with historical metrics
        n_estimators: Number of trees in the forest
        test_size: Fraction of data to use for testing
        
    Returns:
        Tuple of (trained_model, test_score)
    """
    # Feature columns
    feature_columns = ['deployed_capital_pct', 'open_positions']
    X = df[feature_columns]
    
    # Target column (what we want to predict)
    y = df['pnl_gain_pct']
    
    # Split into train and test sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )
    
    # Train the model
    logger.info(f"Training RandomForest with {n_estimators} estimators...")
    model = RandomForestRegressor(n_estimators=n_estimators, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate on test set
    test_score = model.score(X_test, y_test)
    logger.info(f"Model R² score on test set: {test_score:.4f}")
    
    return model, test_score


def save_model(model, output_path: str = 'ml/model.pkl') -> None:
    """
    Save trained model to disk.
    
    Args:
        model: Trained scikit-learn model
        output_path: Path to save the model
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)
    logger.info(f"Model saved to {output_path}")


def main():
    """Main training pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Load data
        logger.info("Loading training data...")
        df = load_data()
        logger.info(f"Loaded {len(df)} rows of data")
        
        # Train model
        model, test_score = train_model(df)
        
        # Save model
        save_model(model)
        
        print("\n" + "="*60)
        print("ML Model Training Complete!")
        print("="*60)
        print(f"Test Score (R²): {test_score:.4f}")
        print(f"Model saved to: ml/model.pkl")
        print("\nTo use the model:")
        print("1. Set 'ml_enabled': true in your config")
        print("2. Restart the execution engine")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
