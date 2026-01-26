import pandas as pd
import numpy as np
from simple_quant.events import SignalEvent, FillEvent, OrderEvent, EventType
from simple_quant.portfolio.base import Portfolio
from simple_quant.data.base import DataHandler
from queue import Queue
from collections import defaultdict
from typing import Dict, List, Optional

class RobustPortfolio(Portfolio):
    """
    A robust portfolio class that handles:
    1. Realistic order execution (checking cash balance).
    2. Proper Exit logic.
    3. Accurate fill pricing logic (using trade price vs closing price).
    4. Performance statistics calculation.
    """

    def __init__(self, bars: DataHandler, events: Queue, start_date, initial_capital=100000.0):
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list
        self.start_date = start_date
        self.initial_capital = initial_capital
        
        # 使用 List 记录历史状态
        self.all_positions = self.construct_all_positions()
        self.all_holdings = self.construct_all_holdings()
        
        # 使用 Dict 维护当前实时状态
        self.current_positions = dict((s, 0) for s in self.symbol_list)
        self.current_holdings = self.construct_current_holdings()
        self.equity_curve = None
        self.trade_history = []  # Store individual trade details for analysis/visualization

    def construct_all_positions(self):
        d = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        d['datetime'] = self.start_date
        return [d]

    def construct_all_holdings(self):
        d = dict((k, v) for k, v in [(s, 0.0) for s in self.symbol_list])
        d['datetime'] = self.start_date
        d['cash'] = self.initial_capital
        d['commission'] = 0.0
        d['total'] = self.initial_capital
        return [d]

    def construct_current_holdings(self):
        d = dict((k, v) for k, v in [(s, 0.0) for s in self.symbol_list])
        d['cash'] = self.initial_capital
        d['commission'] = 0.0
        d['total'] = self.initial_capital
        return d

    def update_timeindex(self, event):
        """
        每日结算逻辑：
        通常在新的 MarketEvent 到达时（意味着新的一天开始），或者显式地在一天结束后调用。
        它负责将 'current' 的状态快照保存到 'all' 历史列表中。
        """
        # 获取最新的时间戳
        latest_datetime = self.bars.get_latest_bar_datetime(self.symbol_list[0])

        # 1. 快照 Positions
        dp = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        dp['datetime'] = latest_datetime
        for s in self.symbol_list:
            dp[s] = self.current_positions[s]
        self.all_positions.append(dp)

        # 2. 快照 Holdings & 计算当日市值 (Mark-to-Market)
        dh = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        dh['datetime'] = latest_datetime
        dh['cash'] = self.current_holdings['cash']
        dh['commission'] = self.current_holdings['commission']
        dh['total'] = self.current_holdings['cash']

        for s in self.symbol_list:
            # 尝试获取最新收盘价计算市值
            market_price = self.bars.get_latest_bar_value(s, "Close")
            if market_price is None or np.isnan(market_price):
                 # 如果取不到今天的（比如停牌），取昨天的持有市值
                market_value = self.current_holdings[s] 
            else:
                market_value = self.current_positions[s] * market_price
            
            dh[s] = market_value
            dh['total'] += market_value

        self.current_holdings['total'] = dh['total'] # 更新当前总资产
        self.all_holdings.append(dh)

    # ========================================================
    # 核心修改：生成订单逻辑 (加入风控)
    # ========================================================
    def update_signal(self, event: SignalEvent):
        """
        Handles SignalEvent by rebalancing the portfolio to the target weight.
        
        Logic:
        1. Calculate Current Total Equity (Cash + Market Value of all positions).
        2. Determine Target Value for the symbol: Total Equity * event.strength.
           (If type is EXIT, target is 0).
        3. Calculate Current Value for the symbol.
        4. Determine Difference (Target - Current).
        5. Generate Order (Buy/Sell) to close the gap.
        """
        if event.type == EventType.SIGNAL:
            symbol = event.symbol
            order_type = 'MKT'
            
            # 1. Get Current Price
            current_price = self.bars.get_latest_bar_value(symbol, "Close")
            if current_price is None or current_price == 0:
                return # Cannot trade without price

            # 2. Calculate Total Equity
            # We assume self.current_holdings['total'] is updated daily. 
            # Ideally, for intraday rebalancing, we should recalc total equity using live prices.
            # Here we recalc it quickly to be safe.
            current_equity = self.current_holdings['cash']
            for s in self.symbol_list:
                price = self.bars.get_latest_bar_value(s, "Close")
                qty = self.current_positions.get(s, 0)
                if price and qty != 0:
                    current_equity += qty * price
            
            # 3. Determine Target Weight & Value
            if event.signal_type == 'EXIT':
                target_weight = 0.0
            else:
                # Interpret 'strength' as target portfolio percentage (e.g. 0.10 for 10%)
                target_weight = event.strength
                
            target_value = current_equity * target_weight
            
            # 4. Calculate Current Value
            current_qty = self.current_positions.get(symbol, 0)
            current_value = current_qty * current_price
            
            # 5. Calculate Difference
            diff_value = target_value - current_value
            
            # 6. Generate Order
            # Calculate quantity needed to change
            # Use int() to truncate to whole shares (or 100s if market requires)
            quantity_to_trade = int(diff_value / current_price)
            
            # Round to nearest 100 for A-shares style (optional, but good for realism)
            # For this 'learning' phase, simpler is better, but let's stick to 100 if buying.
            # Selling odd lots is usually allowed, buying usually 100 multiples.
            # Let's just use raw integer quantity for precision in backtest.
            
            if quantity_to_trade == 0:
                return

            if quantity_to_trade > 0:
                direction = 'BUY'
                # Check cash constraint
                cost = quantity_to_trade * current_price
                if cost > self.current_holdings['cash']:
                    # Adjust to max affordable
                    quantity_to_trade = int(self.current_holdings['cash'] / current_price)
                    if quantity_to_trade == 0:
                        return
            else:
                direction = 'SELL'
                quantity_to_trade = abs(quantity_to_trade)
                # Cap sell at current holding (just in case of float errors)
                if quantity_to_trade > abs(current_qty):
                    quantity_to_trade = abs(current_qty)

            if quantity_to_trade > 0:
                order = OrderEvent(
                    symbol=symbol, 
                    quantity=quantity_to_trade, 
                    direction=direction, 
                    order_type=order_type
                )
                self.events.put(order)
                print(f"[Rebalance] {symbol}: CurPct={current_value/current_equity:.1%} -> TgtPct={target_weight:.1%} | Action: {direction} {quantity_to_trade} @ {current_price:.2f}")

    # ========================================================
    # 核心修改：成交更新逻辑 (使用真实价格)
    # ========================================================
    def update_fill(self, event: FillEvent):
        if event.type == EventType.FILL:
            fill_dir = 0
            if event.direction == 'BUY':
                fill_dir = 1
            if event.direction == 'SELL':
                fill_dir = -1
            
            # 1. 优先从 Event 中获取真实的成交价 (Model Fill Price)
            # 如果 event 中没有 price 字段，再降级使用 Close
            fill_price = getattr(event, 'price', None)
            if fill_price is None:
                fill_price = self.bars.get_latest_bar_value(event.symbol, "Close")

            # 2. 更新持仓数量
            self.current_positions[event.symbol] += fill_dir * event.quantity

            # 3. 更新资金变动 (Cash)
            cost = fill_dir * fill_price * event.quantity
            self.current_holdings['cash'] -= (cost + event.commission)
            self.current_holdings['commission'] += event.commission
            
            # Record trade for visualization
            self.trade_history.append({
                'datetime': self.bars.get_latest_bar_datetime(event.symbol),
                'symbol': event.symbol,
                'action': event.direction, # 'BUY' or 'SELL'
                'quantity': event.quantity,
                'price': fill_price,
                'commission': event.commission,
                'cost': cost
            })
            
            # 注意：这里不再去重算 'total' equity。
            # 因为 'total' 包含浮动盈亏，应该由 update_timeindex 在日结时统一计算，
            # 避免盘中每笔交易都遍历所有股票。

    # ========================================================
    # 统计指标计算部分 (保持原逻辑，增强健壮性)
    # ========================================================
    def create_equity_curve_dataframe(self):
        curve = pd.DataFrame(self.all_holdings)
        curve.set_index('datetime', inplace=True)
        curve['returns'] = curve['total'].pct_change()
        curve['equity_curve'] = (1.0 + curve['returns']).cumprod()
        self.equity_curve = curve

    def output_summary_stats(self):
        # 确保有数据才计算
        if not hasattr(self, 'equity_curve') or self.equity_curve.empty:
            return []

        total_return = self.equity_curve['equity_curve'].iloc[-1]
        returns = self.equity_curve['returns']
        pnl = self.equity_curve['total']
        
        sharp_ratio = self.create_sharpe_ratio(returns)
        max_dd, dd_duration = self.create_drawdowns(pnl)
        
        calmar_ratio = self.create_calmar_ratio(total_return, max_dd)
        sortino_ratio = self.create_sortino_ratio(returns)
        stability_score = self.create_stability_score(sharp_ratio, max_dd)

        stats = [
            ("Total Return", "%0.2f%%" % ((total_return - 1.0) * 100.0)),
            ("Sharpe Ratio", "%0.2f" % sharp_ratio),
            ("Sortino Ratio", "%0.2f" % sortino_ratio),
            ("Calmar Ratio", "%0.2f" % calmar_ratio),
            ("Max Drawdown", "%0.2f%%" % (max_dd * 100.0)),
            ("Drawdown Duration", "%d" % dd_duration),
            ("Stability Score", "%0.2f" % stability_score)
        ]
        return stats  
    
    def create_sharpe_ratio(self, returns, periods=252):
        std = np.std(returns)
        if std == 0: return 0.0
        return np.sqrt(periods) * (np.mean(returns)) / std

    def create_sortino_ratio(self, returns, periods=252):
        downside_returns = returns[returns < 0]
        downside_std = np.std(downside_returns)
        if downside_std == 0: return 0.0
        return np.sqrt(periods) * (np.mean(returns)) / downside_std

    def create_calmar_ratio(self, total_return, max_dd, years=1):
        if max_dd == 0: return 0.0
        try:
            duration = (self.equity_curve.index[-1] - self.equity_curve.index[0]).days / 365.25
            if duration < 0.1: duration = 0.1
        except:
            duration = 1.0
        
        # 防止 returns 为负数时求幂报错
        if total_return < 0: return -1.0 
        annualized_return = (total_return) ** (1/duration) - 1
        return annualized_return / max_dd

    def create_stability_score(self, sharpe, max_dd):
        if max_dd > 1.0: max_dd = 1.0
        return sharpe * (1.0 - max_dd)

    def create_drawdowns(self, pnl):
        hwm = [0]
        eq_idx = pnl.index
        drawdown = pd.Series(index = eq_idx)
        duration = pd.Series(0, index = eq_idx)

        for t in range(1, len(eq_idx)):
            hwm.append(max(hwm[t-1], pnl.iloc[t]))
            # 只有当 hwm > 0 时才算 drawdown，防止初始资金为0的情况（虽不常见）
            if hwm[t] > 0:
                drawdown.iloc[t] = (hwm[t] - pnl.iloc[t]) / hwm[t]
            else:
                drawdown.iloc[t] = 0
            
            duration.iloc[t] = (0 if drawdown.iloc[t] == 0 else duration.iloc[t-1]+1)

        return drawdown.max(), duration.max()