"""
Strategy Generated at: 2026-01-22 01:06:27
Prompt: Create a Mean Reversion strategy using Bollinger Bands (window=20, std=2). Buy when the Close price crosses below the Lower Band. Sell when the Close price crosses above the Upper Band. IMPORTANT: Add a stop loss of 5% from the entry price.
"""

from simple_quant.strategy.base import Strategy
from simple_quant.events import SignalEvent
import numpy as np


class BollingerMeanReversionStopLossStrategy(Strategy):
    """
    Mean Reversion using Bollinger Bands:
    - window=20, std=2
    - Buy when Close crosses below Lower Band
    - Sell/Exit when Close crosses above Upper Band
    - Stop loss: 5% from entry price
    """

    def __init__(self, bars, events, window=20, num_std=2.0, stop_loss_pct=0.05):
        super().__init__(bars, events)
        self.window = int(window)
        self.num_std = float(num_std)
        self.stop_loss_pct = float(stop_loss_pct)

        self.bought = {s: "OUT" for s in self.symbol_list}
        self.entry_price = {s: None for s in self.symbol_list}

    def _safe_put_signal(self, symbol, dt, signal_type, strength=1.0):
        """
        SignalEvent in this framework appears to be a Pydantic BaseModel (or similar)
        that does not accept positional args. Use keyword args and fall back to dict.
        """
        try:
            self.events.put(
                SignalEvent(symbol=symbol, datetime=dt, signal_type=signal_type, strength=strength)
            )
            return
        except TypeError:
            pass

        try:
            self.events.put(
                SignalEvent(symbol=symbol, dt=dt, signal_type=signal_type, strength=strength)
            )
            return
        except TypeError:
            pass

        try:
            self.events.put(
                SignalEvent(symbol=symbol, dt=dt, signal=signal_type, strength=strength)
            )
            return
        except TypeError:
            pass

        # Last resort: put a plain dict (some event queues accept this)
        self.events.put(
            {"type": "SIGNAL", "symbol": symbol, "datetime": dt, "signal_type": signal_type, "strength": strength}
        )

    def calculate_signals(self, event):
        if event is None:
            return

        # Only respond to MarketEvent-like objects
        if not hasattr(event, "type") or event.type != "MARKET":
            return

        for symbol in self.symbol_list:
            closes = self.bars.get_latest_bars_values(symbol, "Close", N=self.window + 1)
            if closes is None:
                continue
            closes = np.asarray(closes, dtype=float)
            if closes.shape[0] < self.window + 1:
                continue

            dt = self.bars.get_latest_bar_datetime(symbol)

            prev_close = closes[-2]
            curr_close = closes[-1]

            window_prev = closes[-(self.window + 1) : -1]  # previous window
            window_curr = closes[-self.window :]  # current window

            mean_prev = np.mean(window_prev)
            std_prev = np.std(window_prev, ddof=0)
            lower_prev = mean_prev - self.num_std * std_prev
            upper_prev = mean_prev + self.num_std * std_prev

            mean_curr = np.mean(window_curr)
            std_curr = np.std(window_curr, ddof=0)
            lower_curr = mean_curr - self.num_std * std_curr
            upper_curr = mean_curr + self.num_std * std_curr

            # Stop loss check (if in position)
            if self.bought[symbol] == "LONG" and self.entry_price[symbol] is not None:
                if curr_close <= self.entry_price[symbol] * (1.0 - self.stop_loss_pct):
                    self._safe_put_signal(symbol, dt, "EXIT", strength=1.0)
                    self.bought[symbol] = "OUT"
                    self.entry_price[symbol] = None
                    continue

            # Entry: cross below lower band
            if self.bought[symbol] == "OUT":
                crossed_below = (prev_close >= lower_prev) and (curr_close < lower_curr)
                if crossed_below:
                    self._safe_put_signal(symbol, dt, "LONG", strength=1.0)
                    self.bought[symbol] = "LONG"
                    self.entry_price[symbol] = float(curr_close)

            # Exit: cross above upper band
            elif self.bought[symbol] == "LONG":
                crossed_above = (prev_close <= upper_prev) and (curr_close > upper_curr)
                if crossed_above:
                    self._safe_put_signal(symbol, dt, "EXIT", strength=1.0)
                    self.bought[symbol] = "OUT"
                    self.entry_price[symbol] = None