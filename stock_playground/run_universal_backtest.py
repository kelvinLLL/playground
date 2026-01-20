
import sys
import os
import pandas as pd
from queue import Queue
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from stock_playground.simple_quant.engine import BacktestEngine
from stock_playground.simple_quant.data.csv_data import HistoricCSVDataHandler
from stock_playground.simple_quant.portfolio.simple import RobustPortfolio
from stock_playground.simple_quant.execution.backtest import SimulatedExecutionHandler
from stock_playground.simple_quant.strategy.std_strategies import MovingAverageCrossStrategy, RSIStrategy

def main():
    print("=== Universal Backtest Runner ===")
    
    # 1. Discovery
    csv_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
    if not os.path.exists(csv_dir):
        print(f"Error: Data directory not found at {csv_dir}")
        return

    # Auto-discover symbols
    files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
    symbol_list = [f.replace('.csv', '') for f in files]
    
    if not symbol_list:
        print("No CSV data files found. Please run 'python stock_playground/scripts/fetch_data.py' first.")
        return
        
    print(f"Discovered {len(symbol_list)} symbols: {symbol_list}")
    
    # 2. Configuration
    initial_capital = 100000.0
    start_date = datetime(2020, 1, 1) # Default start
    
    # Ask for strategy (simple command line arg or hardcoded default for now)
    # Defaulting to Dual SMA 10/30 as a benchmark
    print("\nRunning Benchmark Strategy: Dual SMA (Short=10, Long=30)")
    
    events = Queue()
    
    # 3. Setup
    # Load ALL symbols
    data_handler = HistoricCSVDataHandler(events, csv_dir, symbol_list)
    
    strategy = MovingAverageCrossStrategy(data_handler, events, short_window=10, long_window=30)
    portfolio = RobustPortfolio(data_handler, events, start_date, initial_capital=initial_capital)
    execution_handler = SimulatedExecutionHandler(events, data_handler)
    
    engine = BacktestEngine(data_handler, strategy, portfolio, execution_handler)
    
    # 4. Execution
    print("Starting Backtest Simulation...")
    engine.simulate_trading()
    
    # 5. Reporting
    print("\n" + "="*40)
    print("       FINAL PERFORMANCE REPORT       ")
    print("="*40)
    
    portfolio.create_equity_curve_dataframe()
    stats = portfolio.output_summary_stats()
    
    for label, value in stats:
        print(f"{label:<20}: {value}")
        
    print("-" * 40)
    print(f"Final Portfolio Value : {portfolio.current_holdings['total']:.2f}")
    print("="*40)

if __name__ == "__main__":
    main()
