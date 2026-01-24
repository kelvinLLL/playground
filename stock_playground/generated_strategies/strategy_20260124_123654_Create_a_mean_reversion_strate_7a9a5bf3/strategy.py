"""
Strategy Generated at: 2026-01-24 12:37:09
Prompt: Create a mean reversion strategy using RSI (buy < 30, sell > 70)
"""

from simple_quant.strategy.base import Strategy
from simple_quant.events import SignalEvent
import numpy as np


class RSIMeanReversionStrategy(Strategy):
    """
    Mean reversion strategy using RSI:
      - Buy (LONG) when RSI < 30
      - Exit when RSI > 70
    """

    def __init__(self, bars, events, rsi_period=14, oversold=30.0, overbought=70.0):
        super().__init__(bars, events)
        self.rsi_period = int(rsi_period)
        self.oversold = float(oversold)
        self.overbought = float(overbought)
        self.bought = {s: "OUT" for s in self.symbol_list}

    @staticmethod
    def _rsi_from_closes(closes: np.ndarray, period: int) -> float:
        """
        Wilder-style RSI computed from the last (period+1) closes.
        Returns np.nan if cannot be computed robustly.
        """
        if closes is None:
            return np.nan
        closes = np.asarray(closes, dtype=float)
        if closes.size < period + 1:
            return np.nan

        deltas = np.diff(closes[-(period + 1):])
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0.0 and avg_gain == 0.0:
            return 50.0
        if avg_loss == 0.0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _emit_signal(self, symbol, dt, signal_type, strength=1.0):
        """
        SignalEvent in this framework appears to be a Pydantic BaseModel (or similar)
        that does not accept positional args. Use keyword args.
        """
        self.events.put(
            SignalEvent(symbol=symbol, datetime=dt, signal_type=signal_type, strength=float(strength))
        )

    def calculate_signals(self, event):
        if event is None:
            return
        if getattr(event, "type", None) != "MARKET":
            return

        for symbol in self.symbol_list:
            closes = self.bars.get_latest_bars_values(symbol, "Close", N=self.rsi_period + 1)
            if closes is None or len(closes) < self.rsi_period + 1:
                continue

            rsi = self._rsi_from_closes(closes, self.rsi_period)
            if not np.isfinite(rsi):
                continue

            dt = self.bars.get_latest_bar_datetime(symbol)

            if rsi < self.oversold and self.bought[symbol] == "OUT":
                self._emit_signal(symbol, dt, "LONG", strength=1.0)
                self.bought[symbol] = "LONG"

            elif rsi > self.overbought and self.bought[symbol] == "LONG":
                self._emit_signal(symbol, dt, "EXIT", strength=1.0)
                self.bought[symbol] = "OUT"