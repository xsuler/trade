# data/data_fetcher.py

import akshare as ak
import pandas as pd
import logging
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
        self.spot_data = self.fetch_spot_data()  # 初始化时获取实时价格

    def get_all_symbols(self) -> List[str]:
        try:
            stock_list = ak.stock_zh_a_spot_em()
            symbols = stock_list['代码'].str.strip().tolist()
            logging.info(f"获取到 {len(symbols)} 只A股股票代码。")
            return symbols
        except Exception as e:
            logging.error(f"获取股票代码失败: {e}")
            return []

    def fetch_spot_data(self) -> pd.DataFrame:
        """获取所有A股的实时价格数据"""
        try:
            spot_df = ak.stock_zh_a_spot_em()
            if spot_df is not None and not spot_df.empty:
                logging.info("成功获取实时价格数据。")
                return spot_df
            else:
                logging.warning("未获取到实时价格数据。")
                return pd.DataFrame()
        except Exception as e:
            logging.error(f"获取实时价格数据失败: {e}")
            return pd.DataFrame()

    def fetch_data_for_symbol(self, symbol: str) -> Tuple[str, pd.DataFrame]:
        try:
            # 使用 stock_zh_a_hist 代替 stock_zh_a_daily
            df = ak.stock_zh_a_hist(symbol=symbol, period=self.period, start_date=self.start_date, end_date=self.end_date, adjust=self.adjust)
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
        for symbol in self.symbols:
            try:
                sym, df = self.fetch_data_for_symbol(symbol)
                if not df.empty:
                    data[sym] = df
            except Exception as e:
                logging.error(f"处理 {symbol} 时发生异常: {e}")
        logging.info(f"成功获取 {len(data)} 只股票的历史数据。")
        return data

    def fetch_current_price(self, symbol: str) -> float:
        """获取实时价格，使用 stock_zh_a_spot_em"""
        try:
            if self.spot_data.empty:
                logging.warning("实时价格数据为空，无法获取当前价格。返回0.0")
                return 0.0

            # 查找对应的 symbol 的实时价格
            row = self.spot_data[self.spot_data['代码'] == symbol]
            if not row.empty:
                current_price = float(row.iloc[0]['最新价'])  # 确保转换为浮点数
                return current_price
            else:
                logging.warning(f"无法找到 {symbol} 的实时价格，使用最新收盘价代替")
                return 0.0
        except Exception as e:
            logging.error(f"获取 {symbol} 当前价格失败: {e}")
            return 0.0
