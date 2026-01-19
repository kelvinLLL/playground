import pandas as pd
from simple_quant.events import SignalEvent, FillEvent, OrderEvent, EventType
from simple_quant.portfolio.base import Portfolio
from simple_quant.data.base import DataHandler
from queue import Queue
from collections import defaultdict
from typing import Dict, List

class NaivePortfolio(Portfolio):
    """
    The NaivePortfolio object is designed to send orders to
    a brokerage object with a constant quantity size blindly,
    i.e. without any risk management or position sizing. It is
    used to test simpler strategies such as BuyAndHoldStrategy.
    """

    def __init__(self, bars: DataHandler, events: Queue, start_date, initial_capital=100000.0):
        """
        Initializes the portfolio with bars and an event queue. 
        Also includes a starting timestamp and initial capital. 
        The absolute values of which are not important.
        """
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list
        self.start_date = start_date
        self.initial_capital = initial_capital
        
        self.all_positions = self.construct_all_positions()
        self.current_positions = dict( (k,v) for k, v in [(s, 0) for s in self.symbol_list] )
        
        self.all_holdings = self.construct_all_holdings()
        self.current_holdings = self.construct_current_holdings()

    def construct_all_positions(self):
        """
        Constructs the positions list using the start_date
        to determine when the time index will begin.
        """
        d = dict( (k,v) for k, v in [(s, 0) for s in self.symbol_list] )
        d['datetime'] = self.start_date
        return [d]

    def construct_all_holdings(self):
        """
        Constructs the holdings list using the start_date
        to determine when the time index will begin.
        """
        d = dict( (k,v) for k, v in [(s, 0.0) for s in self.symbol_list] )
        d['datetime'] = self.start_date
        d['cash'] = self.initial_capital
        d['commission'] = 0.0
        d['total'] = self.initial_capital
        return [d]

    def construct_current_holdings(self):
        """
        This constructs the dictionary which will hold the instantaneous
        value of the portfolio across all symbols.
        """
        d = dict( (k,v) for k, v in [(s, 0.0) for s in self.symbol_list] )
        d['cash'] = self.initial_capital
        d['commission'] = 0.0
        d['total'] = self.initial_capital
        return d

    def update_timeindex(self, event):
        """
        Adds a new record to the positions matrix for the current 
        market data bar. This reflects the PREVIOUS bar, i.e. all
        current market data at this stage is known (OLHCVI).
        
        Makes use of a MarketEvent from the events queue.
        """
        latest_datetime = self.bars.get_latest_bar_datetime(self.symbol_list[0])

        # Update positions
        dp = dict( (k,v) for k, v in [(s, 0) for s in self.symbol_list] )
        dp['datetime'] = latest_datetime

        for s in self.symbol_list:
            dp[s] = self.current_positions[s]

        # Append the current positions
        self.all_positions.append(dp)

        # Update holdings
        dh = dict( (k,v) for k, v in [(s, 0) for s in self.symbol_list] )
        dh['datetime'] = latest_datetime
        dh['cash'] = self.current_holdings['cash']
        dh['commission'] = self.current_holdings['commission']
        dh['total'] = self.current_holdings['cash']

        for s in self.symbol_list:
            # Approximation to the real value
            market_value = self.current_positions[s] * self.bars.get_latest_bar_value(s, "Close")
            dh[s] = market_value
            dh['total'] += market_value

        self.all_holdings.append(dh)

    def update_signal(self, event: SignalEvent):
        """
        Acts on a SignalEvent to generate new orders 
        based on the portfolio logic.
        """
        # Generate an OrderEvent
        order = None
        if event.type == EventType.SIGNAL:
            order_type = 'MKT'
            quantity = 100 # TODO: Sizing
            direction = event.signal_type
            
            # Simple logic for now: Buy/Sell fixed quantity 
            # (In reality, we would check cash balance here)
            
            if direction == 'EXIT':
                # Exit specific handling (e.g. close all)
                pass # TODO
            else:
                o_dir = 'BUY' if direction == 'LONG' else 'SELL'
                order = OrderEvent(
                    symbol=event.symbol, 
                    quantity=quantity, 
                    direction=o_dir,
                    order_type=order_type
                )

        if order is not None:
            self.events.put(order)

    def update_fill(self, event: FillEvent):
        """
        Updates the portfolio current positions and holdings 
        from a FillEvent.
        """
        if event.type == EventType.FILL:
            fill_dir = 0
            if event.direction == 'BUY':
                fill_dir = 1
            if event.direction == 'SELL':
                fill_dir = -1
            
            # Update positions list
            self.current_positions[event.symbol] += fill_dir * event.quantity

            # Update holdings list
            fill_cost = self.bars.get_latest_bar_value(event.symbol, "Close") # Use current close as fill price estimate if not provided
            cost = fill_dir * fill_cost * event.quantity
            self.current_holdings[event.symbol] = self.current_positions[event.symbol] * fill_cost # This is approximate re-val
            self.current_holdings['cash'] -= (cost + event.commission)
            self.current_holdings['commission'] += event.commission
            self.current_holdings['total'] = self.current_holdings['cash'] + sum(
                self.current_positions[s] * self.bars.get_latest_bar_value(s, "Close") for s in self.symbol_list
            )

    def create_equity_curve_dataframe(self):
        """
        Creates a pandas DataFrame from the all_holdings
        list of dictionaries.
        """
        curve = pd.DataFrame(self.all_holdings)
        curve.set_index('datetime', inplace=True)
        curve['returns'] = curve['total'].pct_change()
        curve['equity_curve'] = (1.0 + curve['returns']).cumprod()
        self.equity_curve = curve

    def output_summary_stats(self):
        """
        Creates a list of summary statistics for the portfolio.
        """
        total_return = self.equity_curve['equity_curve'].iloc[-1]
        returns = self.equity_curve['returns']
        pnl = self.equity_curve['total']
        
        sharp_ratio = self.create_sharpe_ratio(returns)
        max_dd, dd_duration = self.create_drawdowns(pnl)

        stats = [
            ("Total Return", "%0.2f%%" % ((total_return - 1.0) * 100.0)),
            ("Sharpe Ratio", "%0.2f" % sharp_ratio),
            ("Max Drawdown", "%0.2f%%" % (max_dd * 100.0)),
            ("Drawdown Duration", "%d" % dd_duration)
        ]
        return stats  
    
    def create_sharpe_ratio(self, returns, periods=252):
        """
        Create the Sharpe ratio for the strategy, based on a 
        benchmark of zero (i.e. no risk-free rate information).
        """
        return np.sqrt(periods) * (np.mean(returns)) / np.std(returns)

    def create_drawdowns(self, pnl):
        """
        Calculate the largest peak-to-trough drawdown of the PnL curve
        as well as the duration of the drawdown.
        """
        # Calculate the cumulative returns curve 
        # and set up the High Water Mark
        hwm = [0]
        eq_idx = pnl.index
        drawdown = pd.Series(index = eq_idx)
        duration = pd.Series(0, index = eq_idx)

        # Loop over the index range
        for t in range(1, len(eq_idx)):
            hwm.append(max(hwm[t-1], pnl.iloc[t]))
            drawdown.iloc[t] = (hwm[t] - pnl.iloc[t]) / hwm[t]
            duration.iloc[t] = (0 if drawdown.iloc[t] == 0 else duration.iloc[t-1]+1)

        return drawdown.max(), duration.max()

import numpy as np
