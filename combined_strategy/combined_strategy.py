# combined_strategy/combined_strategy.py

import pandas as pd
from typing import List, Tuple, Dict
from strategies.base_strategy import BaseStrategy

class CombinedStrategy(BaseStrategy):
    def __init__(self, strategies: List[BaseStrategy]):
        self.strategies = strategies

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        for strategy in self.strategies:
            data = strategy.generate_signals(data)
        return data

    def decide_trade(self, data: pd.DataFrame, portfolio) -> Tuple[List[Dict], List[Dict]]:
        all_buy_trades = []
        all_sell_trades = []
        for strategy in self.strategies:
            buy_trades, sell_trades = strategy.decide_trade(data.copy(), portfolio)
            all_buy_trades.extend(buy_trades)
            all_sell_trades.extend(sell_trades)
        return all_buy_trades, all_sell_trades
