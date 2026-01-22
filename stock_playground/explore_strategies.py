
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from queue import Queue

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from stock_playground.simple_quant.engine import BacktestEngine
from stock_playground.simple_quant.data.csv_data import HistoricCSVDataHandler
from stock_playground.simple_quant.portfolio.simple import RobustPortfolio
from stock_playground.simple_quant.execution.backtest import SimulatedExecutionHandler
from stock_playground.simple_quant.strategy.std_strategies import MovingAverageCrossStrategy

import argparse

def evaluate_strategy(strategy_cls, params, symbol_list, start_date, end_date, initial_capital=100000.0, data_dir=None):
    """
    Runs a backtest and returns performance metrics.
    """
    if data_dir is None:
        csv_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
    else:
        csv_dir = data_dir
        
    events = Queue()
    
    # Setup components
    data_handler = HistoricCSVDataHandler(events, csv_dir, symbol_list, start_date=start_date, end_date=end_date)
    strategy = strategy_cls(data_handler, events, **params)
    
    # Portfolio requires a datetime object for start_date
    start_dt = pd.to_datetime(start_date)
    portfolio = RobustPortfolio(data_handler, events, start_dt, initial_capital=initial_capital)
    
    execution_handler = SimulatedExecutionHandler(events, data_handler)
    
    engine = BacktestEngine(data_handler, strategy, portfolio, execution_handler)
    engine.simulate_trading()
    
    # Extract stats
    portfolio.create_equity_curve_dataframe()
    stats_list = portfolio.output_summary_stats()
    
    # Convert stats list to dict for easier access
    # stats_list is like [("Total Return", "12.0%"), ...]
    stats = {}
    for k, v in stats_list:
        try:
            # Clean string values to floats where possible
            if '%' in v:
                val = float(v.replace('%', '')) / 100.0
            else:
                val = float(v)
        except:
            val = v
        stats[k] = val
        
    return stats

def main():
    print("=== Strategy Exploration Agent ===")
    
    parser = argparse.ArgumentParser(description='Explore strategy parameters.')
    parser.add_argument('--data_dir', type=str, default=None, help='Path to data directory (e.g. data/ai)')
    args = parser.parse_args()
    
    # 1. Configuration
    # Auto-discover symbols in the specified or default directory
    if args.data_dir:
        base_data_dir = args.data_dir
    else:
        base_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
        
    if not os.path.exists(base_data_dir):
        print(f"Error: Data directory {base_data_dir} does not exist.")
        return

    files = [f for f in os.listdir(base_data_dir) if f.endswith('.csv')]
    symbol_list = [f.replace('.csv', '') for f in files]
    
    if not symbol_list:
        print(f"No CSV data found in {base_data_dir}")
        return
        
    print(f"Target Data Directory: {base_data_dir}")
    print(f"Symbols ({len(symbol_list)}): {symbol_list}")
    
    # Train/Test Split
    train_start = "2020-01-01"
    train_end = "2023-12-31"
    
    test_start = "2024-01-01"
    test_end = "2024-12-31" # or current date
    
    print(f"Training Period: {train_start} to {train_end}")
    print(f"Testing Period:  {test_start} to {test_end}")
    
    # 2. Define Grid Search Space
    # Moving Average Cross: Short (5-20), Long (20-60)
    # Constraints: Short < Long
    param_grid = []
    for short in [5, 10, 15, 20]:
        for long in [20, 30, 40, 50, 60]:
            if short < long:
                param_grid.append({'short_window': short, 'long_window': long})
                
    print(f"Testing {len(param_grid)} parameter combinations...")
    
    # 3. Training Loop
    results = []
    
    for params in param_grid:
        print(f"  > Testing {params}...", end="", flush=True)
        try:
            stats = evaluate_strategy(
                MovingAverageCrossStrategy, 
                params, 
                symbol_list, 
                train_start, 
                train_end,
                data_dir=base_data_dir
            )
            
            score = stats.get('Stability Score', 0.0)
            print(f" Stability: {score:.2f}")
            
            results.append({
                'params': params,
                'stats': stats,
                'score': score
            })
        except Exception as e:
            print(f" Failed: {e}")

    # 4. Rank and Select
    # Sort by Stability Score descending
    results.sort(key=lambda x: x['score'], reverse=True)
    
    top_n = 3
    print(f"\n=== Top {top_n} Strategies (Training) ===")
    for i, res in enumerate(results[:top_n]):
        print(f"{i+1}. Params: {res['params']}, Stability: {res['score']:.2f}, Sharpe: {res['stats'].get('Sharpe Ratio',0):.2f}")

    # 5. Out-of-Sample Testing
    print(f"\n=== Out-of-Sample Validation ({test_start} - {test_end}) ===")
    
    print(f"{'Rank':<5} {'Params':<25} {'Train Stab':<12} {'Test Stab':<12} {'Test Return':<12} {'Status'}")
    print("-" * 80)
    
    for i, res in enumerate(results[:top_n]):
        params = res['params']
        train_score = res['score']
        
        try:
            test_stats = evaluate_strategy(
                MovingAverageCrossStrategy,
                params,
                symbol_list,
                test_start,
                test_end,
                data_dir=base_data_dir
            )
            test_score = test_stats.get('Stability Score', 0.0)
            test_ret = test_stats.get('Total Return', 0.0)
            
            # Simple robustness check: Test score shouldn't drop by more than 50% (arbitrary)
            is_robust = "PASS" if test_score > 0 and test_score > (train_score * 0.5) else "FAIL"
            if train_score <= 0: is_robust = "FAIL"
            
            print(f"{i+1:<5} {str(params):<25} {train_score:.2f}         {test_score:.2f}         {test_ret*100:.1f}%        {is_robust}")
            
        except Exception as e:
            print(f"{i+1:<5} {str(params):<25} ERROR: {e}")

if __name__ == "__main__":
    main()
