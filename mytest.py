# -*- coding: utf-8 -*-
"""
@Time ： 2024/12/3 下午5:57
@Author ： Jinbo CHEN
@File ：mytest.py
"""

from freqtrade.commands import Arguments, start_test_pairlist, start_download_data, start_backtesting, start_hyperopt, \
        start_lookahead_analysis
from freqtrade.commands.trade_commands import start_trading
from freqtrade.loggers import setup_logging_pre
from freqtrade.system import asyncio_setup

setup_logging_pre()
asyncio_setup()


def get_args(args):
    return Arguments(args).get_parsed_arg()


# 运行策略
args = ['trade',
        '-c', 'user_data/config_test.json',
        '--db-url', 'sqlite:///user_data/trade_test_live_bd70.sqlite',
        '--strategy', 'BD70Strategy',
        '--logfile', './logs1']
start_trading(get_args(args))

# # 运行freqai策略
# args = ['trade',
#         '-c', 'user_data/config_freqai.example.json',
#         '--strategy', 'FreqaiExampleStrategy',
#         '--freqaimodel', 'LightGBMRegressor']
# start_trading(get_args(args))


# # 生成交易对列表
# args = ['test-pairlist',
#         '-c', 'user_data/config.json',
#         '--quote', 'USDT',
#         '--print-json']
# start_test_pairlist(get_args(args))


# # 下载数据
# args = ['download-data',
#         '-c', 'user_data/config.json',
#         '--days', '90',
#         '--timeframes', '5m', '1h']
# start_download_data(get_args(args))

# 回测
# args = ['backtesting',
#         '-c', 'user_data/config_test.json',
#         '--strategy', 'MFLsdca',
#         '--timeframe', '5m',
#         '--timerange=20241105-20241205',
#         '--breakdown', 'day', 'week', 'month',
#         # '--enable-protections',
#         '--cache', 'none']
# start_backtesting(get_args(args))


# # 参数优化
# args = ['hyperopt',
#         '--hyperopt-loss', 'SharpHyperOptLoss',
#         '--strategy', 'EMAStrategy',
#         '--spaces', 'roi', 'stoploss', 'trailing', 'buy',
#         '-c', 'user_data/config_test.json',
#         '--timerange=20240910-20241010',
#         '-e', '100']
# start_hyperopt(get_args(args))


# # 前瞻性分析
# args = ['lookahead-analysis',
#         '-c', 'user_data/config_test.json',
#         '--strategy', 'EMAStrategy',
#         '--timerange=20241011-20241211',
#         '--enable-protections']
# start_lookahead_analysis(get_args(args))
