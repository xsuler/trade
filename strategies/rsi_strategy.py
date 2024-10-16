# strategies/rsi_strategy.py

import pandas as pd
import numpy as np
from collections import OrderedDict
from typing import List, Tuple, Dict
from .base_strategy import BaseStrategy
import logging

class RSIStrategy(BaseStrategy):
    def __init__(self, window: int = 14, overbought: float = 70, oversold: float = 30, buy_pct: float = 0.05, sell_pct: float = 0.3, weight: float = 1.0):
        super().__init__(weight)
        self.window = window
        self.overbought = overbought
        self.oversold = oversold
        self.buy_pct = buy_pct
        self.sell_pct = sell_pct

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算 RSI 指标并生成信号
        """
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.window).mean()
        RS = gain / loss
        data['RSI'] = 100 - (100 / (1 + RS))
        data['Signal'] = 0
        data['Signal'] = np.where(data['RSI'] > self.overbought, -1, np.where(data['RSI'] < self.oversold, 1, 0))
        data['Position'] = data['Signal'].diff()
        return data

    def decide_trade(self, data: Dict[str, pd.DataFrame], portfolio, price_time_series: Dict[str, OrderedDict]) -> Tuple[List[Dict], List[Dict]]:
        """
        根据 RSI 策略决定买卖操作
        """
        trades_buy = []
        trades_sell = []

        for symbol, df in data.items():
            signals = self.generate_signals(df)
            latest = signals.iloc[-1]

            if 'symbol' not in df.columns:
                logging.warning(f"Symbol 信息缺失，跳过 RSI 交易决策。")
                continue

            # 从 price_time_series 获取最新价格
            if symbol in price_time_series and len(price_time_series[symbol]) > 0:
                current_price = list(price_time_series[symbol].values())[-1]
            else:
                logging.warning(f"没有找到 {symbol} 的最新价格。")
                continue

            if not isinstance(current_price, (int, float)) or current_price <= 0:
                logging.warning(f"股票 {symbol} 的最新价格无效: {current_price}")
                continue

            # 使用统一的 price_time_series 来分析趋势
            symbol_price_time_series = price_time_series.get(symbol, OrderedDict())
            if len(symbol_price_time_series) >= self.window:
                recent_prices = list(symbol_price_time_series.values())[-self.window:]
                recent_trend = np.mean(np.diff(recent_prices))
                # 根据趋势调整买入或卖出比例
                if recent_trend > 0:
                    adjusted_buy_pct = self.buy_pct * 1.1  # 略微增加买入比例
                    adjusted_sell_pct = self.sell_pct * 0.9
                else:
                    adjusted_buy_pct = self.buy_pct * 0.9
                    adjusted_sell_pct = self.sell_pct * 1.1
            else:
                adjusted_buy_pct = self.buy_pct
                adjusted_sell_pct = self.sell_pct

            # 生成买入信号
            if latest['Position'] == 1:
                budget = portfolio.cash * adjusted_buy_pct * self.weight
                quantity = int(budget // current_price)
                if quantity > 0:
                    trades_buy.append({
                        'symbol': symbol,
                        'price': current_price,
                        'quantity': quantity
                    })
                    logging.info(f"RSI 策略生成买入信号：{symbol}，价格：{current_price}，数量：{quantity}")

            # 生成卖出信号
            elif latest['Position'] == -1 and symbol in portfolio.holdings:
                quantity = int(portfolio.holdings[symbol] * adjusted_sell_pct * self.weight)
                if quantity > 0:
                    trades_sell.append({
                        'symbol': symbol,
                        'price': current_price,
                        'quantity': quantity
                    })
                    logging.info(f"RSI 策略生成卖出信号：{symbol}，价格：{current_price}，数量：{quantity}")

        return trades_buy, trades_sell