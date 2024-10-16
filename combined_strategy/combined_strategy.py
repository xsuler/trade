# combined_strategy/combined_strategy.py

import pandas as pd
from typing import List, Dict, Tuple
from collections import OrderedDict
from strategies.base_strategy import BaseStrategy
from price_time_series_manager import PriceTimeSeriesManager
from config.config import STRATEGY_CONFIGS

class CombinedStrategy:
    def __init__(self, strategies: List[BaseStrategy]):
        """
        初始化组合策略。

        :param strategies: 子策略列表
        """
        self.strategies = strategies
        self.price_manager = PriceTimeSeriesManager()  # 初始化管理器

    def decide_trade(self, data: Dict[str, pd.DataFrame], portfolio, price_time_series: Dict[str, OrderedDict]) -> Tuple[List[Dict], List[Dict]]:
        """
        聚合所有子策略的买入和卖出交易，考虑策略权重。

        :param data: 所有股票的数据字典，键为股票代码，值为对应的DataFrame
        :param portfolio: 当前的投资组合
        :param price_time_series: 各股票的价格时序数据
        :return: (买入交易列表, 卖出交易列表)
        """
        buy_trades_dict = {}
        sell_trades_dict = {}

        for strategy in self.strategies:
            trades_buy, trades_sell = strategy.decide_trade(data, portfolio, price_time_series)
            strategy_weight = strategy.weight

            for trade in trades_buy:
                trade_symbol = trade['symbol']
                weighted_quantity = int(trade['quantity'] * strategy_weight)
                if trade_symbol in buy_trades_dict:
                    buy_trades_dict[trade_symbol]['quantity'] += weighted_quantity
                    buy_trades_dict[trade_symbol]['price'] = (buy_trades_dict[trade_symbol]['price'] + trade['price']) / 2
                else:
                    buy_trades_dict[trade_symbol] = {
                        'symbol': trade_symbol,
                        'price': trade['price'],
                        'quantity': weighted_quantity
                    }

            for trade in trades_sell:
                trade_symbol = trade['symbol']
                weighted_quantity = int(trade['quantity'] * strategy_weight)
                if trade_symbol in sell_trades_dict:
                    sell_trades_dict[trade_symbol]['quantity'] += weighted_quantity
                    sell_trades_dict[trade_symbol]['price'] = (sell_trades_dict[trade_symbol]['price'] + trade['price']) / 2
                else:
                    sell_trades_dict[trade_symbol] = {
                        'symbol': trade_symbol,
                        'price': trade['price'],
                        'quantity': weighted_quantity
                    }

        # 转换为列表形式
        merged_buy_trades = list(buy_trades_dict.values())
        merged_sell_trades = list(sell_trades_dict.values())

        return merged_buy_trades, merged_sell_trades