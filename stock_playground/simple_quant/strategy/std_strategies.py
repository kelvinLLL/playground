
from simple_quant.strategy.base import Strategy
from simple_quant.events import SignalEvent, EventType
import numpy as np

class MovingAverageCrossStrategy(Strategy):
    """
    Standard Dual Moving Average Crossover Strategy.
    Long when Short MA > Long MA.
    Exit when Short MA < Long MA.
    """
    def __init__(self, bars, events, short_window=10, long_window=50):
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.short_window = short_window
        self.long_window = long_window
        self.bought = {s: 'OUT' for s in self.symbol_list}

    def calculate_signals(self, event):
        if event.type == EventType.MARKET:
            for s in self.symbol_list:
                bars = self.bars.get_latest_bars_values(s, "Close", N=self.long_window)
                
                if bars is not None and len(bars) >= self.long_window:
                    short_sma = np.mean(bars[-self.short_window:])
                    long_sma = np.mean(bars[-self.long_window:])
                    
                    dt = self.bars.get_latest_bar_datetime(s)
                    
                    if short_sma > long_sma and self.bought[s] == 'OUT':
                        print(f"LONG: {s} at {dt}")
                        self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='LONG', strength=1.0))
                        self.bought[s] = 'LONG'
                    elif short_sma < long_sma and self.bought[s] == 'LONG':
                        print(f"EXIT: {s} at {dt}")
                        self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='EXIT', strength=1.0))
                        self.bought[s] = 'OUT'

class RSIStrategy(Strategy):
    """
    RSI Mean Reversion Strategy.
    Buy when RSI < 30.
    Sell when RSI > 70.
    """
    def __init__(self, bars, events, period=14, buy_threshold=30, sell_threshold=70):
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.period = period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.bought = {s: 'OUT' for s in self.symbol_list}

    def _calculate_rsi(self, prices, period=14):
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum()/period
        down = -seed[seed < 0].sum()/period
        rs = up/down if down != 0 else float('inf')
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100./(1. + rs)

        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta
            
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            rs = up/down if down != 0 else float('inf')
            rsi[i] = 100. - 100./(1. + rs)
            
        return rsi[-1]

    def _calculate_rsi_simple(self, prices, period=14):
        # A simpler vectorised approach for the window passed
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_signals(self, event):
        if event.type == EventType.MARKET:
            for s in self.symbol_list:
                # We need enough bars for RSI
                # Simple RSI needs period + 1 at least
                bars = self.bars.get_latest_bars_values(s, "Close", N=self.period+10) # buffer
                
                if bars is not None and len(bars) >= self.period + 1:
                    # Calculate RSI on the window
                    # Note: standard RSI needs more history for smoothing, 
                    # but we will use a simple window average for this MVP.
                    rsi = self._calculate_rsi_simple(bars, self.period)
                    
                    dt = self.bars.get_latest_bar_datetime(s)
                    
                    if rsi < self.buy_threshold and self.bought[s] == 'OUT':
                        print(f"LONG (RSI={rsi:.2f}): {s} at {dt}")
                        self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='LONG', strength=1.0))
                        self.bought[s] = 'LONG'
                    elif rsi > self.sell_threshold and self.bought[s] == 'LONG':
                         print(f"EXIT (RSI={rsi:.2f}): {s} at {dt}")
                         self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='EXIT', strength=1.0))
                         self.bought[s] = 'OUT'
