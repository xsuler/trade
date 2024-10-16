# backtest/backtester.py

import os
import json
import logging
import pandas as pd
from typing import Dict
from portfolio.portfolio import Portfolio
from combined_strategy.combined_strategy import CombinedStrategy
from price_time_series_manager import PriceTimeSeriesManager
from datetime import datetime
from config.config import INITIAL_CASH, BACKTRACE_FILE

class Backtester:
    def __init__(self, strategy: CombinedStrategy, data: Dict[str, pd.DataFrame]):
        self.strategy = strategy
        self.data = data
        self.results = {}
        self.price_manager = PriceTimeSeriesManager()  # 初始化管理器

    def run_backtest(self):
        portfolio = Portfolio(initial_cash=INITIAL_CASH, data_fetcher=None)  # 确保使用相同的初始现金

        # 获取所有交易日期的排序列表
        all_dates = set()
        for df in self.data.values():
            all_dates.update(df['date'].dt.date)
        all_dates = sorted(list(all_dates))

        for current_date in all_dates:
            logging.info(f"回测日期: {current_date}")

            # 更新每只股票在当前日期的收盘价
            for symbol, df in self.data.items():
                day_data = df[df['date'].dt.date == current_date]
                if not day_data.empty:
                    close_price = day_data.iloc[-1]['close']
                    timestamp = datetime.combine(current_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
                    self.price_manager.add_price(symbol, timestamp, close_price)
                    portfolio.latest_prices[symbol] = close_price

                    # 将当天收盘价添加到 data[symbol] 中
                    new_row = {
                        'date': pd.to_datetime(timestamp),
                        'open': close_price,
                        'close': close_price,
                        'high': close_price,
                        'low': close_price,
                        'volume': 0,       # 可选填
                        'turnover': 0.0,   # 可选填
                        'symbol': symbol
                    }
                    self.data[symbol] = pd.concat([self.data[symbol], pd.DataFrame([new_row])], ignore_index=True)

            # 获取所有股票的最新价格时序
            current_price_series = self.price_manager.get_all_series()

            # 决定当天的买卖操作
            trades_buy, trades_sell = self.strategy.decide_trade(self.data, portfolio, current_price_series)

            # 模拟买入
            for trade in trades_buy:
                price = trade['price']
                quantity = trade['quantity']
                portfolio.buy_stock(trade['symbol'], price, quantity, current_date.strftime("%Y-%m-%d %H:%M:%S"))

            # 模拟卖出
            for trade in trades_sell:
                price = trade['price']
                quantity = trade['quantity']
                portfolio.sell_stock(trade['symbol'], price, quantity, current_date.strftime("%Y-%m-%d %H:%M:%S"))


        total_return = (portfolio.get_portfolio_value() - portfolio.initial_cash) / portfolio.initial_cash
        logging.info(f"回测总收益: {total_return * 100:.2f}%")
        self.results = {'total_return': total_return}
        
        # 保存详细结果
        backtest_result = {
            'total_return': total_return,
            'initial_cash': portfolio.initial_cash,
            'final_portfolio_value': portfolio.get_portfolio_value(),
            'transactions': portfolio.transactions
        }
        backtest_result_path = BACKTRACE_FILE
        with open(backtest_result_path, 'w') as f:
            json.dump(backtest_result, f, indent=4)
        logging.info("回测结果已保存。")

        return self.results
