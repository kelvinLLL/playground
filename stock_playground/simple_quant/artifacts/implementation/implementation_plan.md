# Stock Backtesting Framework Implementation Plan

## Goal Description
Build a lightweight, extensible, and modern (Python 3.12) backtesting framework for stock trading (Daily frequency initially).
The system should support future extensions for multiple markets (A-share, HK, US) and easy strategy exploration.

## User Review Required
> [!IMPORTANT]
> I am proposing an **Event-Driven Architecture**. This is slightly more code than a simple Vectorized (pandas-based) backtest, but it provides significantly better extensibility for:
> 1. Multi-asset/Multi-market support.
> 2. Realistic handling of order execution and latency.
> 3. Transitioning to Live Trading seamlessly in the future (reusing the same strategy logic).

## Architecture Overview

We will use a modular design:
1.  **Events**: The glue. `MarketEvent`, `SignalEvent`, `OrderEvent`, `FillEvent`.
2.  **DataHandler**: Interface for fetching data. Returns `MarketEvent`.
3.  **Strategy**: Receives `MarketEvent`, generates `SignalEvent`.
4.  **Portfolio**: Receives `SignalEvent` & `FillEvent`. Manages cash/positions and risk. Generates `OrderEvent`.
5.  **ExecutionHandler**: Receives `OrderEvent`, simulates execution (or routes to API), generates `FillEvent`.
6.  **Engine**: The main loop processing the Event Queue.

## Proposed Changes

### Directory Structure
```
simple_quant/
  ├── __init__.py
  ├── events.py          # Event classes (Data classes)
  ├── engine.py          # Main Event Loop
  ├── data/
  │   ├── base.py        # DataHandler ABC
  │   └── csv_data.py    # Simple CSV loader for testing
  ├── strategy/
  │   ├── base.py        # Strategy ABC
  │   └── examples.py    # Example Strategies
  ├── portfolio/
  │   ├── base.py        # Portfolio ABC
  │   └── simple.py      # Basic Portfolio manager
  └── execution/
      ├── base.py
      └── backtest.py    # Simulated execution
```

### Dependencies
- `pandas`: For data storage/time-series manipulation.
- `pydantic`: For robust data modelling of Events.
- `numpy`: Calculation.

## Verification Plan

### Automated Tests
- Create a dummy dataset (e.g., sine wave price).
- Run a "Buy and Hold" strategy.
- Verify that final Portfolio Value matches expected manual calculation.

### Manual Verification
- Run the system with a sample CSV file (e.g., AAPL daily data).
- Output a transaction log and final equity curve.
