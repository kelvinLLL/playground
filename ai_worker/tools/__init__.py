"""Tools module for AI Worker - external tool integrations."""

from .base import BaseTool
from .market_data import MarketDataTool
from .backtest import BacktestTool
from .pdf_reader import PDFReaderTool
from .web_search import WebSearchTool
from .rss_feed import RSSFeedTool, MultiFeedTool
from .realtime_sources import (
    HackerNewsTodayTool,
    RedditDailyTool,
    GitHubTrendingTool,
    MultiRealtimeTool,
)

__all__ = [
    "BaseTool",
    "MarketDataTool",
    "BacktestTool",
    "PDFReaderTool",
    "WebSearchTool",
    "RSSFeedTool",
    "MultiFeedTool",
    "HackerNewsTodayTool",
    "RedditDailyTool",
    "GitHubTrendingTool",
    "MultiRealtimeTool",
]
