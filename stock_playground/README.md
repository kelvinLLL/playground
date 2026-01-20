Simple Quant 项目代码走读
一、项目概述
项目名称: simple_quant - 事件驱动量化交易回测框架
核心架构: 采用事件驱动模式，支持策略回测、风险管理和性能分析
技术栈: Python, Pandas, NumPy, Pydantic
---
二、数据源
2.1 数据获取 (stock_playground/scripts/fetch_data.py)
数据源: Yahoo Finance (通过 yfinance 库)
支持市场: 
- 中国A股（上海交易所：.SS 后缀）
- 美股（如 AAPL）
- 其他 Yahoo Finance 支持的市场
数据字段:
Date, Open, High, Low, Close, Volume, Adj Close
获取流程:
# 第14行：下载数据
df = yf.download(symbol, start=start_date, end=end_date)
# 第36-40行：标准化列名
required_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
示例数据 (stock_playground/data/600519.SS.csv):
- 贵州茅台 (600519.SS) 2024年数据
- 中国平安 (601318.SS) 2024年数据
- 也可以生成模拟数据 (AAPL) 用于测试 (generate_data.py)
2.2 数据处理 (stock_playground/simple_quant/data/csv_data.py)
核心类: HistoricCSVDataHandler
主要功能:
1. 读取CSV文件到 pandas DataFrame
2. 按时间线重新索引，确保所有股票对齐
3. 使用迭代器模式逐条提供数据（模拟实时行情）
关键方法:
- _open_convert_csv_files() (第37-68行): 
  - 加载CSV文件
  - 使用 reindex() 和 pad 方法填充缺失数据
  - 将 DataFrame 转换为迭代器
# 第68行：关键 - 转换为迭代器用于逐条读取
self.symbol_data[s] = self.symbol_data[s].reindex(
    index=comb_index, method='pad'
).iterrows()
- update_bars() (第140-155行): 
  - 逐个时间步前进
  - 生成 MarketEvent 事件
  - 所有符号同步更新
# 第147行：获取下一根K线
bar = next(self.symbol_data[s])
# 第155行：推送市场事件
self.events.put(MarketEvent())
---
三、核心算法
3.1 移动平均线交叉策略 (stock_playground/simple_quant/strategy/std_strategies.py)
类: MovingAverageCrossStrategy (第6-38行)
算法逻辑:
# 第26-27行：计算双均线
short_sma = np.mean(bars[-self.short_window:])  # 短期均线
long_sma = np.mean(bars[-self.long_window:])    # 长期均线
# 第31行：金叉买入信号
if short_sma > long_sma and self.bought[s] == 'OUT':
    # 生成买入信号
# 第35行：死叉卖出信号  
elif short_sma < long_sma and self.bought[s] == 'LONG':
    # 生成卖出信号
参数:
- short_window: 默认 10
- long_window: 默认 30
信号类型:
- LONG: 买入（金叉）
- EXIT: 卖出（死叉）
3.2 RSI 相对强弱策略 (stock_playground/simple_quant/strategy/std_strategies.py)
类: RSIStrategy (第40-115行)
算法逻辑 (简化版 RSI 计算):
# 第82-84行：计算涨跌
deltas = np.diff(prices)
gains = np.where(deltas > 0, deltas, 0)
losses = np.where(deltas < 0, -deltas, 0)
# 第86-90行：计算 RSI
avg_gain = np.mean(gains)
avg_loss = np.mean(losses)
rs = avg_gain / avg_loss if avg_loss != 0 else 0
rsi = 100 - (100 / (1 + rs))
交易规则:
# 第108行：超卖买入
if rsi < buy_threshold and self.bought[s] == 'OUT':
    # 生成买入信号
# 第112行：超买卖出
elif rsi > sell_threshold and self.bought[s] == 'LONG':
    # 生成卖出信号
参数:
- period: RSI周期，默认 14
- buy_threshold: 买入阈值，默认 30（超卖）
- sell_threshold: 卖出阈值，默认 70（超买）
---
四、事件驱动架构
4.1 事件类型 (stock_playground/simple_quant/events.py)
事件枚举 (第6-10行):
class EventType(str, Enum):
    MARKET = "MARKET"   # 市场数据更新
    SIGNAL = "SIGNAL"   # 策略信号
    ORDER = "ORDER"     # 订单
    FILL = "FILL"       # 成交
事件类层次:
- Event (基类) - 包含类型和时间戳
- MarketEvent - 市场数据事件
- SignalEvent - 策略信号 (symbol, signal_type, strength)
- OrderEvent - 订单 (symbol, quantity, direction, order_type)
- FillEvent - 成交 (symbol, quantity, fill_cost, commission)
4.2 回测引擎 (stock_playground/simple_quant/engine.py)
类: BacktestEngine (第9-97行)
核心循环 (_run_backtest(), 第44-80行):
while True:
    # 1. 获取市场数据
    if self.data_handler.continue_backtest:
        self.data_handler.update_bars()
    else:
        break
    
    # 2. 处理事件队列
    while True:
        event = self.events.get()
        
        if event.type == MARKET:
            # 策略计算信号，投资组合更新时间
            self.strategy.calculate_signals(event)
            self.portfolio.update_timeindex(event)
        
        elif event.type == SIGNAL:
            # 投资组合处理信号，生成订单
            self.portfolio.update_signal(event)
        
        elif event.type == ORDER:
            # 执行器处理订单，生成成交
            self.execution_handler.execute_order(event)
        
        elif event.type == FILL:
            # 投资组合更新持仓
            self.portfolio.update_fill(event)
流程图:
CSV数据 → MarketEvent → Strategy → SignalEvent 
                                    → OrderEvent → FillEvent → Portfolio
---
五、投资组合管理
5.1 持仓跟踪 (stock_playground/simple_quant/portfolio/simple.py)
类: NaivePortfolio
核心数据结构:
- current_positions: 当前持仓 {symbol: quantity}
- current_holdings: 当前资产 {symbol: value, cash: cash, total: total}
- all_positions: 历史持仓列表
- all_holdings: 历史资产列表
关键方法:
- update_timeindex() (第67-100行): 
  - 每个时间步更新
  - 计算当前市值
# 第96行：计算单个股票市值
market_value = self.current_positions[s] * self.bars.get_latest_bar_value(s, "Close")
# 第98行：累加总资产
dh['total'] += market_value
- update_signal() (第102-130行): 
  - 将信号转换为订单
  - 固定数量 100 股（第111行）
- update_fill() (第132-155行): 
  - 处理成交
  - 更新现金和持仓
# 第145行：更新持仓
self.current_positions[event.symbol] += fill_dir * event.quantity
# 第151行：更新现金
self.current_holdings['cash'] -= (cost + event.commission)
5.2 交易执行 (stock_playground/simple_quant/execution/backtest.py)
类: SimulatedExecutionHandler
简化假设 (第25-48行):
- 无延迟：订单立即成交
- 无滑点：以收盘价成交
- 固定手续费：max(1.0, 0.005 * quantity) (参考IB标准)
# 第36行：以收盘价成交
fill_price = self.bars.get_latest_bar_value(event.symbol, "Close")
# 第46行：计算手续费
commission = max(1.0, 0.005 * event.quantity)
---
六、输出交付
6.1 性能统计 (stock_playground/simple_quant/portfolio/simple.py)
output_summary_stats() (第168-184行):
输出指标:
1. 总收益率 (Total Return): (最终资产 / 初始资产 - 1) * 100%
2. 夏普比率 (Sharpe Ratio): √252 × mean(returns) / std(returns)
3. 最大回撤 (Max Drawdown): 峰值到谷底的最大跌幅
4. 回撤持续时间 (Drawdown Duration): 最大回撤的持续天数
计算细节:
- 夏普比率 (第187-192行):
def create_sharpe_ratio(self, returns, periods=252):
    return np.sqrt(periods) * (np.mean(returns)) / np.std(returns)
- 最大回撤 (第194-212行):
# 维护高水位线
hwm.append(max(hwm[t-1], pnl.iloc[t]))
# 计算回撤
drawdown.iloc[t] = (hwm[t] - pnl.iloc[t]) / hwm[t]
6.2 资金曲线 (create_equity_curve_dataframe(), 第157-166行)
生成 DataFrame 包含:
- datetime: 时间索引
- 各股票市值
- cash: 现金
- total: 总资产
- returns: 收益率
- equity_curve: 累积收益曲线
# 第164行：计算收益率
curve['returns'] = curve['total'].pct_change()
# 第165行：计算累积收益
curve['equity_curve'] = (1.0 + curve['returns']).cumprod()
6.3 运行示例 (stock_playground/run_strategies.py)
第42-47行: 运行两个策略
# 双均线交叉 (10日/30日)
run_strategy(MovingAverageCrossStrategy, "Dual SMA (10/30)", 
             symbol_list, short_window=10, long_window=30)
# RSI (14日, 30/70阈值)
run_strategy(RSIStrategy, "RSI (14, 30/70)", 
             symbol_list, period=14, buy_threshold=30, sell_threshold=70)
输出示例:
Performance Statistics:
Total Return: 12.34%
Sharpe Ratio: 1.23
Max Drawdown: -5.67%
Drawdown Duration: 15
Final Portfolio Value: 112340.56
---
七、项目结构总结
stock_playground/
├── simple_quant/
│   ├── __init__.py
│   ├── events.py           # 事件系统定义
│   ├── engine.py           # 回测引擎
│   ├── data/
│   │   ├── base.py         # 数据处理抽象类
│   │   └── csv_data.py     # CSV数据处理器
│   ├── strategy/
│   │   ├── base.py         # 策略抽象类
│   │   ├── examples.py     # 示例策略
│   │   └── std_strategies.py # 标准策略 (MA, RSI)
│   ├── portfolio/
│   │   ├── base.py         # 投资组合抽象类
│   │   └── simple.py       # 简单投资组合实现
│   └── execution/
│       ├── base.py         # 执行抽象类
│       └── backtest.py     # 回测执行器
├── scripts/
│   └── fetch_data.py       # 数据获取脚本
├── data/                   # 数据目录
│   ├── 600519.SS.csv
│   └── 601318.SS.csv
├── run_strategies.py       # 策略运行入口
├── run_backtest.py         # 回测运行入口
└── generate_data.py        # 模拟数据生成
---
八、关键设计模式
1. 事件驱动架构: 所有组件通过事件队列通信，解耦度高
2. 策略模式: 策略可以轻松替换和扩展
3. 迭代器模式: 数据逐条读取，模拟实时交易
4. 抽象工厂模式: 通过抽象基类定义接口，支持多种实现
---
九、扩展性
易于扩展的部分:
- 新策略：继承 Strategy 类
- 新数据源：继承 DataHandler 类
- 新执行逻辑：继承 ExecutionHandler 类
- 新风险管理：继承 Portfolio 类
待优化部分:
- 固定仓位管理（第111行：quantity=100）
- 简化手续费模型
- 无滑点模拟
- RSI 计算简化版（建议使用完整 Wilder's smoothing）