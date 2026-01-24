"""
Strategy Generated at: 2026-01-24 12:12:32
Prompt: Create a dual moving average crossover strategy (SMA 10 and SMA 50)
"""

from simple_quant.strategy.base import Strategy
from simple_quant.events import SignalEvent
import numpy as np


class DualMovingAverageCrossStrategy(Strategy):
    def __init__(self, bars, events, short_window=10, long_window=50):
        super().__init__(bars, events)
        self.short_window = int(short_window)
        self.long_window = int(long_window)
        self.bought = {s: "OUT" for s in self.symbol_list}

    def _safe_put_signal(self, symbol, dt, signal_type, strength=1.0):
        """
        SignalEvent in this framework appears to be a pydantic BaseModel (or similar)
        that doesn't accept positional args. Use keyword args and fall back to dict.
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

        # Last resort: push a plain dict if the event queue/engine supports it
        self.events.put(
            {"type": "SIGNAL", "symbol": symbol, "datetime": dt, "signal_type": signal_type, "strength": strength}
        )

    def calculate_signals(self, event):
        if event is None:
            return

        for symbol in self.symbol_list:
            closes = self.bars.get_latest_bars_values(symbol, "Close", N=self.long_window)
            if closes is None:
                continue

            closes = np.asarray(closes, dtype=float)
            if closes.shape[0] < self.long_window:
                continue

            short_sma = np.mean(closes[-self.short_window:])
            long_sma = np.mean(closes[-self.long_window:])

            dt = self.bars.get_latest_bar_datetime(symbol)

            if short_sma > long_sma and self.bought[symbol] == "OUT":
                self._safe_put_signal(symbol, dt, "LONG", strength=1.0)
                self.bought[symbol] = "LONG"
            elif short_sma < long_sma and self.bought[symbol] == "LONG":
                self._safe_put_signal(symbol, dt, "EXIT", strength=1.0)
                self.bought[symbol] = "OUT"