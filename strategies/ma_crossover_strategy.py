# strategies/ma_crossover_strategy.py

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict
from .base_strategy import BaseStrategy
import logging

class MovingAverageCrossoverStrategy(BaseStrategy):
    def __init__(self, short_window: int = 5, long_window: int = 20, buy_pct: float = 0.1, sell_pct: float = 0.5):
        self.short_window = short_window
        self.long_window = long_window
        self.buy_pct = buy_pct  # 买入资金比例
        self.sell_pct = sell_pct  # 卖出持仓比例

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data['MA_Short'] = data['close'].rolling(window=self.short_window).mean()
        data['MA_Long'] = data['close'].rolling(window=self.long_window).mean()
        data['Signal'] = 0
        data['Signal'] = np.where(data['MA_Short'] > data['MA_Long'], 1, -1)
        data['Position'] = data['Signal'].diff()
        return data

    def decide_trade(self, data: pd.DataFrame, portfolio) -> Tuple[List[Dict], List[Dict]]:
        signals = self.generate_signals(data)
        latest = signals.iloc[-1]
        trades_buy = []
        trades_sell = []
        symbol = latest['symbol']

        if latest['Position'] == 1:
            current_price = portfolio.data_fetcher.fetch_current_price(symbol)
            if current_price > 0:
                budget = portfolio.cash * self.buy_pct
                quantity = int(budget // current_price)
                if quantity > 0:
                    trades_buy.append({
                        'symbol': symbol,
                        'price': current_price,
                        'quantity': quantity
                    })

        elif latest['Position'] == -1 and symbol in portfolio.holdings:
            current_price = portfolio.data_fetcher.fetch_current_price(symbol)
            if current_price > 0:
                quantity = int(portfolio.holdings[symbol] * self.sell_pct)
                if quantity > 0:
                    trades_sell.append({
                        'symbol': symbol,
                        'price': current_price,
                        'quantity': quantity
                    })

        return trades_buy, trades_sell
