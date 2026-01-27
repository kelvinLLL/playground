"""
Backtest Tool.

Allows AI workers to run quantitative backtests.
"""

import os
import sys
from datetime import datetime
from queue import Queue
from typing import Any

# Add project root to path
# playground/ai_worker/tools/backtest.py -> playground
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Also add stock_playground directory to path so internal imports work
STOCK_PLAYGROUND_DIR = os.path.join(PROJECT_ROOT, "stock_playground")
if STOCK_PLAYGROUND_DIR not in sys.path:
    sys.path.append(STOCK_PLAYGROUND_DIR)

from ai_worker.tools.base import BaseTool, ToolResult
from ai_worker.tools.registry import ToolRegistry

# Import stock_playground components
# Note: These imports might fail if dependencies aren't installed in the environment
# Make sure numpy, pandas, etc. are available
try:
    from stock_playground.simple_quant.engine import BacktestEngine
    from stock_playground.simple_quant.data.csv_data import HistoricCSVDataHandler
    from stock_playground.simple_quant.portfolio.simple import RobustPortfolio
    from stock_playground.simple_quant.execution.backtest import SimulatedExecutionHandler
    from stock_playground.simple_quant.strategy.std_strategies import MovingAverageCrossStrategy
    STOCK_PLAYGROUND_AVAILABLE = True
except ImportError:
    STOCK_PLAYGROUND_AVAILABLE = False


@ToolRegistry.register("run_backtest")
class BacktestTool(BaseTool):
    """Tool for running strategy backtests."""

    def __init__(self):
        super().__init__(
            name="run_backtest",
            description="Run a backtest for a specific stock symbol and strategy.",
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol (e.g., 'AAPL', '600519.SS')",
                },
                "strategy": {
                    "type": "string",
                    "enum": ["ma_cross"],
                    "description": "Strategy to run (currently only 'ma_cross')",
                    "default": "ma_cross",
                },
                "short_window": {
                    "type": "integer",
                    "description": "Short moving average window (default: 10)",
                    "default": 10,
                },
                "long_window": {
                    "type": "integer",
                    "description": "Long moving average window (default: 30)",
                    "default": 30,
                },
                "initial_capital": {
                    "type": "number",
                    "description": "Initial capital (default: 100000.0)",
                    "default": 100000.0,
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        if not STOCK_PLAYGROUND_AVAILABLE:
            return ToolResult(
                success=False,
                data=None,
                error="Stock Playground dependencies not found. Please install requirements.",
            )

        symbol = kwargs.get("symbol")
        strategy_name = kwargs.get("strategy", "ma_cross")
        short_window = kwargs.get("short_window", 10)
        long_window = kwargs.get("long_window", 30)
        initial_capital = kwargs.get("initial_capital", 100000.0)

        csv_dir = os.path.join(PROJECT_ROOT, "stock_playground/data")
        csv_path = os.path.join(csv_dir, f"{symbol}.csv")

        if not os.path.exists(csv_path):
            return ToolResult(
                success=False,
                data=None,
                error=f"Data file for {symbol} not found. Please fetch data first.",
            )

        try:
            # Capture stdout to return as result
            import io
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                self._run_engine(
                    csv_dir, 
                    [symbol], 
                    short_window, 
                    long_window, 
                    initial_capital
                )
            
            output = f.getvalue()
            return ToolResult(success=True, data=output)

        except Exception as e:
            return ToolResult(success=False, data=None, error=f"Backtest failed: {str(e)}")

    def _run_engine(self, csv_dir, symbol_list, short_window, long_window, initial_capital):
        """Helper to run the backtest engine."""
        events = Queue()
        start_date = datetime(2020, 1, 1)

        data_handler = HistoricCSVDataHandler(events, csv_dir, symbol_list)
        strategy = MovingAverageCrossStrategy(
            data_handler, events, short_window=short_window, long_window=long_window
        )
        portfolio = RobustPortfolio(
            data_handler, events, start_date, initial_capital=initial_capital
        )
        execution_handler = SimulatedExecutionHandler(events, data_handler)

        engine = BacktestEngine(data_handler, strategy, portfolio, execution_handler)
        engine.simulate_trading()
