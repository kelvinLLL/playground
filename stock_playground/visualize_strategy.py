
import os
import sys
import argparse
import importlib.util
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from queue import Queue

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simple_quant.engine import BacktestEngine
from simple_quant.data.csv_data import HistoricCSVDataHandler
from simple_quant.portfolio.simple import RobustPortfolio
from simple_quant.execution.backtest import SimulatedExecutionHandler

def load_strategy_class(file_path):
    """Dynamically loads the Strategy class from a python file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Strategy file not found: {file_path}")
        
    module_name = os.path.basename(file_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    # Find the strategy class (must inherit from Strategy but not be Strategy itself)
    # Checking for 'calculate_signals' method is a good heuristic
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and hasattr(attr, 'calculate_signals') and attr_name != 'Strategy':
            return attr
    return None

def visualize(strategy_path, data_dir, symbol, output_file="strategy_result.png"):
    print(f"--- Visualizing Strategy ---")
    print(f"Strategy: {strategy_path}")
    print(f"Data: {data_dir}")
    print(f"Symbol: {symbol}")
    
    # 1. Load Strategy
    strategy_cls = load_strategy_class(strategy_path)
    if not strategy_cls:
        print("Error: No valid Strategy class found in file.")
        return

    # 2. Setup Engine
    events = Queue()
    # We only load ONE symbol for clear visualization, though the strategy might support list
    symbol_list = [symbol]
    
    data_handler = HistoricCSVDataHandler(events, data_dir, symbol_list)
    strategy = strategy_cls(data_handler, events)
    
    # Use enough capital to avoid 'insufficient cash' noise in visualization
    start_dt = pd.to_datetime("2020-01-01") # Start of typical dataset
    portfolio = RobustPortfolio(data_handler, events, start_dt, initial_capital=1000000.0)
    
    execution_handler = SimulatedExecutionHandler(events, data_handler)
    
    engine = BacktestEngine(data_handler, strategy, portfolio, execution_handler)
    
    print("Running backtest...")
    engine.simulate_trading()
    portfolio.create_equity_curve_dataframe()
    
    # 3. Prepare Data for Plotting
    print("Generating plot...")
    
    # Get Price Data
    # HistoricCSVDataHandler stores data in self.symbol_data but it's an iterator that is consumed.
    # However, 'csv_data.py' loads data into self.symbol_data[s] as a generator?
    # Wait, the original csv_data.py converts it to generator in _open_convert_csv_files.
    # We need to reload the dataframe to plot it, or access the cached 'latest_symbol_data' if it kept full history?
    # No, 'latest_symbol_data' is a list of bars. We can reconstruct it from there if it stores everything.
    # Actually, let's just re-read the CSV for plotting the price background. It's safer.
    
    csv_path = os.path.join(data_dir, f"{symbol}.csv")
    price_df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    
    # Filter price_df to match the backtest period if needed (assuming full usage here)
    
    # Get Trades
    trades = pd.DataFrame(portfolio.trade_history)
    
    # Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    # Top Plot: Price and Markers
    ax1.plot(price_df.index, price_df['Close'], label='Close Price', color='black', linewidth=1, alpha=0.6)
    
    if not trades.empty:
        # Buy Markers
        buys = trades[trades['action'] == 'BUY']
        if not buys.empty:
            ax1.scatter(buys['datetime'], buys['price'], marker='^', color='green', s=100, label='Buy', zorder=5)
            
        # Sell Markers
        sells = trades[trades['action'] == 'SELL'] # 'SELL' from Portfolio (RobustPortfolio sends 'SELL' for exits usually)
        # Note: RobustPortfolio logic: exit_dir = 'SELL' if cur_qty > 0 else 'BUY'. 
        # Check simple.py: self.trade_history records event.direction ('BUY'/'SELL')
        if not sells.empty:
            ax1.scatter(sells['datetime'], sells['price'], marker='v', color='red', s=100, label='Sell', zorder=5)
            
    ax1.set_title(f"Strategy Execution: {symbol}")
    ax1.set_ylabel("Price")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Bottom Plot: Equity Curve
    equity = portfolio.equity_curve
    ax2.plot(equity.index, equity['total'], label='Portfolio Value', color='blue')
    ax2.set_ylabel("Equity")
    ax2.set_xlabel("Date")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Formatting Dates
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Saved visualization to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy_file", help="Path to strategy.py")
    parser.add_argument("--data", default="data", help="Data directory")
    parser.add_argument("--symbol", help="Symbol to plot (defaults to first in csv list)")
    parser.add_argument("--output", default="strategy_result.png", help="Output image file")
    
    args = parser.parse_args()
    
    # Auto-detect symbol if not provided
    target_symbol = args.symbol
    if not target_symbol:
        files = [f for f in os.listdir(args.data) if f.endswith(".csv")]
        if files:
            target_symbol = files[0].replace(".csv", "")
        else:
            print("No data found!")
            sys.exit(1)
            
    visualize(args.strategy_file, args.data, target_symbol, args.output)
