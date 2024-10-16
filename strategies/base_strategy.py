from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Tuple, Dict

class BaseStrategy(ABC):
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        pass

    @abstractmethod
    def decide_trade(self, data: Dict[str, pd.DataFrame], portfolio, price_time_series: Dict[str, Dict[str, float]]) -> Tuple[List[Dict], List[Dict]]:
        """
        根据交易信号，决定买卖操作
        返回买入和卖出操作列表
        每个操作为字典，包含 symbol, price, quantity
        """
        pass