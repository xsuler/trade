# app.py

import os
import json
import logging
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.graph_objs as go
from pathlib import Path

# 导入您的模块
from portfolio.portfolio import Portfolio
from storage.storage import Storage
from data.data_fetcher import DataFetcher
from factories.strategy_factory import StrategyFactory
from combined_strategy.combined_strategy import CombinedStrategy
from backtest.backtester import Backtester
from utils.logger import setup_logger
from config.config import STRATEGY_CONFIGS, INITIAL_CASH, PORTFOLIO_FILE, LOG_FILE, BACKTRACE_FILE, TRANSACTION_COST_RATE, SLIPPAGE_RATE

# 导入价格时序管理器
from price_time_series_manager import PriceTimeSeriesManager

# 设置日志
setup_logger()

# 初始化 PriceTimeSeriesManager
price_manager = PriceTimeSeriesManager()

# 初始化 Session State
if 'signals' not in st.session_state:
    st.session_state.signals = []
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []  # 存储交易历史用于可视化
if 'price_history' not in st.session_state:
    st.session_state.price_history = []  # 存储价格更新历史

@st.cache_resource(show_spinner=False)
def data_fetcher():
    return DataFetcher(start_date="20220101", end_date=datetime.now().strftime("%Y%m%d"))

@st.cache_data(ttl=3600*12, show_spinner=False)
def all_stock_data(start_date, end_date):
    data_fetcher_instance = data_fetcher()
    return data_fetcher_instance.fetch_all_data(start_date=start_date, end_date=end_date)

@st.cache_resource(show_spinner=False)
def portfolio_instance():
    storage = Storage(filepath=PORTFOLIO_FILE)
    portfolio = Portfolio(initial_cash=INITIAL_CASH, storage=storage, data_fetcher=data_fetcher(), simulate_costs=False)
    return portfolio

portfolio = portfolio_instance()
portfolio.load_portfolio()

# 页面标题
st.title("量化交易系统")

# 顶部标签页导航
tabs = ["投资组合", "交易日志", "实时交易", "回测", "设置"]

tab1, tab2, tab3, tab4, tab5 = st.tabs(tabs)

def perform_live_trading():
    # 创建占位符用于显示状态信息
    status_placeholder = st.empty()
    progress_bar = st.progress(0)

    try:
        # 步骤 1: 获取数据
        status_placeholder.text("步骤 1/6: 获取所有股票数据...")
        data = all_stock_data(start_date="20220101", end_date=datetime.now().strftime("%Y%m%d"))
        st.info(f"获取到 {len(data)} 只股票的数据。")
        progress_bar.progress(16)

        # 步骤 2: 获取最新价格并更新 price_time_series
        status_placeholder.text("步骤 2/6: 更新最新价格...")
        for symbol in data.keys():
            current_price = portfolio.data_fetcher.fetch_current_price(symbol)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            price_manager.add_price(symbol, timestamp, current_price)
            portfolio.latest_prices[symbol] = current_price
            # 收集用于可视化的价格历史
            if symbol in portfolio.holdings:
                st.session_state.price_history.append({
                    'symbol': symbol,
                    'price': current_price,
                    'time': datetime.now()
                })

            # 将最新价格添加到 data[symbol] 数据帧中
            if current_price > 0:
                new_row = {
                    'date': pd.to_datetime(timestamp),
                    'open': current_price,
                    'close': current_price,
                    'high': current_price,
                    'low': current_price,
                    'volume': 0,       # 由于是实时数据，这里暂时为 0
                    'turnover': 0.0,   # 同上
                    'symbol': symbol
                }
                data[symbol] = pd.concat([data[symbol], pd.DataFrame([new_row])], ignore_index=True)
        portfolio.save_portfolio()
        progress_bar.progress(33)
        st.session_state.log_messages.append(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 最新价格更新完成。"
        )

        # 步骤 3: 初始化策略
        status_placeholder.text("步骤 3/6: 初始化组合策略...")
        strategies = [
            StrategyFactory.get_strategy(cfg['name'], weight=cfg.get('weight', 1.0), **cfg['params']) for cfg in STRATEGY_CONFIGS
        ]
        combined_strategy = CombinedStrategy(strategies)
        progress_bar.progress(50)
        st.session_state.log_messages.append(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 组合策略初始化完成，子策略已准备就绪。"
        )

        # 步骤 4: 生成交易信号
        status_placeholder.text("步骤 4/6: 生成交易信号...")
        buy_trades, sell_trades = combined_strategy.decide_trade(data, portfolio, price_manager.get_all_series())
        progress_bar.progress(66)
        st.session_state.log_messages.append(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 交易信号生成完成，买入信号数量: {len(buy_trades)}, 卖出信号数量: {len(sell_trades)}。"
        )

        # 步骤 5: 处理交易信号
        status_placeholder.text("步骤 5/6: 处理交易信号...")
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
        progress_bar.progress(83)
        st.session_state.log_messages.append(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 交易信号已添加至待处理信号队列。"
        )

        # 步骤 6: 完成
        status_placeholder.text("步骤 6/6: 实时交易完成。")
        progress_bar.progress(100)
        st.session_state.log_messages.append(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 实时交易完成。"
        )

    except Exception as e:
        logging.error(f"实时交易过程中发生错误: {e}")
        st.session_state.log_messages.append(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 实时交易过程中发生错误: {e}"
        )
        status_placeholder.text("实时交易过程中发生错误。")
        progress_bar.empty()
    finally:
        # 移除已有的占位符
        status_placeholder.empty()

# 投资组合页面
with tab1:
    if st.button("清除数据"):
        price_manager.clear()
        st.session_state.signals = []
        st.session_state.log_messages = []
        st.session_state.trade_history = []
        st.session_state.price_history = []
        f = open(LOG_FILE, "a")
        f.truncate(0)
        f.close()
        portfolio.reset_portfolio()

        if os.path.exists(PORTFOLIO_FILE):
            os.remove(PORTFOLIO_FILE)
        if os.path.exists(BACKTRACE_FILE):
            os.remove(BACKTRACE_FILE)
        st.rerun()

    st.header("投资组合概览")

    # 显示现金和持仓
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("现金")
        st.write(f"￥{portfolio.cash:,.2f}")

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
    portfolio_value = portfolio.get_portfolio_value()
    st.write(f"￥{portfolio_value:,.2f}")

    # 计算收益
    total_return = (portfolio_value - portfolio.initial_cash) / portfolio.initial_cash
    st.write(f"**总收益**: {total_return * 100:.2f}%")

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

    # 可视化投资组合价值变化
    st.subheader("投资组合价值变化")
    if not transactions:
        st.write("暂无交易记录，无法绘制投资组合价值变化。")
    else:
        transactions_df = transactions_df.sort_values(by='time')
        transactions_df['portfolio_value'] = portfolio.initial_cash
        for idx, row in transactions_df.iterrows():
            if row['type'] == 'buy':
                transactions_df.at[idx, 'portfolio_value'] -= row['price'] * row['quantity']
            elif row['type'] == 'sell':
                transactions_df.at[idx, 'portfolio_value'] += row['price'] * row['quantity']
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=transactions_df['time'], y=transactions_df['portfolio_value'],
                                 mode='lines+markers', name='Portfolio Value'))
        st.plotly_chart(fig)

    # 新增部分：当前持仓收益可视化
    st.subheader("当前持仓收益")

    if holdings:
        avg_costs = portfolio.get_average_cost()
        profit_data = []
        for symbol, qty in holdings.items():
            current_price = portfolio.latest_prices.get(symbol, 0.0)
            avg_cost = avg_costs.get(symbol, 0.0)
            profit = (current_price - avg_cost) * qty
            profit_data.append({
                'symbol': symbol,
                '数量': qty,
                '平均成本价': f"￥{avg_cost:,.2f}",
                '当前价格': f"￥{current_price:,.2f}",
                '收益': profit
            })
        profit_df = pd.DataFrame(profit_data).set_index('symbol')
        st.dataframe(profit_df)

    else:
        st.write("暂无持仓，无法展示收益。")

# 交易日志页面
with tab2:
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

# 实时交易页面
with tab3:
    st.header("实时交易")
    subtabs = st.tabs(["操作界面", "可视化界面"])
    with subtabs[0]:
        if st.button("计算交易信号"):
            st.session_state.signals = []  # 清空之前的信号
            st.session_state.log_messages = []  # 清空之前的日志
            perform_live_trading()

        st.subheader("当前信号")
        if st.session_state.signals:
            # 使用副本防止在迭代时修改列表
            for idx, signal in enumerate(st.session_state.signals.copy()):
                with st.expander(f"信号 {idx + 1} - {signal['time'].strftime('%Y-%m-%d %H:%M:%S')}"):
                    st.write(f"**类型**: {signal['type'].capitalize()}")
                    st.write(f"**股票代码**: {signal['symbol']}")
                    st.write(f"**价格**: ￥{signal['price']:,.2f}")
                    # 提供调整数量的输入框
                    new_quantity = st.number_input(f"调整 {signal['type']} 份额", min_value=1, value=int(signal['quantity']), key=f"qty_{idx}")
                    col1, col2 = st.columns(2)
                    with col1:
                        # 当用户确认买入或卖出
                        if st.button(f"确认 {signal['type'].capitalize()}", key=f"conf_{idx}"):
                            # 实际交易，不模拟费用和滑点
                            if signal['type'] == 'buy':
                                portfolio.buy_stock(signal['symbol'], signal['price'], new_quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                                st.session_state.trade_history.append({
                                    'symbol': signal['symbol'],
                                    'price': signal['price'],
                                    'quantity': new_quantity,
                                    'time': datetime.now(),
                                    'type': 'buy'  # 添加 'type' 字段
                                })
                                st.success(f"已买入 {new_quantity} 份 {signal['symbol']}")
                            elif signal['type'] == 'sell':
                                portfolio.sell_stock(signal['symbol'], signal['price'], new_quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                                st.session_state.trade_history.append({
                                    'symbol': signal['symbol'],
                                    'price': signal['price'],
                                    'quantity': new_quantity,
                                    'time': datetime.now(),
                                    'type': 'sell'  # 添加 'type' 字段
                                })
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

    with subtabs[1]:
        # 增加实时交易的日志展示
        st.subheader("实时交易日志")
        if st.session_state.log_messages:
            log_display = st.empty()
            for message in st.session_state.log_messages[-100:]:  # 显示最新100条日志
                log_display.write(message)
        else:
            st.write("暂无实时交易日志。")

        # 可视化交易过程和股票价格变动
        st.subheader("交易可视化")
        if st.session_state.trade_history:
            trade_df = pd.DataFrame(st.session_state.trade_history)
            trade_df['time'] = pd.to_datetime(trade_df['time'])
            symbols = trade_df['symbol'].unique().tolist()
            selected_symbol = st.selectbox("选择股票进行可视化", symbols)

            if selected_symbol:
                # 获取历史价格数据
                historical_data = all_stock_data(start_date="20220101", end_date=datetime.now().strftime("%Y%m%d"))
                if selected_symbol in historical_data:
                    df = historical_data[selected_symbol]
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df['date'], y=df['close'], mode='lines', name='收盘价'))

                    # 绘制买卖点
                    buys = trade_df[(trade_df['symbol'] == selected_symbol) & (trade_df['type'] == 'buy')]
                    sells = trade_df[(trade_df['symbol'] == selected_symbol) & (trade_df['type'] == 'sell')]

                    fig.add_trace(go.Scatter(
                        x=buys['time'],
                        y=buys['price'],
                        mode='markers',
                        marker=dict(color='green', size=10, symbol='triangle-up'),
                        name='买入'
                    ))

                    fig.add_trace(go.Scatter(
                        x=sells['time'],
                        y=sells['price'],
                        mode='markers',
                        marker=dict(color='red', size=10, symbol='triangle-down'),
                        name='卖出'
                    ))

                    fig.update_layout(title=f"{selected_symbol} 价格与交易信号",
                                      xaxis_title="时间",
                                      yaxis_title="价格 (元)")
                    st.plotly_chart(fig)
                else:
                    st.write(f"没有找到 {selected_symbol} 的历史数据。")
        else:
            st.write("暂无交易历史，无法进行可视化。")

        # 可视化价格更新
        st.subheader("价格更新可视化")
        if st.session_state.price_history:
            price_df = pd.DataFrame(st.session_state.price_history)
            price_df['time'] = pd.to_datetime(price_df['time'])
            symbols = price_df['symbol'].unique().tolist()
            selected_symbol_price = st.selectbox("选择股票查看价格变化", symbols, key='price_select')

            if selected_symbol_price:
                price_symbol_df = price_df[price_df['symbol'] == selected_symbol_price]
                price_symbol_df = price_symbol_df.sort_values(by='time')

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=price_symbol_df['time'], y=price_symbol_df['price'],
                                         mode='lines+markers', name='最新价格'))

                fig.update_layout(title=f"{selected_symbol_price} 最新价格变化",
                                  xaxis_title="时间",
                                  yaxis_title="价格 (元)")
                st.plotly_chart(fig)
        else:
            st.write("暂无价格更新记录。")

# 回测页面
with tab4:
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
            data_fetcher_instance = DataFetcher(
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )
            data = data_fetcher_instance.fetch_all_data(start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"))

            strategies = [
                StrategyFactory.get_strategy(cfg['name'], weight=cfg.get('weight', 1.0), **cfg['params']) for cfg in STRATEGY_CONFIGS
            ]
            combined_strategy = CombinedStrategy(strategies)  # 不限制 top_n

            backtester = Backtester(combined_strategy, data)
            results = backtester.run_backtest()
        st.success(f"回测完成，收益: {results['total_return']*100:.2f}%")
        st.write("回测结果:", results)
        st.rerun()

    # 显示最新回测结果
    st.subheader("最新回测结果")
    backtest_result_path = Path(BACKTRACE_FILE)
    if backtest_result_path.exists():
        with open(backtest_result_path, 'r') as f:
            backtest_results = json.load(f)
        st.write(f"**初始资金**: ￥{backtest_results['initial_cash']:,.2f}")
        st.write(f"**最终组合价值**: ￥{backtest_results['final_portfolio_value']:,.2f}")
        st.write(f"**总收益**: {backtest_results['total_return']*100:.2f}%")
        st.subheader("回测交易记录")
        transactions_df = pd.DataFrame(backtest_results['transactions'])
        transactions_df['time'] = pd.to_datetime(transactions_df['time'])
        transactions_df = transactions_df.sort_values(by='time', ascending=False)
        st.dataframe(transactions_df)
    else:
        st.write("暂无回测结果。")

# 设置页面
with tab5:
    st.header("系统设置")

    # 显示当前配置
    st.subheader("当前策略配置与权重")
    for cfg in STRATEGY_CONFIGS:
        st.write(f"### {cfg['name']} - 权重: {cfg.get('weight', 1.0)}")
        for key, value in cfg['params'].items():
            st.write(f"- **{key}**: {value}")

    st.subheader("修改交易参数")
    # 示例：修改初始现金
    new_initial_cash = st.number_input("初始现金金额", value=portfolio.initial_cash, min_value=0, step=1000)
    if st.button("更新初始现金"):
        portfolio.initial_cash = new_initial_cash
        portfolio.cash = new_initial_cash
        portfolio.save_portfolio()
        st.success(f"初始现金已更新为 ￥{new_initial_cash:,.2f}")
        st.rerun()