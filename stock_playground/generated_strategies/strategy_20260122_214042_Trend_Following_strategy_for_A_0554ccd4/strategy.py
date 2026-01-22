"""
Strategy Generated at: 2026-01-22 21:41:09
Prompt: Trend Following strategy for AI sector. Use Donchian Channel (20-day High/Low) breakout. Buy when Close > 20-day High. Sell when Close < 10-day Low. Use ATR(14) for volatility sizing: position size = 1% risk / (2 * ATR). Max position size 20%.
"""

from simple_quant.strategy.base import Strategy
from simple_quant.events import SignalEvent
import numpy as np


class DonchianATRTrendFollowingAISectorStrategy(Strategy):
    """
    Trend Following strategy:
    - Entry: Close > 20-day High (Donchian breakout)
    - Exit:  Close < 10-day Low
    - Volatility sizing: position size = 1% risk / (2 * ATR(14)), capped at 20%
    Notes:
    - Emits SignalEvent with keyword arguments to avoid BaseModel positional-arg issues.
    - Strength is used to pass sizing (fractional, capped at 0.20).
    """

    def __init__(
        self,
        bars,
        events,
        entry_window=20,
        exit_window=10,
        atr_window=14,
        risk_per_trade=0.01,
        atr_multiple=2.0,
        max_position_frac=0.20,
    ):
        super().__init__(bars, events)
        self.entry_window = int(entry_window)
        self.exit_window = int(exit_window)
        self.atr_window = int(atr_window)
        self.risk_per_trade = float(risk_per_trade)
        self.atr_multiple = float(atr_multiple)
        self.max_position_frac = float(max_position_frac)

        self.bought = {s: "OUT" for s in self.symbol_list}

    def _true_range(self, highs, lows, closes):
        prev_close = closes[:-1]
        high = highs[1:]
        low = lows[1:]
        tr1 = high - low
        tr2 = np.abs(high - prev_close)
        tr3 = np.abs(low - prev_close)
        return np.maximum(tr1, np.maximum(tr2, tr3))

    def _atr(self, highs, lows, closes, window):
        if highs is None or lows is None or closes is None:
            return None
        if len(highs) < window + 1 or len(lows) < window + 1 or len(closes) < window + 1:
            return None
        tr = self._true_range(highs, lows, closes)
        if tr is None or len(tr) < window:
            return None
        return float(np.mean(tr[-window:]))

    def _safe_strength_from_atr(self, atr):
        if atr is None or not np.isfinite(atr) or atr <= 0.0:
            return 1.0
        size = self.risk_per_trade / (self.atr_multiple * atr)
        if not np.isfinite(size) or size <= 0.0:
            return 1.0
        return float(min(size, self.max_position_frac))

    def calculate_signals(self, event):
        if event is None:
            return
        if getattr(event, "type", None) != "MARKET":
            return

        for symbol in self.symbol_list:
            dt = self.bars.get_latest_bar_datetime(symbol)

            # Need enough data for Donchian and ATR
            need = max(self.entry_window, self.exit_window, self.atr_window + 1)

            closes = self.bars.get_latest_bars_values(symbol, "Close", N=need)
            highs = self.bars.get_latest_bars_values(symbol, "High", N=need)
            lows = self.bars.get_latest_bars_values(symbol, "Low", N=need)

            if closes is None or highs is None or lows is None:
                continue
            if len(closes) < need or len(highs) < need or len(lows) < need:
                continue

            close = float(closes[-1])

            # Donchian levels computed excluding current bar to avoid lookahead
            entry_high = float(np.max(highs[-(self.entry_window + 1) : -1]))
            exit_low = float(np.min(lows[-(self.exit_window + 1) : -1]))

            atr = self._atr(highs, lows, closes, self.atr_window)
            strength = self._safe_strength_from_atr(atr)

            if self.bought[symbol] == "OUT":
                if close > entry_high:
                    # Use keyword args to satisfy BaseModel/Pydantic-style constructors
                    self.events.put(
                        SignalEvent(symbol=symbol, datetime=dt, signal_type="LONG", strength=strength)
                    )
                    self.bought[symbol] = "LONG"

            elif self.bought[symbol] == "LONG":
                if close < exit_low:
                    self.events.put(
                        SignalEvent(symbol=symbol, datetime=dt, signal_type="EXIT", strength=1.0)
                    )
                    self.bought[symbol] = "OUT"