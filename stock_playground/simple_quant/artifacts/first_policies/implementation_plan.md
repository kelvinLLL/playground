# Implementation Plan - Stock Playground Upgrade

The goal is to implement two classic trading strategies and backtest them using actual A-share 2024 data.

## User Review Required

> [!IMPORTANT]
> This plan requires installing the `yfinance` library to fetch historical data.

## Proposed Changes

### Scripts

#### [NEW] [fetch_data.py](file:///home/kelvin11888/my_house/playground/stock_playground/scripts/fetch_data.py)
- A script to fetch 2024 daily data for A-share stocks (e.g., Kweichow Moutai `600519.SS`, Ping An `000001.SS`) using `yfinance`.
- Saves data to `data/` directory in a format compatible with `HistoricCSVDataHandler`.

#### [NEW] [run_strategies.py](file:///home/kelvin11888/my_house/playground/stock_playground/run_strategies.py)
- A dedicated runner script to execute backtests for the new strategies.
- Loads the fetched data.
- Initializes and runs both `MovingAverageCrossStrategy` and `RSIStrategy`.
- reports final portfolio value.

### Simple Quant Package

#### [NEW] [std_strategies.py](file:///home/kelvin11888/my_house/playground/stock_playground/simple_quant/strategy/std_strategies.py)
- **MovingAverageCrossStrategy**: Standard Dual SMA crossover (e.g., 10/50 days).
- **RSIStrategy**: A Mean Reversion strategy using RSI (Relative Strength Index). Buy when RSI < 30, Sell when RSI > 70.

## Verification Plan

### Automated Tests
- Run `python3 scripts/fetch_data.py` and verify `data/600519.SS.csv` exists and has data for 2024.
- Run `python3 run_strategies.py` and check the console output for backtest completion and performance metrics.
