# ui/user_interface.py

import logging
import threading
import time
from typing import Dict
from portfolio.portfolio import Portfolio

class UserInterface:
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio
        self.trade_queue = []
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.process_trades)
        self.thread.daemon = True
        self.thread.start()

    def add_trade(self, trade: Dict, trade_type: str):
        with self.lock:
            self.trade_queue.append((trade, trade_type))

    def process_trades(self):
        while True:
            with self.lock:
                if self.trade_queue:
                    trade, trade_type = self.trade_queue.pop(0)
                    if trade_type == 'buy':
                        self.prompt_user_buy(trade)
                    elif trade_type == 'sell':
                        self.prompt_user_sell(trade)
            time.sleep(1)  # 等待一秒后处理下一个交易

    def prompt_user_buy(self, trade: Dict):
        symbol = trade['symbol']
        price = trade['price']
        suggested_quantity = trade['quantity']
        logging.info(f"推荐买入 {symbol} - 推荐数量: {suggested_quantity}, 价格: {price}")
        while True:
            decision = input(f"[买入] 是否买入 {symbol} (推荐数量: {suggested_quantity}, 价格: {price})? (y/n): ")
            if decision.lower() == 'y':
                while True:
                    qty_input = input(f"请输入买入数量（推荐: {suggested_quantity}）: ")
                    try:
                        quantity = int(qty_input)
                        if quantity <= 0:
                            print("数量必须大于0。")
                            continue
                        self.portfolio.buy_stock(symbol, price, quantity)
                        break
                    except ValueError:
                        print("请输入有效的整数数量。")
                break
            elif decision.lower() == 'n':
                logging.info(f"用户放弃买入 {symbol} - 推荐数量: {suggested_quantity}, 价格: {price}")
                break
            else:
                print("请输入 'y' 或 'n'。")

    def prompt_user_sell(self, trade: Dict):
        symbol = trade['symbol']
        price = trade['price']
        suggested_quantity = trade['quantity']
        logging.info(f"推荐卖出 {symbol} - 推荐数量: {suggested_quantity}, 价格: {price}")
        while True:
            decision = input(f"[卖出] 是否卖出 {symbol} (推荐数量: {suggested_quantity}, 价格: {price})? (y/n): ")
            if decision.lower() == 'y':
                while True:
                    qty_input = input(f"请输入卖出数量（推荐: {suggested_quantity}）: ")
                    try:
                        quantity = int(qty_input)
                        if quantity <= 0:
                            print("数量必须大于0。")
                            continue
                        self.portfolio.sell_stock(symbol, price, quantity)
                        break
                    except ValueError:
                        print("请输入有效的整数数量。")
                break
            elif decision.lower() == 'n':
                logging.info(f"用户放弃卖出 {symbol} - 推荐数量: {suggested_quantity}, 价格: {price}")
                break
            else:
                print("请输入 'y' 或 'n'。")
