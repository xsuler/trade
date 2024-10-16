# app.py
import streamlit as st
import pandas as pd
import os
import json
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

# 初始化 Session State
if 'live_trading' not in st.session_state:
    st.session_state.live_trading = False
if 'signals' not in st.session_state:
    st.session_state.signals = []

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
page = st.sidebar.radio("前往", ["投资组合", "交易日志", "实时交易", "回测", "设置"])

# 引入自动刷新功能（仅在实时交易模式下）
if 'auto_refresh_id' not in st.session_state:
    st.session_state.auto_refresh_id = None

# 实时交易的逻辑函数
def perform_live_trading():
    data_fetcher_instance = data_fetcher()
    combined_strategy = CombinedStrategy([
        StrategyFactory.get_strategy(cfg['name'], **cfg['params']) for cfg in STRATEGY_CONFIGS
    ])
    data = data_fetcher_instance.fetch_all_data()
    for symbol, df in data.items():
        buy_trades, sell_trades = combined_strategy.decide_trade(df.copy(), portfolio)
        # 添加买入信号
        for trade in buy_trades:
            st.session_state.signals.append({
                'type': 'buy',
                'symbol': trade['symbol'],
                'price': trade['price'],
                'quantity': trade['quantity'],
                'time': datetime.now()
            })
        # 添加卖出信号
        for trade in sell_trades:
            st.session_state.signals.append({
                'type': 'sell',
                'symbol': trade['symbol'],
                'price': trade['price'],
                'quantity': trade['quantity'],
                'time': datetime.now()
            })

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
    current_prices = {}
    for symbol in portfolio.holdings.keys():
        current_price = data_fetcher().fetch_current_price(symbol)
        current_prices[symbol] = current_price
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

elif page == "实时交易":
    st.header("实时交易")
    
    if not st.session_state.live_trading:
        if st.button("启动实时交易"):
            st.session_state.live_trading = True
            st.session_state.signals = []  # 清空之前的信号
            # 启动自动刷新，每分钟刷新一次（60000 毫秒）
            st.session_state.auto_refresh_id = st.experimental_get_query_params()
            st.experimental_set_query_params(auto_refresh=True)
            st.rerun()
            st.success("实时交易已启动")
    else:
        if st.button("停止实时交易"):
            st.session_state.live_trading = False
            # 停止自动刷新
            st.experimental_set_query_params(auto_refresh=False)
            st.rerun()
            st.success("实时交易已停止")
    
    # 如果实时交易开启，执行交易逻辑
    if st.session_state.live_trading:
        perform_live_trading()
        # 启动自动刷新，每分钟刷新一次（60000 毫秒）
        count = st.experimental_get_query_params().get('count', [0])[0]
        count = int(count) + 1
        st.experimental_set_query_params(count=count)
        st.rerun()

    st.subheader("当前信号")
    if st.session_state.signals:
        # 使用副本防止在迭代时修改列表
        for idx, signal in enumerate(st.session_state.signals.copy()):
            with st.expander(f"信号 {idx + 1} - {signal['time'].strftime('%Y-%m-%d %H:%M:%S')}"):
                st.write(f"**类型**: {signal['type'].capitalize()}")
                st.write(f"**股票代码**: {signal['symbol']}")
                st.write(f"**价格**: ${signal['price']:,.2f}")
                # 提供调整数量的输入框
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
                        # 移除已处理的信号
                        st.session_state.signals.pop(idx)
                        st.rerun()
                with col2:
                    if st.button(f"忽略", key=f"ign_{idx}"):
                        st.session_state.signals.pop(idx)
                        st.rerun()
    else:
        st.write("暂无待处理的交易信号。")

elif page == "回测":
    st.header("策略回测")
    
    # 选择回测日期
    st.subheader("选择回测日期范围")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", datetime(2022, 1, 1))
    with col2:
        end_date = st.date_input("结束日期", datetime.now())
    
    if st.button("运行回测"):
        with st.spinner("运行回测..."):
            data_fetcher_instance = data_fetcher()
            data = data_fetcher_instance.fetch_all_data(start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"))
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
