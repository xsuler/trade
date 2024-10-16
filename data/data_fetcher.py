# data/data_fetcher.py

import akshare as ak
import pandas as pd
import logging
from typing import List, Dict
from price_time_series_manager import PriceTimeSeriesManager

class DataFetcher:
    # 定义列名映射，将中文列名映射为英文
    COLUMN_MAPPINGS_INDEX_CONS = {
        '品种代码': 'symbol_code',
        # 添加其他需要映射的列
    }

    COLUMN_MAPPINGS_SPOT = {
        '代码': 'symbol',
        '最新价': 'latest_price',
        # 添加其他需要映射的列
    }

    COLUMN_MAPPING_HISTORY = {
        '日期': 'date',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
        '成交额': 'turnover',
        # 添加其他需要映射的列
    }

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
        self.symbols = self.get_hot_symbols()[:30]  # 限制前10只股票
        # 初始化 PriceTimeSeriesManager
        self.price_manager = PriceTimeSeriesManager()

    def get_hot_symbols(self) -> List[str]:
        """
        获取热门指数的成分股代码

        :return: 股票代码列表
        """
        all_symbols = set()
        for index_code in self.hot_indices:
            while True:
                try:
                    index_df = ak.index_stock_cons(symbol=index_code)
                    # 重命名列
                    index_df.rename(columns=self.COLUMN_MAPPINGS_INDEX_CONS, inplace=True)

                    if 'symbol_code' in index_df.columns:
                        symbols = index_df['symbol_code'].str.strip().tolist()
                        logging.info(f"从指数 {index_code} 获取到 {len(symbols)} 只股票代码。")
                        all_symbols.update(symbols)
                    break
                except Exception as e:
                    pass
        return list(all_symbols)

    def fetch_current_price(self, symbol: str) -> float:
        """
        获取指定股票的最新价格。

        :param symbol: 股票代码
        :return: 最新价格
        """
        while True:
            try:
                stock_zh_a_spot_df = ak.stock_zh_a_spot_em()
                stock_info = stock_zh_a_spot_df[stock_zh_a_spot_df['代码'] == symbol]
                if not stock_info.empty:
                    latest_price = stock_info.iloc[0]['最新价']
                    return float(latest_price)
                else:
                    logging.warning(f"未找到股票代码 {symbol} 的最新价格。")
                    return 0.0
            except Exception as e:
                pass

    def fetch_all_data(self, start_date: str = None, end_date: str = None) -> Dict[str, pd.DataFrame]:
        """
        获取所有股票的历史数据。

        :param start_date: 开始日期，格式 'YYYYMMDD'
        :param end_date: 结束日期，格式 'YYYYMMDD'
        :return: 字典，键为股票代码，值为对应的历史数据 DataFrame
        """
        all_data = {}
        for symbol in self.symbols:
            while True:
                try:
                    stock_df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, end_date=end_date, adjust=self.adjust)
                    stock_df.rename(columns=self.COLUMN_MAPPING_HISTORY, inplace=True)
                    stock_df['symbol'] = symbol  # 添加 symbol 列
                    # 确保日期是datetime格式并排序
                    stock_df['date'] = pd.to_datetime(stock_df['date'])
                    stock_df.sort_values(by='date', inplace=True)
                    all_data[symbol] = stock_df
                    break
                except Exception as e:
                    pass
        return all_data