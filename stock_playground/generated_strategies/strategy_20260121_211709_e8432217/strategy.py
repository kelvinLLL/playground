"""
Strategy Generated at: 2026-01-21 21:17:09
Prompt: Simple Moving Average Crossover 5 and 20
"""


from simple_quant.strategy.base import Strategy
from simple_quant.events import SignalEvent
import numpy as np

class GeneratedStrategy(Strategy):
    def __init__(self, bars, events):
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list
        self.bought = {s: 'OUT' for s in self.symbol_list}
        
    def calculate_signals(self, event):
        if event.type == 'MARKET':
            for s in self.symbol_list:
                bars = self.bars.get_latest_bars_values(s, "Close", N=20)
                if len(bars) < 20:
                    continue
                    
                # Simple Momentum / Mean Reversion Hybrid
                # If price is above 20-day MA, buy
                ma20 = np.mean(bars)
                price = bars[-1]
                
                dt = self.bars.get_latest_bar_datetime(s)
                
                if price > ma20 and self.bought[s] == 'OUT':
                    print(f"LONG: {s} at {dt}")
                    self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='LONG', strength=1.0))
                    self.bought[s] = 'LONG'
                elif price < ma20 and self.bought[s] == 'LONG':
                    print(f"EXIT: {s} at {dt}")
                    self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='EXIT', strength=1.0))
                    self.bought[s] = 'OUT'
