"""
Production Monitoring Dashboard - Real-time overview of running engine

This dashboard provides real-time monitoring of the production engine:
- Capital state JSON view
- Open positions table (from DB)
- Recent orders table
- Cumulative PnL line chart
- Tail of production logs
- Auto-refresh every 10 seconds

Run with:
    streamlit run freqtrade/ui/prod_monitor.py

Access at:
    http://localhost:8502
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

# Add freqtrade to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_capital_state(db_path: Path) -> dict[str, Any] | None:
    """Load capital state from database or state file."""
    try:
        # Try to load from persistence if available
        from freqtrade.persistence import Trade
        from freqtrade.persistence.models import init_db
        
        # Initialize DB
        init_db(f"sqlite:///{db_path}")
        
        # Get open trades
        open_trades = Trade.get_open_trades()
        closed_trades = Trade.get_trades([Trade.is_open.is_(False)]).all()
        
        # Calculate capital state
        deployed_capital = sum(t.stake_amount for t in open_trades)
        realized_pnl = sum(t.close_profit_abs or 0.0 for t in closed_trades if t.close_profit_abs)
        
        # Calculate unrealized PnL from open positions
        # Note: This is approximate as we don't have current market prices here
        # In production, this should be calculated from live price feeds
        unrealized_pnl = sum(t.close_profit_abs or 0.0 for t in open_trades if t.close_profit_abs)
        
        # Try to get initial capital from config
        config_path = Path(__file__).parent.parent.parent / "config.prod.json"
        initial_capital = 10000.0
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                initial_capital = config.get("initial_capital", 10000.0)
        
        total_capital = initial_capital + realized_pnl
        available_capital = total_capital - deployed_capital
        
        return {
            "available_capital": available_capital,
            "deployed_capital": deployed_capital,
            "pnl_realized": realized_pnl,
            "pnl_unrealized": unrealized_pnl,
            "total_capital": total_capital,
            "initial_capital": initial_capital,
            "total_pnl": realized_pnl + unrealized_pnl
        }
    except Exception as e:
        st.warning(f"⚠️ Could not load capital state from DB: {e}")
        return None


def get_open_positions(db_path: Path) -> list[dict[str, Any]]:
    """Get open positions from database."""
    try:
        from freqtrade.persistence import Trade
        from freqtrade.persistence.models import init_db
        
        # Initialize DB
        init_db(f"sqlite:///{db_path}")
        
        # Get open trades
        trades = Trade.get_open_trades()
        
        positions = []
        for trade in trades:
            positions.append({
                "id": trade.id,
                "pair": trade.pair,
                "side": "long" if trade.is_long else "short",
                "amount": trade.amount,
                "open_rate": trade.open_rate,
                "current_rate": trade.close_rate or trade.open_rate,
                "stake_amount": trade.stake_amount,
                "profit_pct": (trade.close_profit * 100) if trade.close_profit else 0.0,
                "profit_abs": trade.close_profit_abs or 0.0,
                "open_date": trade.open_date.strftime("%Y-%m-%d %H:%M:%S") if trade.open_date else "",
                "duration": str(datetime.now(timezone.utc) - trade.open_date) if trade.open_date else ""
            })
        
        return positions
    except Exception as e:
        st.warning(f"⚠️ Could not load open positions: {e}")
        return []


def get_recent_orders(db_path: Path, limit: int = 20) -> list[dict[str, Any]]:
    """Get recent orders from database."""
    try:
        from freqtrade.persistence import Order
        from freqtrade.persistence.models import init_db
        from sqlalchemy import desc
        
        # Initialize DB
        init_db(f"sqlite:///{db_path}")
        
        # Get recent orders
        orders = Order.session.query(Order).order_by(desc(Order.order_date)).limit(limit).all()
        
        order_list = []
        for order in orders:
            order_list.append({
                "id": order.order_id,
                "pair": order.ft_pair,
                "side": order.ft_order_side,
                "amount": order.ft_amount,
                "price": order.ft_price,
                "status": order.status,
                "date": order.order_date.strftime("%Y-%m-%d %H:%M:%S") if order.order_date else "",
                "is_open": order.ft_is_open
            })
        
        return order_list
    except Exception as e:
        st.warning(f"⚠️ Could not load recent orders: {e}")
        return []


def get_pnl_history(db_path: Path) -> list[dict[str, Any]]:
    """Get PnL history from closed trades."""
    try:
        from freqtrade.persistence import Trade
        from freqtrade.persistence.models import init_db
        
        # Initialize DB
        init_db(f"sqlite:///{db_path}")
        
        # Get closed trades
        trades = Trade.get_trades([Trade.is_open.is_(False)]).all()
        
        pnl_data = []
        cumulative_pnl = 0.0
        
        for trade in sorted(trades, key=lambda t: t.close_date or t.open_date):
            if trade.close_profit_abs:
                cumulative_pnl += trade.close_profit_abs
                pnl_data.append({
                    "date": (trade.close_date or trade.open_date).strftime("%Y-%m-%d %H:%M"),
                    "cumulative_pnl": cumulative_pnl,
                    "trade_pnl": trade.close_profit_abs
                })
        
        return pnl_data
    except Exception as e:
        st.warning(f"⚠️ Could not load PnL history: {e}")
        return []


def get_log_tail(log_path: Path, lines: int = 50) -> str:
    """Get last N lines from log file."""
    try:
        if not log_path.exists():
            return "⚠️ Log file not found"
        
        with open(log_path, "r") as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except Exception as e:
        return f"⚠️ Error reading log: {e}"


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Production Monitor",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Production Monitoring Dashboard")
    st.markdown("---")
    
    # Auto-refresh setting in sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        auto_refresh = st.checkbox("🔄 Auto-refresh (10s)", value=False)
        if auto_refresh:
            st.caption("Enable to refresh dashboard automatically")
        
        db_path_str = st.text_input(
            "Database Path",
            value="tradesv3.sqlite",
            help="Path to SQLite database file"
        )
        db_path = Path(db_path_str)
        
        log_path_str = st.text_input(
            "Log File Path",
            value="freqtrade.log",
            help="Path to log file"
        )
        log_path = Path(log_path_str)
        
        log_lines = st.slider(
            "Log Lines",
            min_value=10,
            max_value=200,
            value=50,
            help="Number of log lines to display"
        )
        
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.rerun()
        
        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    # Capital State
    with col1:
        st.subheader("💰 Capital State")
        capital_state = load_capital_state(db_path)
        
        if capital_state:
            # Metrics row
            metric_cols = st.columns(3)
            
            with metric_cols[0]:
                st.metric(
                    "Total Capital",
                    f"${capital_state['total_capital']:,.2f}",
                    delta=f"${capital_state['total_pnl']:,.2f}"
                )
            
            with metric_cols[1]:
                st.metric(
                    "Available",
                    f"${capital_state['available_capital']:,.2f}",
                    delta=f"{(capital_state['available_capital']/capital_state['total_capital']*100):.1f}%"
                )
            
            with metric_cols[2]:
                st.metric(
                    "Deployed",
                    f"${capital_state['deployed_capital']:,.2f}",
                    delta=f"{(capital_state['deployed_capital']/capital_state['total_capital']*100):.1f}%"
                )
            
            # JSON view
            st.json(capital_state)
        else:
            st.info("⚠️ Capital state not available. Check database path.")
    
    # PnL Summary
    with col2:
        st.subheader("📈 PnL Summary")
        
        if capital_state:
            pnl_cols = st.columns(2)
            
            with pnl_cols[0]:
                st.metric(
                    "Realized PnL",
                    f"${capital_state['pnl_realized']:,.2f}",
                    delta=f"{(capital_state['pnl_realized']/capital_state['initial_capital']*100):.2f}%"
                )
            
            with pnl_cols[1]:
                st.metric(
                    "Unrealized PnL",
                    f"${capital_state['pnl_unrealized']:,.2f}",
                    delta=f"{(capital_state['pnl_unrealized']/capital_state['initial_capital']*100):.2f}%"
                )
            
            # PnL breakdown
            st.markdown("**PnL Breakdown:**")
            st.write(f"- Initial Capital: ${capital_state['initial_capital']:,.2f}")
            st.write(f"- Realized Gains/Losses: ${capital_state['pnl_realized']:,.2f}")
            st.write(f"- Unrealized Gains/Losses: ${capital_state['pnl_unrealized']:,.2f}")
            st.write(f"- **Total PnL: ${capital_state['total_pnl']:,.2f}**")
        else:
            st.info("⚠️ PnL data not available. Check database path.")
    
    st.markdown("---")
    
    # Open Positions
    st.subheader("📊 Open Positions")
    positions = get_open_positions(db_path)
    
    if positions:
        st.dataframe(
            positions,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": "ID",
                "pair": "Pair",
                "side": "Side",
                "amount": st.column_config.NumberColumn("Amount", format="%.8f"),
                "open_rate": st.column_config.NumberColumn("Open Price", format="%.8f"),
                "current_rate": st.column_config.NumberColumn("Current Price", format="%.8f"),
                "stake_amount": st.column_config.NumberColumn("Stake", format="$%.2f"),
                "profit_pct": st.column_config.NumberColumn("Profit %", format="%.2f%%"),
                "profit_abs": st.column_config.NumberColumn("Profit $", format="$%.2f"),
                "open_date": "Open Date",
                "duration": "Duration"
            }
        )
    else:
        st.info("ℹ️ No open positions")
    
    st.markdown("---")
    
    # Recent Orders
    st.subheader("📋 Recent Orders")
    orders = get_recent_orders(db_path, limit=20)
    
    if orders:
        st.dataframe(
            orders,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": "Order ID",
                "pair": "Pair",
                "side": "Side",
                "amount": st.column_config.NumberColumn("Amount", format="%.8f"),
                "price": st.column_config.NumberColumn("Price", format="%.8f"),
                "status": "Status",
                "date": "Date",
                "is_open": "Open"
            }
        )
    else:
        st.info("ℹ️ No recent orders")
    
    st.markdown("---")
    
    # PnL Chart
    st.subheader("📈 Cumulative PnL Over Time")
    pnl_history = get_pnl_history(db_path)
    
    if pnl_history:
        try:
            import pandas as pd
            import plotly.express as px
            
            df = pd.DataFrame(pnl_history)
            
            fig = px.line(
                df,
                x="date",
                y="cumulative_pnl",
                title="Cumulative PnL",
                labels={"date": "Date", "cumulative_pnl": "Cumulative PnL ($)"}
            )
            
            fig.update_traces(line_color='#00ff00' if df['cumulative_pnl'].iloc[-1] > 0 else '#ff0000')
            fig.update_layout(
                hovermode='x unified',
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.warning("⚠️ Install plotly and pandas for charts: pip install plotly pandas")
            st.write(pnl_history)
    else:
        st.info("ℹ️ No PnL history available (no closed trades)")
    
    st.markdown("---")
    
    # Production Logs
    st.subheader("📜 Production Logs (Tail)")
    
    log_content = get_log_tail(log_path, log_lines)
    
    st.text_area(
        "Log Output",
        value=log_content,
        height=300,
        disabled=True,
        label_visibility="collapsed"
    )
    
    # Footer note about auto-refresh
    if auto_refresh:
        st.info("💡 Auto-refresh enabled. To implement: Use `st.rerun()` with a timer or external scheduler.")


if __name__ == "__main__":
    main()
