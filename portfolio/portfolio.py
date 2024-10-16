# portfolio/portfolio.py


import logging
from datetime import datetime
from typing import Dict
from storage.storage import Storage
from data.data_fetcher import DataFetcher

class Portfolio:
    def __init__(self, initial_cash: float = 100000, data_fetcher: DataFetcher = None, storage: Storage = None):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.holdings: Dict[str, int] = {}  # symbol: quantity
        self.transactions = []
        self.data_fetcher = data_fetcher
        self.storage = storage if storage else Storage()
        self.load_portfolio()

    def load_portfolio(self):
        data = self.storage.load()
        self.cash = data.get('cash', self.initial_cash)
        self.holdings = data.get('holdings', {})
        self.transactions = data.get('transactions', [])
        logging.info(f"加载组合: 现金={self.cash}, 持仓={self.holdings}")

    def save_portfolio(self):
        data = {
            'cash': self.cash,
            'holdings': self.holdings,
            'transactions': self.transactions
        }
        self.storage.save(data)

    def buy_stock(self, symbol: str, price: float, quantity: int):
        cost = price * quantity
        if self.cash >= cost:
            self.cash -= cost
            self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
            self.transactions.append({
                'type': 'buy',
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            logging.info(f"买入 {symbol} - 数量: {quantity}, 价格: {price}, 成本: {cost}")
            self.save_portfolio()
        else:
            logging.warning(f"现金不足，无法买入 {symbol} - 需要: {cost}, 可用: {self.cash}")

    def sell_stock(self, symbol: str, price: float, quantity: int):
        if self.holdings.get(symbol, 0) >= quantity:
            self.cash += price * quantity
            self.holdings[symbol] -= quantity
            if self.holdings[symbol] == 0:
                del self.holdings[symbol]
            self.transactions.append({
                'type': 'sell',
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            logging.info(f"卖出 {symbol} - 数量: {quantity}, 价格: {price}, 收益: {price * quantity}")
            self.save_portfolio()
        else:
            logging.warning(f"持仓不足，无法卖出 {symbol} - 尝试卖出: {quantity}, 持有: {self.holdings.get(symbol, 0)}")

    def get_portfolio_value(self, current_prices: Dict[str, float] = {}) -> float:
        total = self.cash
        for symbol, qty in self.holdings.items():
            price = current_prices.get(symbol, 0.0)
            total += price * qty
        return total
