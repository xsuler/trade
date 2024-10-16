# data/data_fetcher.py

import akshare as ak
import pandas as pd
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict
from config.config import INITIAL_CASH
import os

class DataFetcher:
    def __init__(self, start_date: str, end_date: str, period: str = 'daily', adjust: str = 'hfq'):
        self.start_date = start_date
        self.end_date = end_date
        self.period = period
        self.adjust = adjust
        self.symbols = self.get_all_symbols()

    def get_all_symbols(self) -> List[str]:
        try:
            stock_list = ak.stock_zh_a_spot_em()
            symbols = stock_list['代码'].str.strip().tolist()
            logging.info(f"获取到 {len(symbols)} 只A股股票代码。")
            return symbols
        except Exception as e:
            logging.error(f"获取股票代码失败: {e}")
            return []

    def fetch_data_for_symbol(self, symbol: str) -> Tuple[str, pd.DataFrame]:
        try:
            df = ak.stock_zh_a_daily(symbol=symbol, start_date=self.start_date, end_date=self.end_date, adjust=self.adjust)
            if df is not None and not df.empty:
                df['symbol'] = symbol
                return symbol, df
            else:
                logging.warning(f"{symbol} 无数据。")
                return symbol, pd.DataFrame()
        except Exception as e:
            logging.error(f"获取 {symbol} 数据失败: {e}")
            return symbol, pd.DataFrame()

    def fetch_all_data(self) -> Dict[str, pd.DataFrame]:
        data = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.fetch_data_for_symbol, symbol): symbol for symbol in self.symbols}
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    sym, df = future.result()
                    if not df.empty:
                        data[sym] = df
                except Exception as e:
                    logging.error(f"处理 {symbol} 时发生异常: {e}")
        logging.info(f"成功获取 {len(data)} 只股票的历史数据。")
        return data

    def fetch_current_price(self, symbol: str) -> float:
        """获取实时价格，akshare 暂无实时API，可使用最新收盘价代替"""
        try:
            df = ak.stock_zh_a_daily(symbol=symbol, start_date=self.end_date, end_date=self.end_date, adjust=self.adjust)
            if df is not None and not df.empty:
                current_price = df.iloc[-1]['close']
                return current_price
            else:
                logging.warning(f"无法获取 {symbol} 的当前价格，使用最新收盘价代替")
                return 0.0
        except Exception as e:
            logging.error(f"获取 {symbol} 当前价格失败: {e}")
            return 0.0
