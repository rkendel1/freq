"""
Production Configuration Dashboard - Streamlit UI for managing config.prod.json

This is a secure interface for managing production configuration:
- Dynamic ExploitModule discovery and multi-select
- Full CCXT exchange list (supports CEX + DEX like Hyperliquid)
- Risk limits, capital, and API credentials input
- Basic validation and save functionality
- Simple environment-based password protection

Run with:
    STREAMLIT_PASSWORD=your_password streamlit run freqtrade/ui/prod_config.py

Access at:
    http://localhost:8501
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st

# Add freqtrade to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def check_password() -> bool:
    """Check if password is correct."""
    required_password = os.environ.get("STREAMLIT_PASSWORD", "")
    
    if not required_password:
        st.warning("⚠️ STREAMLIT_PASSWORD environment variable not set. Dashboard is unsecured!")
        return True
    
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    
    if st.session_state.password_correct:
        return True
    
    password = st.text_input("🔒 Enter Password", type="password", key="password_input")
    
    if st.button("Login"):
        if password == required_password:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ Incorrect password")
    
    return False


def discover_exploit_modules() -> list[str]:
    """Discover available ExploitModule implementations."""
    try:
        # Get exploits directory relative to this file
        exploits_dir = Path(__file__).parent.parent / "exploits"
        
        if not exploits_dir.exists():
            st.warning(f"⚠️ Exploits directory not found at: {exploits_dir}")
            return []
        
        modules = []
        
        for file in exploits_dir.glob("*.py"):
            if file.name.startswith("_") or file.name == "exploit_module.py":
                continue
            module_name = file.stem
            modules.append(module_name)
        
        return sorted(modules)
    except Exception as e:
        st.error(f"❌ Error discovering exploit modules: {e}")
        return []


def get_ccxt_exchanges() -> list[str]:
    """Get list of all CCXT-supported exchanges."""
    try:
        import ccxt
        return sorted(ccxt.exchanges)
    except ImportError:
        st.warning("⚠️ CCXT not installed. Install with: pip install ccxt")
        return ["binance", "bybit", "hyperliquid", "okx", "kraken", "kucoin"]


def load_config(config_path: Path) -> dict[str, Any]:
    """Load existing config or return default."""
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    
    # Default config
    return {
        "max_open_trades": 3,
        "stake_currency": "USDT",
        "stake_amount": "unlimited",
        "tradable_balance_ratio": 0.99,
        "fiat_display_currency": "USD",
        "dry_run": True,
        "initial_capital": 10000.0,
        "exploit_modules": [],
        "exchange": {
            "name": "binance",
            "key": "",
            "secret": "",
            "ccxt_config": {},
            "ccxt_async_config": {},
            "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
            "pair_blacklist": []
        },
        "risk_limits": {
            "max_position_size": 0.2,
            "max_total_exposure": 0.8,
            "max_open_positions": 3,
            "max_loss_per_trade": 0.1,
            "max_daily_loss": 0.2,
            "position_cooldown": 0
        },
        "entry_pricing": {
            "price_side": "same",
            "use_order_book": True,
            "order_book_top": 1
        },
        "exit_pricing": {
            "price_side": "same",
            "use_order_book": True,
            "order_book_top": 1
        },
        "pairlists": [{"method": "StaticPairList"}],
        "bot_name": "freqtrade_prod",
        "initial_state": "running"
    }


def save_config(config: dict[str, Any], config_path: Path) -> None:
    """Save config to file."""
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate configuration and return list of errors."""
    errors = []
    
    # Check required fields
    if not config.get("stake_currency"):
        errors.append("Stake currency is required")
    
    if config.get("initial_capital", 0) <= 0:
        errors.append("Initial capital must be greater than 0")
    
    # Validate exchange
    exchange = config.get("exchange", {})
    if not exchange.get("name"):
        errors.append("Exchange name is required")
    
    # Validate risk limits
    risk = config.get("risk_limits", {})
    if risk.get("max_position_size", 0) > 1.0:
        errors.append("Max position size cannot exceed 100% (1.0)")
    
    if risk.get("max_total_exposure", 0) > 1.0:
        errors.append("Max total exposure cannot exceed 100% (1.0)")
    
    return errors


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Production Config Dashboard",
        page_icon="⚙️",
        layout="wide"
    )
    
    # Password protection
    if not check_password():
        return
    
    st.title("⚙️ Production Configuration Dashboard")
    st.markdown("---")
    
    # Config file path
    config_path = Path(__file__).parent.parent.parent / "config.prod.json"
    
    # Load config
    if "config" not in st.session_state:
        st.session_state.config = load_config(config_path)
    
    config = st.session_state.config
    
    # Sidebar - Save/Load controls
    with st.sidebar:
        st.header("📁 File Operations")
        
        if st.button("💾 Save Configuration", type="primary", use_container_width=True):
            errors = validate_config(config)
            if errors:
                st.error("❌ Validation failed:")
                for error in errors:
                    st.error(f"  • {error}")
            else:
                save_config(config, config_path)
                st.success(f"✅ Saved to {config_path.name}")
        
        if st.button("🔄 Reload from File", use_container_width=True):
            st.session_state.config = load_config(config_path)
            st.rerun()
        
        if st.button("🔴 Reset to Defaults", use_container_width=True):
            st.session_state.config = load_config(Path("nonexistent"))
            st.rerun()
        
        st.markdown("---")
        st.caption(f"Config file: `{config_path.name}`")
    
    # Main content - Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 Capital & Basic",
        "🔌 Exchange",
        "🛡️ Risk Limits",
        "🎯 Exploit Modules",
        "📋 Raw JSON"
    ])
    
    # Tab 1: Capital & Basic Settings
    with tab1:
        st.header("💰 Capital & Basic Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            config["initial_capital"] = st.number_input(
                "Initial Capital",
                min_value=0.0,
                value=float(config.get("initial_capital", 10000.0)),
                step=1000.0,
                help="Starting capital amount"
            )
            
            config["stake_currency"] = st.text_input(
                "Stake Currency",
                value=config.get("stake_currency", "USDT"),
                help="Base currency for trading (e.g., USDT, USD, BTC)"
            )
            
            config["fiat_display_currency"] = st.text_input(
                "Fiat Display Currency",
                value=config.get("fiat_display_currency", "USD"),
                help="Currency for display purposes"
            )
        
        with col2:
            config["dry_run"] = st.checkbox(
                "Dry Run Mode",
                value=config.get("dry_run", True),
                help="Enable for paper trading (no real orders)"
            )
            
            config["max_open_trades"] = st.number_input(
                "Max Open Trades",
                min_value=1,
                max_value=100,
                value=config.get("max_open_trades", 3),
                help="Maximum number of concurrent positions"
            )
            
            config["bot_name"] = st.text_input(
                "Bot Name",
                value=config.get("bot_name", "freqtrade_prod"),
                help="Identifier for this bot instance"
            )
    
    # Tab 2: Exchange Configuration
    with tab2:
        st.header("🔌 Exchange Configuration")
        
        if "exchange" not in config:
            config["exchange"] = {}
        
        exchange = config["exchange"]
        
        # Exchange selection
        ccxt_exchanges = get_ccxt_exchanges()
        current_exchange = exchange.get("name", "binance")
        
        if current_exchange not in ccxt_exchanges:
            ccxt_exchanges.insert(0, current_exchange)
        
        exchange["name"] = st.selectbox(
            "Exchange",
            options=ccxt_exchanges,
            index=ccxt_exchanges.index(current_exchange) if current_exchange in ccxt_exchanges else 0,
            help="Select exchange (CEX or DEX supported via CCXT)"
        )
        
        st.info(f"📊 Selected: **{exchange['name']}** — Supports CEX and DEX venues via CCXT")
        
        # API Credentials
        st.subheader("🔑 API Credentials")
        
        col1, col2 = st.columns(2)
        
        with col1:
            exchange["key"] = st.text_input(
                "API Key",
                value=exchange.get("key", ""),
                type="password",
                help="Exchange API key"
            )
        
        with col2:
            exchange["secret"] = st.text_input(
                "API Secret",
                value=exchange.get("secret", ""),
                type="password",
                help="Exchange API secret"
            )
        
        # Trading Pairs
        st.subheader("📈 Trading Pairs")
        
        whitelist_str = st.text_area(
            "Pair Whitelist (one per line)",
            value="\n".join(exchange.get("pair_whitelist", ["BTC/USDT", "ETH/USDT"])),
            height=100,
            help="Allowed trading pairs"
        )
        exchange["pair_whitelist"] = [p.strip() for p in whitelist_str.split("\n") if p.strip()]
        
        blacklist_str = st.text_area(
            "Pair Blacklist (one per line)",
            value="\n".join(exchange.get("pair_blacklist", [])),
            height=100,
            help="Excluded trading pairs"
        )
        exchange["pair_blacklist"] = [p.strip() for p in blacklist_str.split("\n") if p.strip()]
    
    # Tab 3: Risk Limits
    with tab3:
        st.header("🛡️ Risk Limits")
        
        if "risk_limits" not in config:
            config["risk_limits"] = {}
        
        risk = config["risk_limits"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            risk["max_position_size"] = st.slider(
                "Max Position Size (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(risk.get("max_position_size", 0.2) * 100),
                step=1.0,
                help="Maximum % of capital per position"
            ) / 100.0
            
            risk["max_total_exposure"] = st.slider(
                "Max Total Exposure (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(risk.get("max_total_exposure", 0.8) * 100),
                step=1.0,
                help="Maximum % of capital deployed across all positions"
            ) / 100.0
            
            risk["max_open_positions"] = st.number_input(
                "Max Open Positions",
                min_value=1,
                max_value=100,
                value=risk.get("max_open_positions", 3),
                help="Maximum number of concurrent positions"
            )
        
        with col2:
            risk["max_loss_per_trade"] = st.slider(
                "Max Loss Per Trade (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(risk.get("max_loss_per_trade", 0.1) * 100),
                step=1.0,
                help="Maximum acceptable loss per trade"
            ) / 100.0
            
            risk["max_daily_loss"] = st.slider(
                "Max Daily Loss (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(risk.get("max_daily_loss", 0.2) * 100),
                step=1.0,
                help="Maximum acceptable daily loss"
            ) / 100.0
            
            risk["position_cooldown"] = st.number_input(
                "Position Cooldown (seconds)",
                min_value=0,
                max_value=3600,
                value=risk.get("position_cooldown", 0),
                help="Minimum time between trades on same symbol"
            )
    
    # Tab 4: Exploit Modules
    with tab4:
        st.header("🎯 Exploit Modules")
        
        st.info("💡 Select which ExploitModules to run. Modules are fully independent and can be combined in any way.")
        
        available_modules = discover_exploit_modules()
        
        if not available_modules:
            st.warning("⚠️ No ExploitModules found in freqtrade/exploits/")
        else:
            current_modules = config.get("exploit_modules", [])
            
            selected_modules = st.multiselect(
                "Active Exploit Modules",
                options=available_modules,
                default=[m for m in current_modules if m in available_modules],
                help="Select one or more modules to run. Zero modules = NullExploitModule (engine does nothing)"
            )
            
            config["exploit_modules"] = selected_modules
            
            # Show module details
            if selected_modules:
                st.success(f"✅ **{len(selected_modules)} module(s) selected**")
                for module in selected_modules:
                    st.code(f"freqtrade.exploits.{module}")
            else:
                st.warning("⚠️ No modules selected → NullExploitModule (engine will not trade)")
    
    # Tab 5: Raw JSON
    with tab5:
        st.header("📋 Raw JSON Configuration")
        
        st.info("⚠️ Advanced: Edit raw JSON directly. Changes here override other tabs.")
        
        json_str = st.text_area(
            "Configuration JSON",
            value=json.dumps(config, indent=2),
            height=600,
            help="Raw JSON configuration"
        )
        
        if st.button("Apply JSON Changes"):
            try:
                new_config = json.loads(json_str)
                st.session_state.config = new_config
                st.success("✅ JSON applied successfully")
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {e}")
    
    # Footer
    st.markdown("---")
    st.caption("🔒 Production Configuration Dashboard | Environment-based password protection")


if __name__ == "__main__":
    main()
