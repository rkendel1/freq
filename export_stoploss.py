import pandas as pd

from freqtrade.configuration import Configuration
from freqtrade.optimize.backtesting import Backtesting
from freqtrade.resolvers import StrategyResolver

# 1. Load config
config = Configuration.from_files(["user_data/config.json"])
config["runmode"] = "backtesting"
config["strategy"] = "CeZlsmStrategy"

# 2. Init Backtester
bt = Backtesting(config)

# 3. Load data + timerange
data, timerange = bt.load_bt_data()
print(f"Backtest range: {timerange.startdt} → {timerange.stopdt}")

# 4. Load Strategy
strategy = StrategyResolver.load_strategy(config)

# 5. Run Backtest — 正确调用方式
results = bt.backtest(data, strategy, timerange.stopdt)

# 6. Extract stop‑loss trades
records = []
for t in results.trades:
    if t.exit_reason == "stop_loss":
        records.append({
            "trade_id": t.trade_id,
            "pair": t.pair,
            "open_date": t.open_date,
            "close_date": t.close_date,
            "open_rate": t.open_rate,
            "close_rate": t.close_rate,
            "stoploss_price": t.stop_loss,
            "profit_ratio": t.close_profit,
        })

df = pd.DataFrame(records)
df.to_csv("stoploss_records.csv", index=False)
print(f"Stoploss records saved to stoploss_records.csv ({len(df)} rows)")
