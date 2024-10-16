# data/data_fetcher.py

import akshare as ak
import pandas as pd
import logging
from typing import List, Tuple, Dict
from config.config import INITIAL_CASH
import os
from cachetools import cached, TTLCache

class DataFetcher:
    # 定义一个全局缓存，最多保存1个条目，TTL为12小时
    _fetch_all_data_cache = TTLCache(maxsize=1, ttl=43200)  # 43200秒 = 12小时

    def __init__(self, start_date: str, end_date: str, period: str = 'daily', adjust: str = 'hfq', hot_indices: List[str] = None):
        """
        初始化 DataFetcher

        :param start_date: 数据开始日期，格式 'YYYYMMDD'
        :param end_date: 数据结束日期，格式 'YYYYMMDD'
        :param period: 数据周期，如 'daily', 'weekly' 等
        :param adjust: 复权方式，如 'hfq'（后复权）, 'qfq'（前复权）, 'bfq'（不复权）
        :param hot_indices: 热门指数列表，默认为 ['000300', '399005', '399006']
        """
        self.start_date = start_date
        self.end_date = end_date
        self.period = period
        self.adjust = adjust
        self.hot_indices = hot_indices if hot_indices else ["000300", "399005", "399006"]
        self.symbols = self.get_hot_symbols()
        self.spot_data = self.fetch_spot_data()  # 初始化时获取实时价格

    def get_hot_symbols(self) -> List[str]:
        """
        获取热门指数的成分股代码

        :return: 股票代码列表
        """
        all_symbols = set()
        for index_code in self.hot_indices:
            try:
                index_df = ak.index_stock_cons(symbol=index_code)
                if '代码' in index_df.columns:
                    symbols = index_df['品种代码'].str.strip().tolist()
                    logging.info(f"从指数 {index_code} 获取到 {len(symbols)} 只股票代码。")
                    all_symbols.update(symbols)
                    
                else:
                    logging.warning(f"指数 {index_code} 的成分股数据中不包含 '代码' 列。")
            except Exception as e:
                logging.error(f"获取指数 {index_code} 成分股失败: {e}")

        symbols_list = sorted(list(all_symbols))
        logging.info(f"总共获取到 {len(symbols_list)} 只热门股票代码。")
        return symbols_list

    def fetch_spot_data(self) -> pd.DataFrame:
        """获取热门A股的实时价格数据"""
        try:
            spot_df = ak.stock_zh_a_spot_em()
            if spot_df is not None and not spot_df.empty:
                # 过滤出热门股票
                spot_df['代码'] = spot_df['代码'].str.strip()
                filtered_spot_df = spot_df[spot_df['代码'].isin(self.symbols)]
                logging.info(f"成功获取 {len(filtered_spot_df)} 只热门股票的实时价格数据。")
                return filtered_spot_df
            else:
                logging.warning("未获取到实时价格数据。")
                return pd.DataFrame()
        except Exception as e:
            logging.error(f"获取实时价格数据失败: {e}")
            return pd.DataFrame()

    def fetch_data_for_symbol(self, symbol: str) -> Tuple[str, pd.DataFrame]:
        try:
            # 使用 stock_zh_a_hist 获取历史数据
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

    @cached(_fetch_all_data_cache)
    def fetch_all_data(self) -> Dict[str, pd.DataFrame]:
        """
        获取所有热门股票的历史数据，并使用缓存优化性能。
        缓存有效期为12小时。
        """
        data = {}
        for symbol in self.symbols:
            try:
                sym, df = self.fetch_data_for_symbol(symbol)
                if not df.empty:
                    data[sym] = df
            except Exception as e:
                logging.error(f"处理 {symbol} 时发生异常: {e}")
        logging.info(f"成功获取 {len(data)} 只热门股票的历史数据。")
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
