from simple_quant.strategy.base import Strategy
from simple_quant.events import SignalEvent, MarketEvent, EventType
from simple_quant.data.base import DataHandler
from queue import Queue
from datetime import datetime
import numpy as np

class MovingAverageCrossStrategy(Strategy):
    """
    Carries out a basic Moving Average Crossover strategy with a
    short/long simple weighted moving average. Default short/long
    windows are 100/400 periods respectively, suitable for a 
    long-term trend follower.
    """
    
    def __init__(self, bars: DataHandler, events: Queue, short_window=100, long_window=400):
        """
        Initializes the Running Strategy.
        
        Parameters:
        bars - The DataHandler object that provides bar information
        events - The Event Queue object.
        short_window - The short moving average lookback.
        long_window - The long moving average lookback.
        """
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.short_window = short_window
        self.long_window = long_window
        
        # Set to True if a symbol is in the market
        self.bought = self._calculate_initial_bought()

    def _calculate_initial_bought(self):
        """
        Adds keys to the bought dictionary for all symbols
        and sets them to 'OUT'.
        """
        bought = {}
        for s in self.symbol_list:
            bought[s] = 'OUT'
        return bought

    def calculate_signals(self, event: MarketEvent):
        """
        Generates a new SignalEvent based on the MAC
        SMA with the short window crossing the long window.
        
        Parameters:
        event - A MarketEvent object. 
        """
        if event.type == EventType.MARKET:
            for s in self.symbol_list:
                bars = self.bars.get_latest_bars_values(s, "Close", N=self.long_window)
                
                if bars is not None and bars.size > 0:
                    if len(bars) >= self.long_window:
                        short_sma = np.mean(bars[-self.short_window:])
                        long_sma = np.mean(bars[-self.long_window:])

                        symbol = s
                        dt = self.bars.get_latest_bar_datetime(s)
                        sig_dir = ""

                        if short_sma > long_sma and self.bought[s] == "OUT":
                            sig_dir = 'LONG'
                            signal = SignalEvent(symbol, dt, sig_dir, 1.0)
                            self.events.put(signal)
                            self.bought[s] = 'LONG'

                        elif short_sma < long_sma and self.bought[s] == "LONG":
                            sig_dir = 'EXIT'
                            signal = SignalEvent(symbol, dt, sig_dir, 1.0)
                            self.events.put(signal)
                            self.bought[s] = 'OUT'
