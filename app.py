# app.py

import streamlit as st
import pandas as pd
import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path

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

# 设置日志
setup_logger()

@st.cache_resource
def data_fetcher():
    return DataFetcher(start_date="20220101", end_date=datetime.now().strftime("%Y%m%d"))    

# 初始化组件（全局状态）
@st.cache_resource
def initialize_portfolio():
    storage = Storage(filepath=PORTFOLIO_FILE)
    portfolio = Portfolio(initial_cash=INITIAL_CASH, storage=storage)
    return portfolio

portfolio = initialize_portfolio()

# 页面标题
st.title("量化交易系统")

# 侧边栏导航
st.sidebar.title("导航")
page = st.sidebar.radio("前往", ["投资组合", "交易日志", "交易执行", "回测", "设置"])

# 页面内容
if page == "投资组合":
    st.header("投资组合概览")
    
    # 显示现金和持仓
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("现金")
        st.write(f"${portfolio.cash:,.2f}")
    
    with col2:
        st.subheader("持仓")
        holdings = portfolio.holdings
        if holdings:
            holdings_df = pd.DataFrame.from_dict(holdings, orient='index', columns=['数量'])
            st.dataframe(holdings_df)
        else:
            st.write("暂无持仓")
    
    # 显示组合总价值
    st.subheader("组合总价值")
    # 计算组合总价值
    data_fetcher = data_fetcher()
    current_prices = {symbol: data_fetcher.fetch_current_price(symbol) for symbol in portfolio.holdings.keys()}
    portfolio_value = portfolio.get_portfolio_value(current_prices)
    st.write(f"${portfolio_value:,.2f}")

    # 显示详细交易记录
    st.subheader("交易记录")
    transactions = portfolio.transactions
    if transactions:
        transactions_df = pd.DataFrame(transactions)
        transactions_df['time'] = pd.to_datetime(transactions_df['time'])
        transactions_df = transactions_df.sort_values(by='time', ascending=False)
        st.dataframe(transactions_df)
    else:
        st.write("暂无交易记录")

elif page == "交易日志":
    st.header("交易日志")
    log_file_path = Path(LOG_FILE)
    if log_file_path.exists():
        with open(log_file_path, 'r', encoding='utf-8') as f:
            logs = f.readlines()
        # 显示最新的100条日志
        recent_logs = logs[-100:]
        st.text_area("日志", ''.join(recent_logs), height=600)
    else:
        st.write("日志文件不存在。")

elif page == "交易执行":
    st.header("交易执行")
    
    # 显示策略列表和执行按钮
    st.subheader("当前策略")
    strategies = STRATEGY_CONFIGS
    
    for strategy_cfg in strategies:
        strategy_name = strategy_cfg['name']
        st.write(f"### {strategy_name}")
        if strategy_name == 'MovingAverageCrossover':
            strategy = MovingAverageCrossoverStrategy(**strategy_cfg['params'])
        elif strategy_name == 'RSI':
            strategy = RSIStrategy(**strategy_cfg['params'])
        else:
            st.write("未知策略")
            continue
        
        if st.button(f"执行 {strategy_name} 策略"):
            with st.spinner(f"执行 {strategy_name} 策略..."):
                data_fetcher = data_fetcher()
                data = data_fetcher.fetch_all_data()
                for symbol, df in data.items():
                    buy_trades, sell_trades = strategy.decide_trade(df.copy(), portfolio)
                    # 处理买入信号
                    for trade in buy_trades:
                        portfolio.buy_stock(trade['symbol'], trade['price'], trade['quantity'])
                    # 处理卖出信号
                    for trade in sell_trades:
                        portfolio.sell_stock(trade['symbol'], trade['price'], trade['quantity'])
            st.success(f"{strategy_name} 策略执行完成")
    
    # 手动执行所有策略
    if st.button("执行所有策略"):
        with st.spinner("执行所有策略..."):
            combined_strategy = CombinedStrategy([
                StrategyFactory.get_strategy(cfg['name'], **cfg['params']) for cfg in STRATEGY_CONFIGS
            ])
            data_fetcher = data_fetcher()
            data = data_fetcher.fetch_all_data()
            backtester = Backtester(combined_strategy, data)
            backtester.run_backtest()
        st.success("所有策略执行完成")

elif page == "回测":
    st.header("策略回测")
    
    # 选择回测日期
    st.subheader("选择回测日期范围")
    start_date = st.date_input("开始日期", datetime(2022, 1, 1))
    end_date = st.date_input("结束日期", datetime.now())
    
    if st.button("运行回测"):
        with st.spinner("运行回测..."):
            data_fetcher = data_fetcher()
            data = data_fetcher.fetch_all_data()
            combined_strategy = CombinedStrategy([
                StrategyFactory.get_strategy(cfg['name'], **cfg['params']) for cfg in STRATEGY_CONFIGS
            ])
            backtester = Backtester(combined_strategy, data)
            results = backtester.run_backtest()
        st.success(f"回测完成，收益: {results['total_return']*100:.2f}%")
        st.write("回测结果:", results)

elif page == "设置":
    st.header("系统设置")
    
    # 显示当前配置
    st.subheader("当前策略配置")
    for cfg in STRATEGY_CONFIGS:
        st.write(f"### {cfg['name']}")
        for key, value in cfg['params'].items():
            st.write(f"- **{key}**: {value}")
    
    st.subheader("修改交易参数")
    # 示例：修改初始现金
    new_initial_cash = st.number_input("初始现金金额", value=INITIAL_CASH, min_value=0.0, step=1000.0)
    if st.button("更新初始现金"):
        portfolio.initial_cash = new_initial_cash
        portfolio.cash = new_initial_cash
        portfolio.save_portfolio()
        st.success(f"初始现金已更新为 ${new_initial_cash:,.2f}")
    
    # 你可以继续添加更多的设置选项，如添加/修改策略参数等

# 运行 Streamlit 应用程序
# 在命令行中运行: streamlit run app.py
