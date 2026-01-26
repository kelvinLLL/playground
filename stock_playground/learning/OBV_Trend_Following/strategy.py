
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
        # Store current target weight (float) instead of string status
        self.bought = dict((s, 0.0) for s in self.symbol_list)
        
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
                
                # 4. Signal Logic: Dynamic Weighting (Modern Method)
                
                # Calculate Price SMA
                price_window = 60
                price_sma_60 = 0.0
                current_price = 0.0
                trend_confirmed = False
                
                if len(closes) >= price_window:
                    price_sma_60 = np.mean(closes[-price_window:])
                    current_price = closes[-1]
                    trend_confirmed = current_price > price_sma_60

                # --- Decision Logic ---
                target_weight = 0.0
                action_label = "WAIT"
                
                # Check OBV Trend (Short-term Money Flow)
                obv_bullish = current_obv > current_obv_ma
                
                if obv_bullish:
                    if trend_confirmed:
                        # [Aggressive] Money Flow + Price Trend = Heavy Position
                        target_weight = 0.20 
                        action_label = "STRONG LONG (Target 20%)"
                    else:
                        # [Conservative] Money Flow only = Base Position
                        target_weight = 0.10
                        action_label = "WEAK LONG (Target 10%)"
                else:
                    # Money Flow Breakdown = Clear
                    target_weight = 0.0
                    action_label = "EXIT (Target 0%)"

                # --- Send Signal Only If Changed ---
                # To prevent spamming signals every day, we track current logic state
                # But our Portfolio's 'rebalance' logic handles "no change needed" efficiently.
                # However, sending signal every bar ensures we track weight changes (e.g. 10% -> 20%)
                
                # Current simple check: compare with last *trade* direction won't work well for scaling
                # So we just send signal if the *target tier* changes.
                # For simplicity in this demo, let's just emit if target > 0 or if we hold it and need to sell.
                
                # Simplify: Emit signal if logic implies holding (rebalance will handle sizing) 
                # or if logic implies exit and we firmly hold it.
                
                # Actually, simplest "modern" way: Always emit target weight. 
                # The Portfolio calculates difference. If difference is small, it won't trade much.
                # But to keep logs clean, we filter slightly.
                
                prev_weight = self.bought.get(s, 0.0)
                
                # If target changed significantly (e.g. 0->0.1, 0.1->0.2, 0.2->0), send signal
                if abs(target_weight - prev_weight) > 0.01:
                     print(f"{action_label}: {s} at {dt} | OBV_Diff: {current_obv - current_obv_ma:.0f} | Price vs SMA60: {current_price:.2f}/{price_sma_60:.2f}")
                     self.events.put(SignalEvent(symbol=s, datetime=dt, signal_type='ADJUST', strength=target_weight))
                     self.bought[s] = target_weight

