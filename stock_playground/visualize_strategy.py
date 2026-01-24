
import os
import sys
import argparse
import importlib.util
import pandas as pd
import numpy as np
import math
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
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load strategy from {file_path}")
        
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    # Find the strategy class (must inherit from Strategy but not be Strategy itself)
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        # Check if it's a class, has 'calculate_signals' (duck typing), and isn't the base ABC
        if isinstance(attr, type) and hasattr(attr, 'calculate_signals') and attr.__name__ != 'Strategy':
            return attr
    return None

def run_single_backtest(strategy_cls, data_dir, symbol):
    """
    Helper to run a backtest for a single symbol and return results.
    """
    events = Queue()
    symbol_list = [symbol]
    
    # Setup components
    try:
        data_handler = HistoricCSVDataHandler(events, data_dir, symbol_list)
        strategy = strategy_cls(data_handler, events)
        
        # Use enough capital to avoid 'insufficient cash' noise
        start_dt = pd.to_datetime("2020-01-01") 
        portfolio = RobustPortfolio(data_handler, events, start_dt, initial_capital=1000000.0)
        execution_handler = SimulatedExecutionHandler(events, data_handler)
        
        engine = BacktestEngine(data_handler, strategy, portfolio, execution_handler)
        engine.simulate_trading()
        portfolio.create_equity_curve_dataframe()
        
        return {
            "symbol": symbol,
            "portfolio": portfolio,
            "equity_curve": portfolio.equity_curve,
            "trades": portfolio.trade_history,
            "success": True
        }
    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        return {"symbol": symbol, "success": False, "error": str(e)}

def visualize_sector(strategy_path, data_dir, output_file="sector_overview.png"):
    """
    Visualizes the strategy performance across ALL symbols in the data_dir.
    """
    print(f"--- Visualizing Sector Overview ---")
    print(f"Strategy: {strategy_path}")
    print(f"Data Dir: {data_dir}")

    # 1. Discover Data
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    if not files:
        print("No data found.")
        return
    
    symbols = [f.replace(".csv", "") for f in files]
    print(f"Found {len(symbols)} symbols: {symbols}")

    # 2. Load Strategy
    strategy_cls = load_strategy_class(strategy_path)
    if not strategy_cls:
        print("Error: No valid Strategy class found.")
        return

    # 3. Run Backtests individually
    results = []
    print("Running backtests...")
    for sym in symbols:
        print(f"  > {sym}...", end="", flush=True)
        res = run_single_backtest(strategy_cls, data_dir, sym)
        if res["success"]:
            results.append(res)
            print(" Done.")
        else:
            print(" Failed.")

    if not results:
        print("No successful backtests to plot.")
        return

    # 4. Create Dashboard Plot
    num_plots = len(results)
    # Layout: Top row is Summary (Equity Curves). 
    # Remaining rows are grid of individual charts.
    
    # Calculate grid dimensions for individual charts
    cols = 3
    rows = math.ceil(num_plots / cols)
    
    # Total figure height: Summary (2 units) + Grid (rows units)
    fig_height = 4 + (rows * 3) 
    fig = plt.figure(figsize=(18, fig_height))
    
    # GridSpec
    gs = fig.add_gridspec(rows + 2, cols) # +2 for the summary plot at top
    
    # --- A. Summary Plot (Top spanning all cols) ---
    ax_summary = fig.add_subplot(gs[0:2, :])
    
    final_returns = []
    
    for res in results:
        curve = res["equity_curve"]
        if curve is None or curve.empty:
            continue
            
        # Normalize to start at 1.0 for comparison
        normalized_curve = curve['total'] / curve['total'].iloc[0]
        final_ret = (normalized_curve.iloc[-1] - 1.0) * 100
        final_returns.append(final_ret)
        
        ax_summary.plot(
            curve.index, 
            normalized_curve, 
            label=f"{res['symbol']} ({final_ret:+.1f}%)", 
            alpha=0.5, 
            linewidth=1.5
        )

    # Plot Average Curve
    # Align all curves to the same index (union)
    all_curves = pd.DataFrame()
    for res in results:
        c = res["equity_curve"]
        if c is not None and not c.empty:
            # Reindex to handle potentially different start dates if data is jagged
            # But here we assume mostly overlapping data. simpler to just forward fill
            norm = c['total'] / c['total'].iloc[0]
            all_curves[res['symbol']] = norm
            
    if not all_curves.empty:
        all_curves = all_curves.ffill().bfill()
        avg_curve = all_curves.mean(axis=1)
        ax_summary.plot(avg_curve.index, avg_curve, label='SECTOR AVERAGE', color='black', linewidth=3, linestyle='--')
        
        avg_ret = (avg_curve.iloc[-1] - 1.0) * 100
        ax_summary.set_title(f"Sector Overview: Cumulative Returns (Avg: {avg_ret:+.2f}%)", fontsize=16, fontweight='bold')
    
    ax_summary.axhline(y=1.0, color='gray', linestyle=':', alpha=0.5)
    ax_summary.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize='small')
    ax_summary.grid(True, alpha=0.3)
    ax_summary.set_ylabel("Normalized Equity (Start=1.0)")

    # --- B. Individual Charts (Grid) ---
    for i, res in enumerate(results):
        r = (i // cols) + 2 # Start from row 2
        c = i % cols
        
        ax = fig.add_subplot(gs[r, c])
        symbol = res["symbol"]
        
        # Load price data for background
        csv_path = os.path.join(data_dir, f"{symbol}.csv")
        price_df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        
        # Plot Price
        ax.plot(price_df.index, price_df['Close'], color='gray', alpha=0.4, label='Price')
        
        # Plot Trades
        trades = pd.DataFrame(res['trades'])
        if not trades.empty:
            buys = trades[trades['action'] == 'BUY']
            sells = trades[trades['action'] == 'SELL']
            
            if not buys.empty:
                ax.scatter(buys['datetime'], buys['price'], marker='^', color='green', s=40, zorder=5)
            if not sells.empty:
                ax.scatter(sells['datetime'], sells['price'], marker='v', color='red', s=40, zorder=5)

        # Plot Equity on secondary axis (optional, but maybe too messy. Let's stick to simple price+markers)
        # Or add a text box with stats
        stats = res['portfolio'].output_summary_stats()
        # stats is list of tuples
        stats_dict = dict(stats)
        ret_str = stats_dict.get('Total Return', 'N/A')
        sharpe_str = stats_dict.get('Sharpe Ratio', 'N/A')
        
        # Color title based on profit
        title_color = 'green' if '-' not in ret_str else 'red'
        ax.set_title(f"{symbol} | Ret: {ret_str} | Sharpe: {sharpe_str}", fontsize=10, color=title_color, fontweight='bold')
        
        ax.grid(True, alpha=0.2)
        # Simplify ticks
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Saved sector overview to: {output_file}")


def visualize_single(strategy_path, data_dir, symbol, output_file="strategy_result.png"):
    """
    Original single-symbol visualization.
    """
    print(f"--- Visualizing Single Symbol ---")
    strategy_cls = load_strategy_class(strategy_path)
    if not strategy_cls:
        print("Error: No valid Strategy class found.")
        return

    res = run_single_backtest(strategy_cls, data_dir, symbol)
    if not res["success"]:
        return

    portfolio = res["portfolio"]
    trades = pd.DataFrame(res['trades'])
    
    # Plotting
    csv_path = os.path.join(data_dir, f"{symbol}.csv")
    price_df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    # Top Plot: Price and Markers
    ax1.plot(price_df.index, price_df['Close'], label='Close Price', color='black', linewidth=1, alpha=0.6)
    
    if not trades.empty:
        buys = trades[trades['action'] == 'BUY']
        sells = trades[trades['action'] == 'SELL']
        if not buys.empty:
            ax1.scatter(buys['datetime'], buys['price'], marker='^', color='green', s=100, label='Buy', zorder=5)
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
    
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Saved visualization to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy_file", help="Path to strategy.py")
    parser.add_argument("--data", default="data", help="Data directory")
    parser.add_argument("--symbol", help="Symbol to plot. If omitted, runs SECTOR OVERVIEW mode.")
    parser.add_argument("--output", default=None, help="Output image file name")
    
    args = parser.parse_args()
    
    if args.symbol:
        # Single Mode
        out = args.output if args.output else "strategy_result.png"
        visualize_single(args.strategy_file, args.data, args.symbol, out)
    else:
        # Sector Mode
        out = args.output if args.output else "sector_overview.png"
        visualize_sector(args.strategy_file, args.data, out)

