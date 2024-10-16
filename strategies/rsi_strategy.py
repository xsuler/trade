# strategies/rsi_strategy.py

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict
from .base_strategy import BaseStrategy
import logging

class RSIStrategy(BaseStrategy):
    def __init__(self, window: int = 14, overbought: float = 70, oversold: float = 30, buy_pct: float = 0.05, sell_pct: float = 0.3):
        self.window = window
        self.overbought = overbought
        self.oversold = oversold
        self.buy_pct = buy_pct
        self.sell_pct = sell_pct

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.window).mean()
        RS = gain / loss
        data['RSI'] = 100 - (100 / (1 + RS))
        data['Signal'] = 0
        data['Signal'] = np.where(data['RSI'] > self.overbought, -1, np.where(data['RSI'] < self.oversold, 1, 0))
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
