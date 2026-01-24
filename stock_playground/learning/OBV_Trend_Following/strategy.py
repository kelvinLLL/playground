
import numpy as np
from simple_quant.strategy.base import Strategy
from simple_quant.events import SignalEvent

class OBVTrendStrategy(Strategy):
    """
    On-Balance Volume (OBV) Trend Following Strategy.
    
    Logic:
    1. Calculate OBV for the entire available history up to now.
    2. Calculate SMA of OBV (e.g., 20 periods).
    3. Buy when OBV crosses above SMA.
    4. Sell when OBV crosses below SMA.
    """
    
    def __init__(self, bars, events, obv_window=20):
        self.bars = bars
        self.events = events
        self.obv_window = obv_window
        self.symbol_list = self.bars.symbol_list
        self.bought = dict((s, 'OUT') for s in self.symbol_list)
        
    def calculate_obv(self, prices, volumes):
        """
        Calculates OBV series from price and volume arrays.
        """
        # We need at least 2 data points to calc diff
        if len(prices) < 2:
            return np.zeros(len(prices))
            
        # Calculate price changes
        # sign: 1 if up, -1 if down, 0 if flat
        change = np.diff(prices)
        direction = np.sign(change) 
        
        # Volume flow: direction * volume[1:] 
        # (volume matches the 'change' index, which starts from 2nd bar)
        flow = direction * volumes[1:]
        
        # Cumulative sum to get OBV
        # Insert 0 at start to match original length (first bar OBV is 0 or undefined, let's say 0)
        obv = np.concatenate(([0], np.cumsum(flow)))
        return obv

    def calculate_signals(self, event):
        if event.type == 'MARKET':
            for s in self.symbol_list:
                # 1. Get History
                # We need enough bars to calc OBV and then its SMA
                # Let's request a large window to ensure we have trend context
                # Ideally, the data handler gives us everything available so far
                # But for optimization, we request N = obv_window + 50
                window_size = self.obv_window + 100 
                
                closes = self.bars.get_latest_bars_values(s, "Close", N=window_size)
                volumes = self.bars.get_latest_bars_values(s, "Volume", N=window_size)
                
                if len(closes) < self.obv_window + 2:
                    continue
                    
                # 2. Calculate OBV
                obv_series = self.calculate_obv(closes, volumes)
                
                # 3. Calculate SMA of OBV
                # We only need the last few points to determine cross
                obv_sma_series = np.convolve(obv_series, np.ones(self.obv_window)/self.obv_window, mode='valid')
                
                # Align series:
                # obv_series length: N
                # obv_sma_series length: N - window + 1
                # The last element of obv_sma_series corresponds to the last element of obv_series
                
                current_obv = obv_series[-1]
                current_obv_ma = obv_sma_series[-1]
                
                # Check previous bar for crossover detection
                prev_obv = obv_series[-2]
                prev_obv_ma = obv_sma_series[-2]
                
                dt = self.bars.get_latest_bar_datetime(s)
                
                # 4. Signal Logic: Crossover
                
                # GOLDEN CROSS: OBV goes above MA
                if current_obv > current_obv_ma and prev_obv <= prev_obv_ma:
                    if self.bought[s] == 'OUT':
                        print(f"LONG (OBV Breakout): {s} at {dt} | OBV: {current_obv:.0f} > MA: {current_obv_ma:.0f}")
                        self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='LONG', strength=1.0))
                        self.bought[s] = 'LONG'
                        
                # DEATH CROSS: OBV falls below MA
                elif current_obv < current_obv_ma and prev_obv >= prev_obv_ma:
                    if self.bought[s] == 'LONG':
                        print(f"EXIT (OBV Breakdown): {s} at {dt} | OBV: {current_obv:.0f} < MA: {current_obv_ma:.0f}")
                        self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='EXIT', strength=1.0))
                        self.bought[s] = 'OUT'
