# price_time_series_manager.py

from collections import OrderedDict
from typing import Dict
import threading

class PriceTimeSeriesManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, max_length=100):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(PriceTimeSeriesManager, cls).__new__(cls)
                    cls._instance._initialize(max_length)
        return cls._instance

    def _initialize(self, max_length):
        self.price_time_series: Dict[str, OrderedDict] = {}
        self.max_length = max_length

    def add_price(self, symbol: str, timestamp: str, price: float):
        if symbol not in self.price_time_series:
            self.price_time_series[symbol] = OrderedDict()
        self.price_time_series[symbol][timestamp] = price
        if len(self.price_time_series[symbol]) > self.max_length:
            self.price_time_series[symbol].popitem(last=False)

    def get_series(self, symbol: str) -> OrderedDict:
        return self.price_time_series.get(symbol, OrderedDict())

    def get_all_series(self) -> Dict[str, OrderedDict]:
        return self.price_time_series

    def clear(self):
        self.price_time_series.clear()