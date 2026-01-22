"""
Strategy Generated at: 2026-01-22 01:05:24
Prompt: Create a Mean Reversion strategy using Bollinger Bands (window=20, std=2). Buy when the Close price crosses below the Lower Band. Sell when the Close price crosses above the Upper Band. IMPORTANT: Add a stop loss of 5% from the entry price.
"""

from simple_quant.strategy.base import Strategy
from simple_quant.events import SignalEvent
import numpy as np


class BollingerMeanReversionStrategy(Strategy):
    def __init__(self, bars, events, window=20, num_std=2.0, stop_loss_pct=0.05):
        super().__init__(bars, events)
        self.window = int(window)
        self.num_std = float(num_std)
        self.stop_loss_pct = float(stop_loss_pct)

        self.bought = {s: 'OUT' for s in self.symbol_list}
        self.entry_price = {s: None for s in self.symbol_list}

    def calculate_signals(self, event):
        if event is None or getattr(event, "type", None) != "MARKET":
            return

        for symbol in self.symbol_list:
            closes = self.bars.get_latest_bars_values(symbol, "Close", N=self.window + 1)
            if closes is None:
                continue
            closes = np.asarray(closes, dtype=float)
            if closes.shape[0] < self.window + 1:
                continue
            if np.any(~np.isfinite(closes)):
                continue

            dt = self.bars.get_latest_bar_datetime(symbol)

            prev_close = closes[-2]
            curr_close = closes[-1]

            window_closes_prev = closes[-(self.window + 1):-1]
            window_closes_curr = closes[-self.window:]

            ma_prev = np.mean(window_closes_prev)
            std_prev = np.std(window_closes_prev, ddof=0)
            lower_prev = ma_prev - self.num_std * std_prev
            upper_prev = ma_prev + self.num_std * std_prev

            ma_curr = np.mean(window_closes_curr)
            std_curr = np.std(window_closes_curr, ddof=0)
            lower_curr = ma_curr - self.num_std * std_curr
            upper_curr = ma_curr + self.num_std * std_curr

            # Stop loss check (only when in position and entry price known)
            if self.bought[symbol] == 'LONG' and self.entry_price[symbol] is not None:
                if curr_close <= self.entry_price[symbol] * (1.0 - self.stop_loss_pct):
                    self.events.put(SignalEvent(symbol, dt, 'EXIT', strength=1.0))
                    self.bought[symbol] = 'OUT'
                    self.entry_price[symbol] = None
                    continue

            # Entry: cross below lower band
            if self.bought[symbol] == 'OUT':
                if prev_close >= lower_prev and curr_close < lower_curr:
                    self.events.put(SignalEvent(symbol, dt, 'LONG', strength=1.0))
                    self.bought[symbol] = 'LONG'
                    self.entry_price[symbol] = float(curr_close)

            # Exit: cross above upper band
            elif self.bought[symbol] == 'LONG':
                if prev_close <= upper_prev and curr_close > upper_curr:
                    self.events.put(SignalEvent(symbol, dt, 'EXIT', strength=1.0))
                    self.bought[symbol] = 'OUT'
                    self.entry_price[symbol] = None