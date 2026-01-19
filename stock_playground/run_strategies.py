
from simple_quant.engine import BacktestEngine
from simple_quant.data.csv_data import HistoricCSVDataHandler
from simple_quant.portfolio.simple import NaivePortfolio
from simple_quant.execution.backtest import SimulatedExecutionHandler
from simple_quant.strategy.std_strategies import MovingAverageCrossStrategy, RSIStrategy
from queue import Queue
from datetime import datetime
import os

def run_strategy(strategy_cls, strategy_name, symbol_list, initial_capital=100000.0, **kwargs):
    print(f"\n--- Running {strategy_name} Strategy ---")
    csv_dir = os.path.abspath("./data")
    events = Queue()
    # Start date for backtest. Ensure this is within the range of your fetched data.
    start_date = datetime(2024, 1, 1)
    
    data_handler = HistoricCSVDataHandler(events, csv_dir, symbol_list)
    strategy = strategy_cls(data_handler, events, **kwargs)
    portfolio = NaivePortfolio(data_handler, events, start_date, initial_capital=initial_capital)
    execution_handler = SimulatedExecutionHandler(events, data_handler)
    
    engine = BacktestEngine(data_handler, strategy, portfolio, execution_handler)
    engine.simulate_trading()
    
    # Generate statistics
    portfolio.create_equity_curve_dataframe()
    stats = portfolio.output_summary_stats()
    
    print("\nPerformance Statistics:")
    for s in stats:
        print(f"{s[0]}: {s[1]}")
        
    print(f"Final Portfolio Value: {portfolio.current_holdings['total']:.2f}")

def main():
    # Symbols must match what is in data directory
    symbol_list = ["600519.SS", "601318.SS"]
    
    # Run Dual SMA (Short=10, Long=30)
    # Using shorter windows since we only have ~1 year of data
    run_strategy(MovingAverageCrossStrategy, "Dual SMA (10/30)", symbol_list, 
                 short_window=10, long_window=30)
                 
    # Run RSI
    run_strategy(RSIStrategy, "RSI (14, 30/70)", symbol_list, 
                 period=14, buy_threshold=30, sell_threshold=70)

if __name__ == "__main__":
    main()
