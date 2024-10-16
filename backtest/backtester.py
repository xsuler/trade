# backtest/backtester.py

import logging
import pandas as pd
from typing import Dict
from portfolio.portfolio import Portfolio
from combined_strategy.combined_strategy import CombinedStrategy

class Backtester:
    def __init__(self, strategy: CombinedStrategy, data: Dict[str, pd.DataFrame]):
        self.strategy = strategy
        self.data = data
        self.results = {}

    def run_backtest(self):
        portfolio = Portfolio(initial_cash=100000, data_fetcher=None)  # 不需要数据获取器
        for symbol, df in self.data.items():
            try:
                buy_trades, sell_trades = self.strategy.decide_trade(df.copy(), portfolio)
                # 模拟买入
                for trade in buy_trades:
                    price = trade['price']
                    quantity = trade['quantity']
                    portfolio.buy_stock(trade['symbol'], price, quantity)
                # 模拟卖出
                for trade in sell_trades:
                    price = trade['price']
                    quantity = trade['quantity']
                    portfolio.sell_stock(trade['symbol'], price, quantity)
            except Exception as e:
                logging.error(f"处理 {symbol} 时出错: {e}")
        total_return = (portfolio.get_portfolio_value({}) - portfolio.initial_cash) / portfolio.initial_cash
        logging.info(f"回测总收益: {total_return * 100:.2f}%")
        self.results = {'total_return': total_return}
        return self.results
