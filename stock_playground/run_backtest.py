from simple_quant.engine import BacktestEngine
from simple_quant.data.csv_data import HistoricCSVDataHandler
from simple_quant.strategy.examples import MovingAverageCrossStrategy
from simple_quant.portfolio.simple import RobustPortfolio
from simple_quant.execution.backtest import SimulatedExecutionHandler
from queue import Queue
from datetime import datetime
import os

def run_backtest():
    csv_dir = os.path.abspath("./data")
    symbol_list = ["AAPL"]
    initial_capital = 100000.0
    start_date = datetime(2020, 1, 1)
    heartbeat = 0.0

    events = Queue()
    
    # 1. Data Handler
    data_handler = HistoricCSVDataHandler(events, csv_dir, symbol_list)
    
    # 2. Strategy
    # Using shorter windows for the dummy data (which is ~500 days)
    # MAC 10/50
    strategy = MovingAverageCrossStrategy(data_handler, events, short_window=10, long_window=50)
    
    # 3. Portfolio
    portfolio = RobustPortfolio(data_handler, events, start_date, initial_capital=initial_capital)
    
    # 4. Execution Handler
    execution_handler = SimulatedExecutionHandler(events, data_handler)
    
    # 5. Engine
    engine = BacktestEngine(data_handler, strategy, portfolio, execution_handler, heartbeat)
    
    engine.simulate_trading()

if __name__ == "__main__":
    run_backtest()
