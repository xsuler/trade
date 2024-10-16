# config/config.py

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(BASE_DIR, '..', 'quant_trading_system.log')
PORTFOLIO_FILE = os.path.join(BASE_DIR, '..', 'portfolio.json')
BACKTRACE_FILE = os.path.join(BASE_DIR, '..', 'backtest_result.json')  # 确认路径

INITIAL_CASH = 100000

STRATEGY_CONFIGS = [
    {
        'name': 'MovingAverageCrossover',
        'params': {
            'short_window': 5,
            'long_window': 20,
            'buy_pct': 0.1,
            'sell_pct': 0.5
        }
    },
    {
        'name': 'RSI',
        'params': {
            'window': 14,
            'overbought': 70,
            'oversold': 30,
            'buy_pct': 0.05,
            'sell_pct': 0.3
        }
    }
]