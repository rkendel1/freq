# File Deletion List - Complete Reference

This document lists all files that have been deleted during the refactoring.

## Deleted Modules (Complete Directories)

### FreqAI (ML/AI System)
```
freqtrade/freqai/
├── RL/
│   ├── Base3ActionRLEnv.py
│   ├── Base4ActionRLEnv.py
│   ├── Base5ActionRLEnv.py
│   ├── BaseEnvironment.py
│   ├── BaseReinforcementLearningModel.py
│   └── __init__.py
├── base_models/
│   ├── BaseClassifierModel.py
│   ├── BasePyTorchClassifier.py
│   ├── BasePyTorchModel.py
│   ├── BasePyTorchRegressor.py
│   ├── BaseRegressionModel.py
│   ├── FreqaiMultiOutputClassifier.py
│   └── FreqaiMultiOutputRegressor.py
├── prediction_models/
│   ├── LightGBMClassifier.py
│   ├── LightGBMClassifierMultiTarget.py
│   ├── LightGBMRegressor.py
│   ├── LightGBMRegressorMultiTarget.py
│   ├── PyTorchMLPClassifier.py
│   ├── PyTorchMLPRegressor.py
│   ├── PyTorchTransformerRegressor.py
│   ├── ReinforcementLearner.py
│   ├── ReinforcementLearner_multiproc.py
│   ├── SKLearnRandomForestClassifier.py
│   ├── XGBoostClassifier.py
│   ├── XGBoostRFClassifier.py
│   ├── XGBoostRFRegressor.py
│   ├── XGBoostRegressor.py
│   ├── XGBoostRegressorMultiTarget.py
│   └── __init__.py
├── tensorboard/
│   ├── TensorboardCallback.py
│   ├── __init__.py
│   ├── base_tensorboard.py
│   └── tensorboard.py
├── torch/
│   ├── PyTorchDataConvertor.py
│   ├── PyTorchMLPModel.py
│   ├── PyTorchModelTrainer.py
│   ├── PyTorchTrainerInterface.py
│   ├── PyTorchTransformerModel.py
│   ├── __init__.py
│   └── datasets.py
├── __init__.py
├── data_drawer.py
├── data_kitchen.py
├── freqai_interface.py
└── utils.py
```

### RPC (API/Telegram/WebSocket)
```
freqtrade/rpc/
├── api_server/
│   ├── ws/
│   │   ├── __init__.py
│   │   ├── channel.py
│   │   ├── message_stream.py
│   │   ├── proxy.py
│   │   ├── serializer.py
│   │   └── ws_types.py
│   ├── ui/
│   │   ├── fallback_file.html
│   │   ├── favicon.ico
│   │   └── installed/.gitkeep
│   ├── __init__.py
│   ├── api_auth.py
│   ├── api_background_tasks.py
│   ├── api_backtest.py
│   ├── api_download_data.py
│   ├── api_pair_history.py
│   ├── api_pairlists.py
│   ├── api_schemas.py
│   ├── api_v1.py
│   ├── api_ws.py
│   ├── deps.py
│   ├── uvicorn_threaded.py
│   ├── web_ui.py
│   ├── webserver.py
│   ├── webserver_bgwork.py
│   └── ws_schemas.py
├── __init__.py
├── discord.py
├── external_message_consumer.py
├── fiat_convert.py
├── rpc.py
├── rpc_manager.py
├── rpc_types.py
├── telegram.py
└── webhook.py
```

### Plotting
```
freqtrade/plot/
├── __init__.py
└── plotting.py
```

### Hyperopt (Optimization)
```
freqtrade/optimize/hyperopt/
├── __init__.py
├── hyperopt.py
├── hyperopt_auto.py
├── hyperopt_interface.py
├── hyperopt_logger.py
├── hyperopt_optimizer.py
└── hyperopt_output.py

freqtrade/optimize/hyperopt_loss/
├── hyperopt_loss_calmar.py
├── hyperopt_loss_interface.py
├── hyperopt_loss_max_drawdown.py
├── hyperopt_loss_max_drawdown_per_pair.py
├── hyperopt_loss_max_drawdown_relative.py
├── hyperopt_loss_multi_metric.py
├── hyperopt_loss_onlyprofit.py
├── hyperopt_loss_profit_drawdown.py
├── hyperopt_loss_sharpe.py
├── hyperopt_loss_sharpe_daily.py
├── hyperopt_loss_short_trade_dur.py
├── hyperopt_loss_sortino.py
└── hyperopt_loss_sortino_daily.py

freqtrade/optimize/space/
├── __init__.py
├── decimalspace.py
└── optunaspaces.py

freqtrade/optimize/
├── hyperopt_epoch_filters.py
└── hyperopt_tools.py
```

### Analysis Tools
```
freqtrade/optimize/analysis/
├── __init__.py
├── base_analysis.py
├── lookahead.py
├── lookahead_helpers.py
├── recursive.py
└── recursive_helpers.py
```

### Strategy Templates
```
freqtrade/templates/
├── strategy_subtemplates/
│   ├── buy_trend_full.j2
│   ├── buy_trend_minimal.j2
│   ├── indicators_full.j2
│   ├── indicators_minimal.j2
│   ├── plot_config_full.j2
│   ├── plot_config_minimal.j2
│   ├── sell_trend_full.j2
│   ├── sell_trend_minimal.j2
│   ├── strategy_attributes_full.j2
│   ├── strategy_attributes_minimal.j2
│   ├── strategy_methods_advanced.j2
│   └── strategy_methods_empty.j2
├── subtemplates/
│   ├── exchange_binance.j2
│   ├── exchange_bittrex.j2
│   ├── exchange_gateio.j2
│   ├── exchange_generic.j2
│   ├── exchange_huobi.j2
│   ├── exchange_kraken.j2
│   ├── exchange_kucoin.j2
│   └── exchange_okex.j2
├── FreqaiExampleHybridStrategy.py
├── FreqaiExampleStrategy.py
├── __init__.py
├── base_config.json.j2
├── base_strategy.py.j2
├── sample_hyperopt_loss.py
├── sample_strategy.py
└── strategy_analysis_example.ipynb
```

### Commands
```
freqtrade/commands/
├── analyze_commands.py
├── deploy_ui.py
├── hyperopt_commands.py
├── pairlist_commands.py
├── plot_commands.py
└── webserver_commands.py
```

### Enums
```
freqtrade/enums/
└── rpcmessagetype.py
```

## Deleted Top-Level Directories

### Documentation
```
docs/ (entire directory with 100+ files)
```

### Scripts
```
scripts/
├── rest_client.py
└── ws_client.py
```

### Config Examples
```
config_examples/
├── config_binance.example.json
├── config_freqai.example.json
├── config_full.example.json
└── config_kraken.example.json
```

### User Data
```
user_data/
├── backtest_results/.gitkeep
├── data/.gitkeep
├── freqaimodels/.gitkeep
├── hyperopts/.gitkeep
├── logs/.gitkeep
└── notebooks/.gitkeep
```

### FreqTrade Client
```
ft_client/
├── freqtrade_client/
│   ├── __init__.py
│   ├── ft_client.py
│   └── ft_rest_client.py
├── test_client/
│   ├── __init__.py
│   └── test_rest_client.py
├── LICENSE
├── MANIFEST.in
├── README.md
├── pyproject.toml
└── requirements.txt
```

## Deleted Requirements Files

```
requirements-freqai-rl.txt
requirements-freqai.txt
requirements-hyperopt.txt
requirements-plot.txt
```

## Total Deletion Stats

- **Directories deleted:** ~15 major directories
- **Python files deleted:** ~300+ files  
- **Lines of code removed:** ~40,000+ lines
- **Documentation deleted:** ~140 markdown files
- **Config examples deleted:** 4 files

## What Remains

### Core Modules (Kept)
```
freqtrade/
├── core/ (NEW - execution infrastructure)
├── exploits/ (NEW - signal provider interface)
├── exchange/ (exchange abstraction)
├── persistence/ (database models)
├── data/ (data handling)
├── commands/ (minimal CLI)
├── configuration/ (config handling)
├── enums/ (type definitions)
├── leverage/ (futures support)
├── plugins/ (pairlist, protections)
├── resolvers/ (dynamic loading)
├── strategy/ (legacy - to be deprecated)
├── util/ (utilities)
└── optimize/backtesting.py (backtesting only)
```

### Estimated Reduction
- **Before:** ~38,000 lines of code
- **After:** ~15,000 lines of code (estimate)
- **Reduction:** ~60% of codebase removed

## Next Phase: What Still Needs Removal

1. RPC imports from remaining files:
   - freqtrade/freqtradebot.py (42 references)
   - freqtrade/worker.py
   - freqtrade/data/dataprovider.py

2. Strategy coupling (can be deprecated vs removed):
   - freqtrade/strategy/* (mark as deprecated)
   - Strategy imports in optimize/backtesting.py

3. Optional cleanup:
   - Dynamic pairlists (keep static only)
   - Old test files expecting deleted modules
   - Build helpers for deleted features
