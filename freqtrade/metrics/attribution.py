"""
PnL Attribution Module

This module provides raw attribution for trades, allowing you to track
the sources and components of profit/loss for each trade.

Attribution includes:
- exploit_id: Which exploit generated this trade
- capital_source: Where the capital came from
- fees: Total fees paid (entry + exit)
- funding_earned: Funding fees earned/paid (for futures)
- holding_duration: How long the position was held

This is RAW attribution only - no analytics or aggregation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from freqtrade.persistence import Trade


@dataclass
class TradeAttribution:
    """
    Raw attribution record for a single trade.
    
    This captures all the key metrics needed to attribute PnL to its sources.
    No aggregation or analytics - just the raw data.
    
    Attributes:
        trade_id: Unique identifier for the trade
        exploit_id: ID of the exploit that generated this trade (from strategy name, enter_tag, or "unknown")
        capital_source: Source of capital used (e.g., "initial", "reinvested", "borrowed")
        pair: Trading pair
        is_short: Whether this is a short position
        
        # Entry metrics
        entry_price: Price at which position was opened
        entry_amount: Amount of asset purchased/sold
        entry_stake: Total stake amount (in quote currency)
        entry_date: Timestamp when position was opened
        
        # Exit metrics
        exit_price: Price at which position was closed (None if still open)
        exit_date: Timestamp when position was closed (None if still open)
        
        # Cost breakdown
        fee_open: Fee paid on entry (as percentage)
        fee_close: Fee paid on exit (as percentage, None if still open)
        fee_open_cost: Absolute cost of entry fee (in quote currency)
        fee_close_cost: Absolute cost of exit fee (in quote currency, None if still open)
        total_fees: Total fees paid in quote currency
        
        # Funding (for futures/margin)
        funding_fees: Total funding fees earned/paid (negative = paid, positive = earned, 0.0 for spot)
        
        # Duration
        holding_duration_seconds: How long the position was/has been held (in seconds)
        holding_duration_hours: How long the position was/has been held (in hours)
        
        # PnL (for closed trades)
        realized_profit: Absolute profit in quote currency (None if still open)
        profit_ratio: Profit as a ratio of stake (None if still open)
        
        # Metadata
        is_open: Whether the trade is still open
        exit_reason: Reason for exit (None if still open)
    """
    
    trade_id: int
    exploit_id: str
    capital_source: str
    pair: str
    is_short: bool
    
    # Entry
    entry_price: float
    entry_amount: float
    entry_stake: float
    entry_date: datetime
    
    # Exit
    exit_price: Optional[float]
    exit_date: Optional[datetime]
    
    # Fees
    fee_open: float
    fee_close: Optional[float]
    fee_open_cost: Optional[float]
    fee_close_cost: Optional[float]
    total_fees: float
    
    # Funding
    funding_fees: float
    
    # Duration
    holding_duration_seconds: float
    holding_duration_hours: float
    
    # PnL
    realized_profit: Optional[float]
    profit_ratio: Optional[float]
    
    # Metadata
    is_open: bool
    exit_reason: Optional[str]
    
    def to_dict(self) -> dict:
        """
        Convert attribution to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the attribution
        """
        return {
            "trade_id": self.trade_id,
            "exploit_id": self.exploit_id,
            "capital_source": self.capital_source,
            "pair": self.pair,
            "is_short": self.is_short,
            "entry_price": self.entry_price,
            "entry_amount": self.entry_amount,
            "entry_stake": self.entry_stake,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "exit_price": self.exit_price,
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "fee_open": self.fee_open,
            "fee_close": self.fee_close,
            "fee_open_cost": self.fee_open_cost,
            "fee_close_cost": self.fee_close_cost,
            "total_fees": self.total_fees,
            "funding_fees": self.funding_fees,
            "holding_duration_seconds": self.holding_duration_seconds,
            "holding_duration_hours": self.holding_duration_hours,
            "realized_profit": self.realized_profit,
            "profit_ratio": self.profit_ratio,
            "is_open": self.is_open,
            "exit_reason": self.exit_reason,
        }


def attribute_trade(trade: Trade, capital_source: str = "initial") -> TradeAttribution:
    """
    Attribute a trade to its exploit and capital source.
    
    This function extracts all relevant attribution data from a Trade object,
    creating a complete attribution record that can be used for analysis.
    
    Args:
        trade: Trade object to attribute
        capital_source: Source of capital ("initial", "reinvested", "borrowed", etc.)
                       Defaults to "initial" as we don't track this in the trade model yet
    
    Returns:
        TradeAttribution object with complete attribution data
    
    Example:
        >>> from freqtrade.persistence import Trade
        >>> from freqtrade.metrics.attribution import attribute_trade
        >>> 
        >>> # Assuming you have a closed trade
        >>> trade = Trade.get_trades().filter(Trade.is_open == False).first()
        >>> attribution = attribute_trade(trade, capital_source="initial")
        >>> 
        >>> print(f"Trade {attribution.trade_id}:")
        >>> print(f"  Exploit: {attribution.exploit_id}")
        >>> print(f"  Pair: {attribution.pair}")
        >>> print(f"  Holding time: {attribution.holding_duration_hours:.2f} hours")
        >>> print(f"  Total fees: {attribution.total_fees:.2f}")
        >>> print(f"  Funding fees: {attribution.funding_fees:.2f}")
        >>> print(f"  Realized profit: {attribution.realized_profit:.2f}")
    """
    # Determine exploit_id from strategy or enter_tag
    # Strategy name is the primary identifier, enter_tag can provide additional context
    exploit_id = trade.strategy or trade.enter_tag or "unknown"
    
    # Calculate holding duration
    if trade.close_date:
        duration_seconds = (trade.close_date - trade.open_date).total_seconds()
    else:
        # For open trades, calculate duration until now
        duration_seconds = (datetime.now(trade.open_date.tzinfo) - trade.open_date).total_seconds()
    
    duration_hours = duration_seconds / 3600.0
    
    # Calculate total fees
    fee_open_cost = trade.fee_open_cost or 0.0
    fee_close_cost = trade.fee_close_cost or 0.0
    total_fees = fee_open_cost + fee_close_cost
    
    # Get funding fees (for futures/margin trades)
    funding_fees = trade.funding_fees or 0.0
    
    # Build attribution record
    return TradeAttribution(
        trade_id=trade.id,
        exploit_id=exploit_id,
        capital_source=capital_source,
        pair=trade.pair,
        is_short=trade.is_short,
        
        # Entry
        entry_price=trade.open_rate,
        entry_amount=trade.amount,
        entry_stake=trade.stake_amount,
        entry_date=trade.open_date,
        
        # Exit
        exit_price=trade.close_rate,
        exit_date=trade.close_date,
        
        # Fees
        fee_open=trade.fee_open,
        fee_close=trade.fee_close,
        fee_open_cost=fee_open_cost,
        fee_close_cost=fee_close_cost,
        total_fees=total_fees,
        
        # Funding
        funding_fees=funding_fees,
        
        # Duration
        holding_duration_seconds=duration_seconds,
        holding_duration_hours=duration_hours,
        
        # PnL
        realized_profit=trade.close_profit_abs,
        profit_ratio=trade.close_profit,
        
        # Metadata
        is_open=trade.is_open,
        exit_reason=trade.exit_reason,
    )
