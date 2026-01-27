"""
MCP Server Entrypoint.

Exposes AI Worker tools as a standard Model Context Protocol (MCP) server.
This allows other MCP clients (like Claude Desktop) to use our tools.
"""

import asyncio
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

from ai_worker.config import get_settings
from ai_worker.tools.registry import ToolRegistry
# Trigger registration
import ai_worker.tools  # noqa: F401

# Initialize settings
settings = get_settings()

# Initialize FastMCP Server
mcp = FastMCP("AI Worker Tools")

# Initialize Tools via Registry
# We pre-instantiate them here to reuse connections/sessions
web_tool = ToolRegistry.create_tool(
    "web_search", 
    config={"tavily_api_key": settings.search.tavily_api_key}
)
pdf_tool = ToolRegistry.create_tool("read_pdf")
market_tool = ToolRegistry.create_tool("fetch_market_data")
backtest_tool = ToolRegistry.create_tool("run_backtest")


@mcp.tool()
async def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for real-time information.
    
    Args:
        query: Search query string.
        max_results: Maximum number of results to return (default: 5).
    """
    result = await web_tool.execute(query=query, max_results=max_results)
    if result.success:
        return str(result.data)
    return f"Error: {result.error}"


@mcp.tool()
async def read_pdf(file_path: str, max_pages: int = 20) -> str:
    """
    Extract text content from a PDF file provided by URL or local path.
    
    Args:
        file_path: URL or local absolute path to the PDF.
        max_pages: Maximum number of pages to read (default: 20).
    """
    result = await pdf_tool.execute(file_path=file_path, max_pages=max_pages)
    if result.success:
        return str(result.data)
    return f"Error: {result.error}"


@mcp.tool()
async def fetch_market_data(symbol: str, start_date: str, end_date: str) -> str:
    """
    Fetch historical daily market data for a stock symbol.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', '600519.SS').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
    """
    result = await market_tool.execute(
        symbol=symbol, 
        start_date=start_date, 
        end_date=end_date
    )
    if result.success:
        return str(result.data)
    return f"Error: {result.error}"


@mcp.tool()
async def run_backtest(
    symbol: str, 
    strategy: str = "ma_cross", 
    initial_capital: float = 100000.0
) -> str:
    """
    Run a strategy backtest for a specific stock symbol.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL').
        strategy: Strategy name (currently only 'ma_cross').
        initial_capital: Initial capital amount.
    """
    result = await backtest_tool.execute(
        symbol=symbol,
        strategy=strategy,
        initial_capital=initial_capital
    )
    if result.success:
        return str(result.data)
    return f"Error: {result.error}"


if __name__ == "__main__":
    # This runs the MCP server on stdio by default
    mcp.run()
