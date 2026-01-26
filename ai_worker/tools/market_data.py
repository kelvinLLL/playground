"""
Market Data Tool.

Allows AI workers to fetch historical market data using yfinance.
"""

import os
import sys
from typing import Any

# Add project root to path to import from stock_playground
# playground/ai_worker/tools/market_data.py -> playground
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from stock_playground.scripts.fetch_data import fetch_data
from ai_worker.tools.base import BaseTool, ToolResult


class MarketDataTool(BaseTool):
    """Tool for fetching historical market data."""

    def __init__(self):
        super().__init__(
            name="fetch_market_data",
            description="Fetch historical daily market data for a stock symbol using yfinance.",
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
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format",
                },
            },
            "required": ["symbol", "start_date", "end_date"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        symbol = kwargs.get("symbol")
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")

        if not all([symbol, start_date, end_date]):
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameters: symbol, start_date, end_date",
            )

        try:
            # Define output directory (stock_playground/data)
            output_dir = os.path.join(PROJECT_ROOT, "stock_playground/data")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Call the existing fetch_data function
            # Note: fetch_data is synchronous, might block event loop if large download
            # For production, run in executor. For now, it's fine.
            fetch_data(symbol, start_date, end_date, output_dir)

            file_path = os.path.join(output_dir, f"{symbol}.csv")
            if os.path.exists(file_path):
                return ToolResult(
                    success=True,
                    data=f"Successfully fetched data for {symbol} to {file_path}",
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Failed to fetch data for {symbol} (file not created)",
                )

        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
