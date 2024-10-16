# portfolio/portfolio.py

import logging
from datetime import datetime
from typing import Dict, Optional, List
from storage.storage import Storage
from data.data_fetcher import DataFetcher
from config.config import INITIAL_CASH, TRANSACTION_COST_RATE, SLIPPAGE_RATE

class Portfolio:
    def __init__(self, initial_cash: float = INITIAL_CASH, data_fetcher: Optional[DataFetcher] = None, storage: Optional[Storage] = None, simulate_costs: bool = False):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.holdings: Dict[str, int] = {}  # symbol: quantity
        self.transactions = []
        self.data_fetcher = data_fetcher
        self.storage = storage if storage else Storage()
        self.buy_lots: Dict[str, List[Dict[str, float]]] = {}
        self.latest_prices = {}
        self.simulate_costs = simulate_costs  # 是否模拟交易成本
        self.load_portfolio()

    def load_portfolio(self):
        data = self.storage.load()
        self.cash = data.get('cash', self.initial_cash)
        self.holdings = data.get('holdings', {})
        self.transactions = data.get('transactions', [])
        self.buy_lots = data.get('buy_lots', {})
        self.latest_prices = data.get('latest_prices', {})
        if self.latest_prices == {} and self.data_fetcher is not None:
            for symbol in self.holdings:
                self.latest_prices[symbol] = self.data_fetcher.fetch_current_price(symbol)
            self.save_portfolio()

    def save_portfolio(self):
        data = {
            'cash': self.cash,
            'holdings': self.holdings,
            'transactions': self.transactions,
            'buy_lots': self.buy_lots,
            'latest_prices': self.latest_prices
        }
        self.storage.save(data)

    def buy_stock(self, symbol: str, price: float, quantity: int, time: str):
        cost = price * quantity
        # 模拟交易成本和滑点
        if self.simulate_costs:
            cost += cost * TRANSACTION_COST_RATE  # 交易成本
            cost += price * quantity * SLIPPAGE_RATE  # 滑点
        if self.cash >= cost:
            self.cash -= cost
            self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
            self.transactions.append({
                'type': 'buy',
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'time': time,
                'cost': cost
            })
            logging.info(f"买入 {symbol} - 数量: {quantity}, 价格: {price}, 成本: ￥{cost:.2f}")
            # 更新买入批次
            if symbol not in self.buy_lots:
                self.buy_lots[symbol] = []
            self.buy_lots[symbol].append({'price': price, 'quantity': quantity})
            self.save_portfolio()
        else:
            logging.warning(f"现金不足，无法买入 {symbol} - 需要: ￥{cost:.2f}, 可用: ￥{self.cash:.2f}")

    def sell_stock(self, symbol: str, price: float, quantity: int, time: str):
        if self.holdings.get(symbol, 0) >= quantity:
            revenue = price * quantity
            # 模拟交易成本和滑点
            if self.simulate_costs:
                revenue -= revenue * TRANSACTION_COST_RATE  # 交易成本
                revenue -= price * quantity * SLIPPAGE_RATE  # 滑点
            self.cash += revenue
            self.holdings[symbol] -= quantity
            if self.holdings[symbol] == 0:
                del self.holdings[symbol]
            self.transactions.append({
                'type': 'sell',
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'time': time,
                'revenue': revenue
            })
            logging.info(f"卖出 {symbol} - 数量: {quantity}, 价格: {price}, 收益: ￥{revenue:.2f}")
            # 更新买入批次（FIFO）
            if symbol in self.buy_lots:
                remaining_qty = quantity
                while remaining_qty > 0 and self.buy_lots[symbol]:
                    lot = self.buy_lots[symbol][0]
                    if lot['quantity'] > remaining_qty:
                        lot['quantity'] -= remaining_qty
                        remaining_qty = 0
                    else:
                        remaining_qty -= lot['quantity']
                        self.buy_lots[symbol].pop(0)
                if not self.buy_lots[symbol]:
                    del self.buy_lots[symbol]
            self.save_portfolio()
        else:
            logging.warning(f"持仓不足，无法卖出 {symbol} - 尝试卖出: {quantity}, 持有: {self.holdings.get(symbol, 0)}")

    def get_portfolio_value(self) -> float:
        total = self.cash
        for symbol, qty in self.holdings.items():
            if symbol not in self.latest_prices:
                continue
            price = self.latest_prices.get(symbol, 0.0)
            total += price * qty
        return total

    def get_average_cost(self) -> Dict[str, float]:
        """
        计算每个持仓的平均成本价，基于FIFO原则
        """
        avg_costs = {}
        for symbol, lots in self.buy_lots.items():
            total_cost = sum(lot['price'] * lot['quantity'] for lot in lots)
            total_qty = sum(lot['quantity'] for lot in lots)
            if total_qty > 0:
                avg_costs[symbol] = total_cost / total_qty
            else:
                avg_costs[symbol] = 0.0
        return avg_costs

    def reset_portfolio(self):
        self.cash = self.initial_cash
        self.holdings = {}
        self.transactions = []
        self.buy_lots = {}
        self.latest_prices = {}
        self.save_portfolio()
        logging.info("组合已重置。")