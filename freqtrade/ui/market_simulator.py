"""
Market Simulator - Generates realistic market data for automated demo.

This module simulates realistic price movements for different market conditions:
- Trending markets (bull/bear)
- Volatile/choppy markets
- Range-bound markets
- Mixed conditions
- Real ticker data from exchanges (NEW!)

Used by the automated demo to show how the bot behaves in real market scenarios.
"""

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import numpy as np

from freqtrade.ui.real_ticker_data import RealTickerDataSource


logger = logging.getLogger(__name__)


MarketCondition = Literal["trending_up", "trending_down", "volatile", "ranging", "mixed", "real"]


@dataclass
class MarketTick:
    """Represents a single market price tick."""
    
    timestamp: int
    price: float
    volume: float
    condition: MarketCondition


class MarketSimulator:
    """
    Simulates realistic market price movements.
    
    The simulator generates tick data that mimics real market behavior with:
    - Trend components (directional movement)
    - Volatility (price fluctuation)
    - Mean reversion (ranging behavior)
    - Random noise (market inefficiency)
    - Real ticker data from exchanges (NEW!)
    """
    
    def __init__(
        self,
        initial_price: float = 50000.0,
        condition: MarketCondition = "mixed",
        volatility: float = 0.02,  # 2% typical volatility
        tick_interval_ms: int = 1000,  # 1 second between ticks
        symbol: str = "BTC/USDT",  # Trading pair for real data
    ):
        """
        Initialize market simulator.
        
        Args:
            initial_price: Starting price for the asset
            condition: Market condition to simulate (use "real" for live data)
            volatility: Price volatility (as fraction, e.g., 0.02 = 2%)
            tick_interval_ms: Milliseconds between price ticks
            symbol: Trading pair symbol for real ticker data (e.g., "BTC/USDT")
        """
        self.current_price = initial_price
        self.initial_price = initial_price
        self.condition = condition
        self.volatility = volatility
        self.tick_interval_ms = tick_interval_ms
        self.tick_count = 0
        self.symbol = symbol
        
        # Real ticker data source (created only if needed)
        self._real_ticker_source: RealTickerDataSource | None = None
        
        # Market condition parameters
        self._setup_condition_params()
        
        # State for trend and momentum
        self.momentum = 0.0
        self.trend_direction = 1 if condition == "trending_up" else -1
        self.range_center = initial_price
        
    def _setup_condition_params(self):
        """Setup parameters based on market condition."""
        if self.condition == "trending_up":
            self.trend_strength = 0.0002  # Positive trend
            self.mean_reversion_strength = 0.05
        elif self.condition == "trending_down":
            self.trend_strength = -0.0002  # Negative trend
            self.mean_reversion_strength = 0.05
        elif self.condition == "volatile":
            self.trend_strength = 0.0
            self.mean_reversion_strength = 0.02
            self.volatility *= 2.0  # Double volatility
        elif self.condition == "ranging":
            self.trend_strength = 0.0
            self.mean_reversion_strength = 0.3  # Strong mean reversion
        else:  # mixed
            self.trend_strength = 0.0001
            self.mean_reversion_strength = 0.1
            
    def generate_tick(self) -> MarketTick:
        """
        Generate next market tick with realistic price movement.
        
        If condition is "real", fetches live data from exchanges.
        Otherwise, generates simulated data.
        
        Returns:
            MarketTick with timestamp, price, volume, and condition
        """
        self.tick_count += 1
        
        # Handle real ticker data
        if self.condition == "real":
            return self._generate_real_tick()
        
        # Otherwise, generate simulated tick
        return self._generate_simulated_tick()
    
    def _generate_real_tick(self) -> MarketTick:
        """
        Generate tick from real exchange data.
        
        Returns:
            MarketTick with real price data or simulated fallback
        """
        # Create real ticker source if not exists
        if self._real_ticker_source is None:
            self._real_ticker_source = RealTickerDataSource(cache_duration_seconds=30)
        
        # Try to fetch real ticker data
        ticker_data = self._real_ticker_source.fetch_ticker(self.symbol)
        
        if ticker_data is not None:
            # Successfully got real data
            self.current_price = ticker_data.price
            
            tick = MarketTick(
                timestamp=ticker_data.timestamp,
                price=round(ticker_data.price, 2),
                volume=round(ticker_data.volume, 2),
                condition="real",
            )
            
            logger.info(
                f"Real tick #{self.tick_count}: ${tick.price:,.2f} "
                f"from {ticker_data.exchange}"
            )
            
            return tick
        else:
            # Failed to get real data, fallback to simulation
            logger.warning(
                f"Failed to fetch real ticker data for {self.symbol}, "
                f"using simulated fallback"
            )
            return self._generate_simulated_tick()
    
    def _generate_simulated_tick(self) -> MarketTick:
        """
        Generate simulated market tick.
        
        Returns:
            MarketTick with simulated price data
        """
        # For mixed condition, occasionally change sub-condition
        if self.condition == "mixed" and self.tick_count % 50 == 0:
            self._randomize_mixed_condition()
        
        # Calculate price change components
        
        # 1. Trend component
        trend_change = self.trend_strength * self.current_price
        
        # 2. Mean reversion component (pull toward range center in ranging markets)
        mean_reversion = 0.0
        if self.condition in ("ranging", "mixed"):
            distance_from_center = self.current_price - self.range_center
            mean_reversion = -distance_from_center * self.mean_reversion_strength
        
        # 3. Momentum component (price tends to continue recent direction)
        momentum_change = self.momentum * self.current_price * 0.5
        
        # 4. Random noise (market randomness)
        random_change = np.random.normal(0, self.volatility) * self.current_price
        
        # Combine all components
        total_change = trend_change + mean_reversion + momentum_change + random_change
        
        # Update price
        new_price = self.current_price + total_change
        
        # Ensure price doesn't go negative or too extreme
        new_price = max(new_price, self.initial_price * 0.5)
        new_price = min(new_price, self.initial_price * 2.0)
        
        # Update momentum (exponential moving average of recent changes)
        price_change_pct = (new_price - self.current_price) / self.current_price
        self.momentum = 0.7 * self.momentum + 0.3 * price_change_pct
        
        # Update current price
        self.current_price = new_price
        
        # Generate volume (correlated with volatility)
        base_volume = 1000.0
        volume_volatility = abs(price_change_pct) * 10000
        volume = base_volume + random.uniform(0, volume_volatility)
        
        # Create tick
        tick = MarketTick(
            timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
            price=round(self.current_price, 2),
            volume=round(volume, 2),
            condition=self.condition,
        )
        
        logger.debug(
            f"Tick #{self.tick_count}: ${tick.price:,.2f} "
            f"({price_change_pct:+.4%}) [{self.condition}]"
        )
        
        return tick
    
    def _randomize_mixed_condition(self):
        """Randomly adjust parameters for mixed condition to simulate changing markets."""
        # Randomly adjust trend
        self.trend_strength = random.uniform(-0.0002, 0.0002)
        
        # Randomly adjust mean reversion (ranging vs trending)
        self.mean_reversion_strength = random.uniform(0.05, 0.2)
        
        # Randomly adjust volatility
        self.volatility = random.uniform(0.01, 0.03)
        
        # Reset range center occasionally
        if random.random() < 0.3:
            self.range_center = self.current_price
            
        logger.info(
            f"Mixed condition adjusted: trend={self.trend_strength:.6f}, "
            f"mean_reversion={self.mean_reversion_strength:.2f}, "
            f"volatility={self.volatility:.4f}"
        )
    
    def get_price_change_percent(self) -> float:
        """Get total price change percentage since start."""
        return ((self.current_price - self.initial_price) / self.initial_price) * 100
    
    def reset(self, condition: MarketCondition | None = None):
        """
        Reset simulator to initial state.
        
        Args:
            condition: Optional new market condition
        """
        self.current_price = self.initial_price
        self.tick_count = 0
        self.momentum = 0.0
        self.range_center = self.initial_price
        
        if condition:
            self.condition = condition
            self._setup_condition_params()
            
        logger.info(f"Market simulator reset: {self.condition} condition at ${self.initial_price:,.2f}")
