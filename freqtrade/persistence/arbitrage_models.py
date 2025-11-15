"""Database models for arbitrage trading"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from freqtrade.persistence.base import ModelBase, SessionType


logger = logging.getLogger(__name__)


class ArbitrageOpportunity(ModelBase):
    """
    Model to track detected arbitrage opportunities
    """
    __tablename__ = "arbitrage_opportunities"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Opportunity details
    pair: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    exchange_buy: Mapped[str] = mapped_column(String(25), nullable=False)
    exchange_sell: Mapped[str] = mapped_column(String(25), nullable=False)
    
    # Prices
    buy_price: Mapped[float] = mapped_column(Float, nullable=False)
    sell_price: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Spread and profit
    spread_percent: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    estimated_profit_percent: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_profit_amount: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Fees
    buy_fee_percent: Mapped[float] = mapped_column(Float, nullable=False)
    sell_fee_percent: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Trade amount
    trade_amount: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Status
    executed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    # Session management
    session: SessionType
    
    def __repr__(self) -> str:
        return (
            f"ArbitrageOpportunity(id={self.id}, pair={self.pair}, "
            f"spread={self.spread_percent:.2f}%, profit={self.estimated_profit_percent:.2f}%)"
        )
    
    @staticmethod
    def create_opportunity(
        pair: str,
        exchange_buy: str,
        exchange_sell: str,
        buy_price: float,
        sell_price: float,
        spread_percent: float,
        estimated_profit_percent: float,
        estimated_profit_amount: float,
        buy_fee_percent: float,
        sell_fee_percent: float,
        trade_amount: float,
    ) -> "ArbitrageOpportunity":
        """Create a new arbitrage opportunity record"""
        opportunity = ArbitrageOpportunity(
            pair=pair,
            exchange_buy=exchange_buy,
            exchange_sell=exchange_sell,
            buy_price=buy_price,
            sell_price=sell_price,
            spread_percent=spread_percent,
            estimated_profit_percent=estimated_profit_percent,
            estimated_profit_amount=estimated_profit_amount,
            buy_fee_percent=buy_fee_percent,
            sell_fee_percent=sell_fee_percent,
            trade_amount=trade_amount,
            executed=False,
        )
        
        ArbitrageOpportunity.session.add(opportunity)
        ArbitrageOpportunity.session.commit()
        
        return opportunity
    
    @staticmethod
    def get_recent_opportunities(
        limit: int = 100,
        executed: Optional[bool] = None,
    ) -> list["ArbitrageOpportunity"]:
        """Get recent arbitrage opportunities
        
        Args:
            limit: Maximum number of opportunities to return
            executed: Filter by execution status (None = all)
            
        Returns:
            List of opportunities
        """
        query = ArbitrageOpportunity.session.query(ArbitrageOpportunity)
        
        if executed is not None:
            query = query.filter(ArbitrageOpportunity.executed == executed)
        
        query = query.order_by(ArbitrageOpportunity.detected_at.desc())
        query = query.limit(limit)
        
        return query.all()


class ArbitrageTrade(ModelBase):
    """
    Model to track executed arbitrage trades
    """
    __tablename__ = "arbitrage_trades"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Link to opportunity
    opportunity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Trade details
    pair: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    exchange_buy: Mapped[str] = mapped_column(String(25), nullable=False)
    exchange_sell: Mapped[str] = mapped_column(String(25), nullable=False)
    
    # Buy order
    buy_order_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    buy_price: Mapped[float] = mapped_column(Float, nullable=False)
    buy_amount: Mapped[float] = mapped_column(Float, nullable=False)
    buy_fee: Mapped[float] = mapped_column(Float, nullable=False)
    buy_status: Mapped[str] = mapped_column(String(25), nullable=False, default="pending")
    
    # Sell order
    sell_order_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sell_price: Mapped[float] = mapped_column(Float, nullable=False)
    sell_amount: Mapped[float] = mapped_column(Float, nullable=False)
    sell_fee: Mapped[float] = mapped_column(Float, nullable=False)
    sell_status: Mapped[str] = mapped_column(String(25), nullable=False, default="pending")
    
    # Profit/Loss
    realized_profit_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    realized_profit_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Overall status
    status: Mapped[str] = mapped_column(
        String(25), 
        nullable=False, 
        default="pending",
        index=True
    )  # pending, partial, completed, failed, cancelled
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Session management
    session: SessionType
    
    def __repr__(self) -> str:
        return (
            f"ArbitrageTrade(id={self.id}, pair={self.pair}, "
            f"status={self.status}, profit={self.realized_profit_percent}%)"
        )
    
    @staticmethod
    def create_trade(
        pair: str,
        exchange_buy: str,
        exchange_sell: str,
        buy_price: float,
        sell_price: float,
        amount: float,
        buy_fee: float = 0.0,
        sell_fee: float = 0.0,
        opportunity_id: Optional[int] = None,
    ) -> "ArbitrageTrade":
        """Create a new arbitrage trade record"""
        trade = ArbitrageTrade(
            opportunity_id=opportunity_id,
            pair=pair,
            exchange_buy=exchange_buy,
            exchange_sell=exchange_sell,
            buy_price=buy_price,
            buy_amount=amount,
            buy_fee=buy_fee,
            buy_status="pending",
            sell_price=sell_price,
            sell_amount=amount,
            sell_fee=sell_fee,
            sell_status="pending",
            status="pending",
        )
        
        ArbitrageTrade.session.add(trade)
        ArbitrageTrade.session.commit()
        
        return trade
    
    def update_buy_order(
        self,
        order_id: str,
        status: str,
        actual_price: Optional[float] = None,
        actual_amount: Optional[float] = None,
        fee: Optional[float] = None,
    ) -> None:
        """Update buy order details"""
        self.buy_order_id = order_id
        self.buy_status = status
        
        if actual_price is not None:
            self.buy_price = actual_price
        if actual_amount is not None:
            self.buy_amount = actual_amount
        if fee is not None:
            self.buy_fee = fee
        
        self._update_overall_status()
        ArbitrageTrade.session.commit()
    
    def update_sell_order(
        self,
        order_id: str,
        status: str,
        actual_price: Optional[float] = None,
        actual_amount: Optional[float] = None,
        fee: Optional[float] = None,
    ) -> None:
        """Update sell order details"""
        self.sell_order_id = order_id
        self.sell_status = status
        
        if actual_price is not None:
            self.sell_price = actual_price
        if actual_amount is not None:
            self.sell_amount = actual_amount
        if fee is not None:
            self.sell_fee = fee
        
        self._update_overall_status()
        ArbitrageTrade.session.commit()
    
    def _update_overall_status(self) -> None:
        """Update overall trade status based on order statuses"""
        if self.buy_status == "filled" and self.sell_status == "filled":
            self.status = "completed"
            self.completed_at = datetime.now(timezone.utc)
            self._calculate_profit()
        elif self.buy_status == "failed" or self.sell_status == "failed":
            self.status = "failed"
        elif self.buy_status == "cancelled" or self.sell_status == "cancelled":
            self.status = "cancelled"
        elif self.buy_status == "filled" or self.sell_status == "filled":
            self.status = "partial"
    
    def _calculate_profit(self) -> None:
        """Calculate realized profit"""
        # Total cost (buy + fees)
        total_cost = (self.buy_price * self.buy_amount) + self.buy_fee
        
        # Total revenue (sell - fees)
        total_revenue = (self.sell_price * self.sell_amount) - self.sell_fee
        
        # Profit
        self.realized_profit_amount = total_revenue - total_cost
        
        # Profit percentage
        if total_cost > 0:
            self.realized_profit_percent = (self.realized_profit_amount / total_cost) * 100
        else:
            self.realized_profit_percent = 0.0
    
    def set_error(self, error_message: str) -> None:
        """Set error message and mark as failed"""
        self.error_message = error_message
        self.status = "failed"
        ArbitrageTrade.session.commit()
    
    @staticmethod
    def get_recent_trades(
        limit: int = 100,
        status: Optional[str] = None,
    ) -> list["ArbitrageTrade"]:
        """Get recent arbitrage trades
        
        Args:
            limit: Maximum number of trades to return
            status: Filter by status (None = all)
            
        Returns:
            List of trades
        """
        query = ArbitrageTrade.session.query(ArbitrageTrade)
        
        if status is not None:
            query = query.filter(ArbitrageTrade.status == status)
        
        query = query.order_by(ArbitrageTrade.created_at.desc())
        query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_statistics(days: int = 30) -> dict[str, Any]:
        """Get trading statistics
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Dictionary with statistics
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = ArbitrageTrade.session.query(ArbitrageTrade).filter(
            ArbitrageTrade.created_at >= cutoff_date
        )
        
        all_trades = query.all()
        completed_trades = [t for t in all_trades if t.status == "completed"]
        
        total_trades = len(all_trades)
        successful_trades = len(completed_trades)
        
        total_profit = sum(
            t.realized_profit_amount for t in completed_trades 
            if t.realized_profit_amount is not None
        )
        
        avg_profit = total_profit / successful_trades if successful_trades > 0 else 0.0
        
        success_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        return {
            "total_trades": total_trades,
            "successful_trades": successful_trades,
            "failed_trades": len([t for t in all_trades if t.status == "failed"]),
            "pending_trades": len([t for t in all_trades if t.status == "pending"]),
            "total_profit": total_profit,
            "average_profit": avg_profit,
            "success_rate": success_rate,
            "period_days": days,
        }
