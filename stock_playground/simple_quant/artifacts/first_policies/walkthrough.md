# Backtest Results: A-Share 2024

We implemented and backtested two classic strategies using actual 2024 data for **Kweichow Moutai (600519.SS)** and **Ping An (601318.SS)**.

## Strategies Implemented

1.  **Dual SMA (Simple Moving Average) Crossover**
    *   **Logic**: Long when Short MA (10) > Long MA (30). Exit when Short MA < Long MA.
    *   **Hypothesis**: Captures medium-term trends.
2.  **RSI (Relative Strength Index) Mean Reversion**
    *   **Logic**: Long when RSI < 30 (Oversold). Exit when RSI > 70 (Overbought).
    *   **Hypothesis**: Exploits short-term price reversals.

## Execution Parameters

*   **Initial Capital**: 100,000 CNY
*   **Position Size**: Fixed 100 shares per trade (Naive implementation).
*   **Data Source**: `yfinance` (Daily data, Jan 1, 2024 - Dec 31, 2024).

## Performance Summary

| Metric | Dual SMA (10/30) | RSI (14, 30/70) |
| :--- | :--- | :--- |
| **Total Return** | **-40.72%** | **-2.26%** |
| **Sharpe Ratio** | 0.42 | 0.16 |
| **Max Drawdown** | 80.46% | 32.23% |
| **Final Value** | 57,340.92 | 97,638.78 |

> [!NOTE]
> **Why the high drawdown?**
> The `NaivePortfolio` buys a fixed 100 shares. Kweichow Moutai traded around 1,500-1,700 CNY in 2024. A single trade required ~150,000 - 170,000 CNY, exceeding the 100,000 CNY initial capital. The system allowed negative cash (leverage), amplifying losses when the stock price declined.

## Trade Log Snippets

### Dual SMA
```
LONG: 600519.SS at 2024-02-20
LONG: 601318.SS at 2024-02-20
EXIT: 601318.SS at 2024-03-22
EXIT: 600519.SS at 2024-04-09
...
```

### RSI
```
LONG (RSI=26.41): 601318.SS at 2024-04-11
EXIT (RSI=71.99): 601318.SS at 2024-05-17
LONG (RSI=22.17): 600519.SS at 2024-06-06
...
```

## Conclusion
*   **RSI performed significantly better** than the trend-following SMA strategy in the 2024 A-share market, effectively flat (small loss) vs. a large loss.
*   The system successfully handled:
    *   Data fetching from Yahoo Finance.
    *   Signal generation using `numpy` and `pandas`.
    *   Event-driven backtesting loop.
*   **Next Steps**: Implement position sizing (risk management) to strictly adhere to available capital.
