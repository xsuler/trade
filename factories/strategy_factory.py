# factories/strategy_factory.py

from typing import Dict
from strategies.base_strategy import BaseStrategy
from strategies.ma_crossover_strategy import MovingAverageCrossoverStrategy
from strategies.rsi_strategy import RSIStrategy

class StrategyFactory:
    @staticmethod
    def get_strategy(strategy_name: str, weight: float, **kwargs) -> BaseStrategy:
        if strategy_name == 'MovingAverageCrossover':
            return MovingAverageCrossoverStrategy(weight=weight, **kwargs)
        elif strategy_name == 'RSI':
            return RSIStrategy(weight=weight, **kwargs)
        else:
            raise ValueError(f"未知的策略名称: {strategy_name}")