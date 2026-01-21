
import importlib.util
import os
import sys
import traceback
from queue import Queue
from datetime import datetime
import pandas as pd

# Add project root and stock_playground to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from stock_playground.simple_quant.engine import BacktestEngine
from stock_playground.simple_quant.data.csv_data import HistoricCSVDataHandler
from stock_playground.simple_quant.portfolio.simple import RobustPortfolio
from stock_playground.simple_quant.execution.backtest import SimulatedExecutionHandler

class StrategyExecutor:
    """
    Sandboxed executor for generated strategies.
    Loads a python file dynamically, runs a backtest, and returns the result or error.
    """
    def __init__(self, data_dir: str, symbol_list: list):
        self.data_dir = data_dir
        self.symbol_list = symbol_list

    def run_strategy(self, strategy_file_path: str, start_date_str="2020-01-01", end_date_str="2023-12-31"):
        """
        Dynamically loads the strategy from file and runs it.
        Returns:
            dict: { "success": bool, "error": str, "metrics": dict }
        """
        try:
            # 1. Dynamic Import
            module_name = os.path.basename(strategy_file_path).replace(".py", "")
            spec = importlib.util.spec_from_file_location(module_name, strategy_file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load file: {strategy_file_path}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 2. Find Strategy Class
            # We look for a class that inherits from Strategy (but not Strategy itself)
            # Since we can't easily check 'issubclass' across dynamic reloads without importing base again,
            # we'll check class name or just assume the first class that accepts (bars, events) is it.
            # Better heuristic: Find class with 'calculate_signals' method.
            
            strategy_cls = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and hasattr(attr, 'calculate_signals') and attr_name != 'Strategy':
                    strategy_cls = attr
                    break
            
            if strategy_cls is None:
                return {"success": False, "error": "No valid Strategy class found in file."}

            # 3. Setup Backtest Environment
            events = Queue()
            
            # Using partial data for training/verification
            data_handler = HistoricCSVDataHandler(
                events, 
                self.data_dir, 
                self.symbol_list, 
                start_date=start_date_str, 
                end_date=end_date_str
            )
            
            # Instantiate Strategy
            # Use try-catch for init errors (e.g. missing args)
            try:
                strategy = strategy_cls(data_handler, events)
            except Exception as e:
                # Some strategies might define extra __init__ args without defaults
                # The prompt instructs standard signature, but AI might hallucinate.
                return {"success": False, "error": f"Strategy __init__ failed: {str(e)}"}

            # Instantiate Portfolio
            start_dt = pd.to_datetime(start_date_str)
            portfolio = RobustPortfolio(data_handler, events, start_dt, initial_capital=100000.0)
            
            execution = SimulatedExecutionHandler(events, data_handler)
            engine = BacktestEngine(data_handler, strategy, portfolio, execution, heartbeat=0.0)

            # 4. Run Simulation
            engine.simulate_trading()

            # 5. Harvest Metrics
            portfolio.create_equity_curve_dataframe()
            stats_list = portfolio.output_summary_stats()
            
            stats_dict = {}
            for k, v in stats_list:
                try:
                    val = float(v.replace('%', '')) / 100.0 if '%' in v else float(v)
                except:
                    val = v
                stats_dict[k] = val

            return {
                "success": True,
                "metrics": stats_dict,
                "error": None
            }

        except Exception as e:
            # Capture full traceback for the AI to fix
            return {
                "success": False,
                "error": f"{str(e)}\n{traceback.format_exc()}"
            }
