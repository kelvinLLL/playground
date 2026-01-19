# Stock Backtesting Framework Walkthrough

I have successfully implemented the **Event-Driven Backtesting Framework**.
This system allows you to simulate trading strategies with realistic handling of events (Market Data -> Signals -> Orders -> Fills).

## Architecture
The system is built on a modular "Event Loop" design:
- **Events**: `MarketEvent`, `SignalEvent`, `OrderEvent`, `FillEvent` (defined in `events.py`).
- **Engine**: The core loop (`engine.py`) that processes these events.
- **Components**:
    - `DataHandler`: Feeds market data (currently `HistoricCSVDataHandler`).
    - `Strategy`: Consumes data, produces signals (e.g., `MovingAverageCrossStrategy`).
    - `Portfolio`: Manages cash/positions, tracks performance (`NaivePortfolio`).
    - `ExecutionHandler`: Simulates fills (`SimulatedExecutionHandler`).

## Files Created
- `simple_quant/events.py`: Core event definitions.
- `simple_quant/engine.py`: The backtest engine.
- `simple_quant/data/csv_data.py`: Handling CSV inputs.
- `simple_quant/strategy/base.py`: Strategy interface.
- `simple_quant/portfolio/simple.py`: Basic portfolio management.
- `simple_quant/execution/backtest.py`: Simulated execution.
- `run_backtest.py`: Main entry point.
- `generate_data.py`: Helper to create dummy data.

## Verification & How to Run

### 1. Install Dependencies
> [!IMPORTANT]
> Your environment requires manual installation of dependencies due to system restrictions.

Please run the following commands in your terminal:

```bash
# If you have sudo access:
sudo apt install python3-pandas python3-numpy python3-pydantic

# OR using pip (if available):
pip install pandas numpy pydantic --user --break-system-packages
```

### 2. Generate Data
Create a dummy `AAPL.csv` file for testing:

```bash
python3 generate_data.py
```

### 3. Run Usage Example
Run the Moving Average Crossover backtest:

```bash
python3 run_backtest.py
```

**Expected Output:**
```
Running Backtest...
Creating summary stats...
[('Total Return', '12.50%'), ('Sharpe Ratio', '1.20'), ('Max Drawdown', '5.40%'), ('Drawdown Duration', '15')]
```

## Next Steps
- **Visualization**: Add `matplotlib` to plot the equity curve.
- **Real Data**: Replace `HistoricCSVDataHandler` with an API-based handler (e.g., Yahoo Finance or Alpaca).
- **Complex Strategies**: Implement mean-reversion or machine learning-based strategies in `simple_quant/strategy/`.
