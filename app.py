import streamlit as st
import pandas as pd
import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path
import queue  # Import the queue module

# 导入您的模块
from portfolio.portfolio import Portfolio
from storage.storage import Storage
from data.data_fetcher import DataFetcher
from factories.strategy_factory import StrategyFactory
from strategies.ma_crossover_strategy import MovingAverageCrossoverStrategy
from strategies.rsi_strategy import RSIStrategy
from combined_strategy.combined_strategy import CombinedStrategy
from backtest.backtester import Backtester
from ui.user_interface import UserInterface
from utils.logger import setup_logger
from config.config import STRATEGY_CONFIGS, INITIAL_CASH, PORTFOLIO_FILE, LOG_FILE

# Initialize the logger
setup_logger()

# Initialize session state variables
if 'live_trading' not in st.session_state:
    st.session_state.live_trading = False
if 'signals' not in st.session_state:
    st.session_state.signals = []
if 'signal_queue' not in st.session_state:
    st.session_state.signal_queue = queue.Queue()

@st.cache_resource
def data_fetcher():
    return DataFetcher(start_date="20220101", end_date=datetime.now().strftime("%Y%m%d"))    

# Initialize components (global state)
@st.cache_resource
def initialize_portfolio():
    storage = Storage(filepath=PORTFOLIO_FILE)
    portfolio = Portfolio(initial_cash=INITIAL_CASH, storage=storage)
    return portfolio

portfolio = initialize_portfolio()

# Page title
st.title("量化交易系统")

# Sidebar navigation
st.sidebar.title("导航")
page = st.sidebar.radio("前往", ["投资组合", "交易日志", "实时交易", "回测", "设置"])

# Function to process queued signals
def process_signal_queue():
    while not st.session_state.signal_queue.empty():
        signal = st.session_state.signal_queue.get()
        st.session_state.signals.append(signal)

# Process any new signals from the queue
process_signal_queue()

# Background thread function for live trading
def live_trading_thread():
    data_fetcher_instance = data_fetcher()
    combined_strategy = CombinedStrategy([
        StrategyFactory.get_strategy(cfg['name'], **cfg['params']) for cfg in STRATEGY_CONFIGS
    ])
    while st.session_state.live_trading:
        data = data_fetcher_instance.fetch_all_data()
        for symbol, df in data.items():
            buy_trades, sell_trades = combined_strategy.decide_trade(df.copy(), portfolio)
            # Add signals to the queue
            for trade in buy_trades:
                signal = {
                    'type': 'buy',
                    'symbol': trade['symbol'],
                    'price': trade['price'],
                    'quantity': trade['quantity'],
                    'time': datetime.now()
                }
                st.session_state.signal_queue.put(signal)
            for trade in sell_trades:
                signal = {
                    'type': 'sell',
                    'symbol': trade['symbol'],
                    'price': trade['price'],
                    'quantity': trade['quantity'],
                    'time': datetime.now()
                }
                st.session_state.signal_queue.put(signal)
        time.sleep(60)  # Fetch data every minute

# Page content based on navigation
if page == "投资组合":
    # ... [Your existing code for 投资组合 page] ...
    pass  # Replace with existing code

elif page == "交易日志":
    # ... [Your existing code for 交易日志 page] ...
    pass  # Replace with existing code

elif page == "实时交易":
    st.header("实时交易")
    
    if not st.session_state.live_trading:
        if st.button("启动实时交易"):
            st.session_state.live_trading = True
            # Start the background thread
            t = threading.Thread(target=live_trading_thread, daemon=True)
            t.start()
            st.success("实时交易已启动")
    else:
        if st.button("停止实时交易"):
            st.session_state.live_trading = False
            st.success("实时交易已停止")
    
    st.subheader("当前信号")
    if st.session_state.signals:
        for idx, signal in enumerate(st.session_state.signals.copy()):
            with st.expander(f"信号 {idx + 1} - {signal['time'].strftime('%Y-%m-%d %H:%M:%S')}"):
                st.write(f"**类型**: {signal['type'].capitalize()}")
                st.write(f"**股票代码**: {signal['symbol']}")
                st.write(f"**价格**: ${signal['price']:,.2f}")
                # Provide input for adjusting quantity
                new_quantity = st.number_input(f"调整 {signal['type']} 份额", min_value=1, value=int(signal['quantity']), key=f"qty_{idx}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"确认 {signal['type'].capitalize()}", key=f"conf_{idx}"):
                        if signal['type'] == 'buy':
                            portfolio.buy_stock(signal['symbol'], signal['price'], new_quantity)
                            st.success(f"已买入 {new_quantity} 份 {signal['symbol']}")
                        elif signal['type'] == 'sell':
                            portfolio.sell_stock(signal['symbol'], signal['price'], new_quantity)
                            st.success(f"已卖出 {new_quantity} 份 {signal['symbol']}")
                        # Remove the processed signal
                        st.session_state.signals.pop(idx)
                        st.experimental_rerun()
                with col2:
                    if st.button(f"忽略", key=f"ign_{idx}"):
                        st.session_state.signals.pop(idx)
                        st.experimental_rerun()
    else:
        st.write("暂无待处理的交易信号。")

elif page == "回测":
    # ... [Your existing code for 回测 page] ...
    pass  # Replace with existing code

elif page == "设置":
    # ... [Your existing code for 设置 page] ...
    pass  # Replace with existing code

# Optionally, you can add periodic checks or actions here
# However, with the queue approach, it's handled above
