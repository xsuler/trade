# config/config.py

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(BASE_DIR, '..', 'quant_trading_system.log')
PORTFOLIO_FILE = os.path.join(BASE_DIR, '..', 'portfolio.json')
BACKTRACE_FILE = os.path.join(BASE_DIR, '..', 'backtest_result.json')  # 确认路径

INITIAL_CASH = 100000

# 交易成本配置
TRANSACTION_COST_RATE = 0.001  # 交易成本百分比，例如 0.1%
SLIPPAGE_RATE = 0.0005  # 滑点百分比，例如 0.05%

# 策略配置及其权重
STRATEGY_CONFIGS = [
    {
        'name': 'MovingAverageCrossover',
        'weight': 0.6,  # 策略权重
        'params': {
            'short_window': 5,
            'long_window': 20,
            'buy_pct': 0.1,
            'sell_pct': 0.5
        }
    },
    {
        'name': 'RSI',
        'weight': 0.4,  # 策略权重
        'params': {
            'window': 14,
            'overbought': 70,
            'oversold': 30,
            'buy_pct': 0.05,
            'sell_pct': 0.3
        }
    }
]