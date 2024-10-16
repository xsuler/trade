# combined_strategy/combined_strategy.py

import pandas as pd
from typing import List, Tuple, Dict
from strategies.base_strategy import BaseStrategy
import logging

class CombinedStrategy(BaseStrategy):
    def __init__(self, strategies: List[BaseStrategy], top_n: int = 10):
        self.strategies = strategies
        self.top_n = top_n  # 要筛选的股票数量

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        # 综合所有策略生成信号
        for strategy in self.strategies:
            data = strategy.generate_signals(data)
        return data

    def decide_trade(self, data: Dict[str, pd.DataFrame], portfolio) -> Tuple[List[Dict], List[Dict]]:
        all_buy_trades = []
        all_sell_trades = []

        # 筛选依据：例如，根据最新价格排序，选择前 top_n 只股票
        # 您可以根据需求更改筛选逻辑，如成交量、市值等
        latest_prices = {}
        for symbol, df in data.items():
            if not df.empty:
                latest_prices[symbol] = df.iloc[-1]['close']
        
        # 如果最新价格为空，避免错误
        if not latest_prices:
            return all_buy_trades, all_sell_trades

        # 根据最新价格降序筛选前 top_n 只股票
        sorted_symbols = sorted(latest_prices.items(), key=lambda x: x[1], reverse=True)
        selected_symbols = [symbol for symbol, price in sorted_symbols[:self.top_n]]
        logging.info(f"Selected top {self.top_n} symbols based on latest price: {selected_symbols}")

        # 对选中的股票应用所有策略
        for symbol in selected_symbols:
            df = data.get(symbol)
            if df is not None and not df.empty:
                for strategy in self.strategies:
                    buy_trades, sell_trades = strategy.decide_trade(df.copy(), portfolio)
                    all_buy_trades.extend(buy_trades)
                    all_sell_trades.extend(sell_trades)

        return all_buy_trades, all_sell_trades
