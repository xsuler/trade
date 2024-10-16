# strategies/ma_crossover_strategy.py

import pandas as pd
from collections import OrderedDict
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
        """
        计算短期和长期移动平均线并生成信号
        """
        data['MA_Short'] = data['close'].rolling(window=self.short_window).mean()
        data['MA_Long'] = data['close'].rolling(window=self.long_window).mean()
        data['Signal'] = 0
        data['Signal'] = np.where(data['MA_Short'] > data['MA_Long'], 1, -1)
        data['Position'] = data['Signal'].diff()
        return data

    def decide_trade(self, data: Dict[str, pd.DataFrame], portfolio, price_time_series: Dict[str, OrderedDict]) -> Tuple[List[Dict], List[Dict]]:
        """
        根据移动平均交叉策略决定买卖操作
        """
        trades_buy = []
        trades_sell = []

        for symbol, df in data.items():
            signals = self.generate_signals(df)
            latest = signals.iloc[-1]

            if 'symbol' not in df.columns:
                logging.warning(f"Symbol 信息缺失，跳过 MA 交易决策。")
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
            if len(symbol_price_time_series) >= self.long_window:
                recent_prices = list(symbol_price_time_series.values())[-self.long_window:]
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
                budget = portfolio.cash * adjusted_buy_pct
                quantity = int(budget // current_price)
                if quantity > 0:
                    trades_buy.append({
                        'symbol': symbol,
                        'price': current_price,
                        'quantity': quantity
                    })
                    logging.info(f"MA 交叉策略生成买入信号：{symbol}，价格：{current_price}，数量：{quantity}")

            # 生成卖出信号
            elif latest['Position'] == -1 and symbol in portfolio.holdings:
                quantity = int(portfolio.holdings[symbol] * adjusted_sell_pct)
                if quantity > 0:
                    trades_sell.append({
                        'symbol': symbol,
                        'price': current_price,
                        'quantity': quantity
                    })
                    logging.info(f"MA 交叉策略生成卖出信号：{symbol}，价格：{current_price}，数量：{quantity}")

        return trades_buy, trades_sell