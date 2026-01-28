"""
RSS Feed Reader Tool.

Fetches and parses RSS/Atom feeds for content aggregation.
Used by DailyBriefWorker for curated news sources.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, List, Optional
from dataclasses import dataclass

from ai_worker.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Try to import feedparser, with graceful fallback
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser not installed. RSS tool will be unavailable. Install with: pip install feedparser")


@dataclass
class FeedItem:
    """Represents a single item from an RSS feed."""
    title: str
    link: str
    description: str
    published: Optional[str] = None
    author: Optional[str] = None
    source_name: Optional[str] = None


class RSSFeedTool(BaseTool):
    """
    Tool for fetching and parsing RSS/Atom feeds.
    
    Supports:
    - RSS 2.0
    - Atom 1.0
    - Various feed formats via feedparser
    """

    def __init__(self):
        super().__init__(
            name="rss_feed",
            description="Fetch and parse RSS/Atom feeds to get latest articles"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "RSS feed URL to fetch"
                },
                "max_items": {
                    "type": "integer",
                    "description": "Maximum number of items to return",
                    "default": 10
                },
                "source_name": {
                    "type": "string",
                    "description": "Name of the source for attribution"
                }
            },
            "required": ["url"]
        }

    async def execute(
        self,
        url: str,
        max_items: int = 10,
        source_name: Optional[str] = None,
        **kwargs: Any
    ) -> ToolResult:
        """
        Fetch and parse an RSS feed.
        
        Args:
            url: RSS feed URL
            max_items: Maximum items to return
            source_name: Name to attribute items to
            
        Returns:
            ToolResult with parsed feed items
        """
        if not FEEDPARSER_AVAILABLE:
            return ToolResult(
                success=False,
                data=None,
                error="feedparser not installed. Run: pip install feedparser"
            )

        try:
            # Run feedparser in thread pool (it's synchronous)
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)
            
            if feed.bozo and not feed.entries:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Failed to parse feed: {feed.bozo_exception}"
                )
            
            items: List[FeedItem] = []
            feed_title = feed.feed.get('title', source_name or 'Unknown')
            
            for entry in feed.entries[:max_items]:
                # Extract published date
                published = None
                if hasattr(entry, 'published'):
                    published = entry.published
                elif hasattr(entry, 'updated'):
                    published = entry.updated
                
                # Extract description/summary
                description = ""
                if hasattr(entry, 'summary'):
                    description = entry.summary
                elif hasattr(entry, 'description'):
                    description = entry.description
                
                # Clean HTML from description
                description = self._clean_html(description)
                
                # Truncate long descriptions
                if len(description) > 500:
                    description = description[:500] + "..."
                
                item = FeedItem(
                    title=entry.get('title', 'No title'),
                    link=entry.get('link', ''),
                    description=description,
                    published=published,
                    author=entry.get('author'),
                    source_name=source_name or feed_title,
                )
                items.append(item)
            
            # Format as markdown for LLM consumption
            formatted = self._format_items(items, feed_title)
            
            logger.info(f"Fetched {len(items)} items from {url}")
            
            return ToolResult(
                success=True,
                data={
                    "items": [self._item_to_dict(item) for item in items],
                    "formatted": formatted,
                    "feed_title": feed_title,
                    "item_count": len(items),
                }
            )
            
        except Exception as e:
            logger.error(f"RSS fetch error for {url}: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def _item_to_dict(self, item: FeedItem) -> dict:
        """Convert FeedItem to dictionary."""
        return {
            "title": item.title,
            "link": item.link,
            "description": item.description,
            "published": item.published,
            "author": item.author,
            "source": item.source_name,
        }

    def _format_items(self, items: List[FeedItem], feed_title: str) -> str:
        """Format items as markdown for LLM."""
        if not items:
            return f"No items found from {feed_title}"
        
        lines = [f"### {feed_title}\n"]
        for i, item in enumerate(items, 1):
            lines.append(f"**{i}. [{item.title}]({item.link})**")
            if item.description:
                lines.append(f"   {item.description}")
            if item.published:
                lines.append(f"   *Published: {item.published}*")
            lines.append("")
        
        return "\n".join(lines)


class MultiFeedTool(BaseTool):
    """
    Tool for fetching multiple RSS feeds in parallel.
    
    Useful for aggregating content from many sources efficiently.
    """

    def __init__(self):
        super().__init__(
            name="multi_feed",
            description="Fetch multiple RSS feeds in parallel"
        )
        self.rss_tool = RSSFeedTool()

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "feeds": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "name": {"type": "string"},
                            "max_items": {"type": "integer"}
                        },
                        "required": ["url"]
                    },
                    "description": "List of feeds to fetch"
                }
            },
            "required": ["feeds"]
        }

    async def execute(
        self,
        feeds: List[dict],
        **kwargs: Any
    ) -> ToolResult:
        """
        Fetch multiple feeds in parallel.
        
        Args:
            feeds: List of feed configs with url, name, max_items
            
        Returns:
            ToolResult with aggregated feed data
        """
        tasks = []
        for feed in feeds:
            task = self.rss_tool.execute(
                url=feed["url"],
                max_items=feed.get("max_items", 10),
                source_name=feed.get("name")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_items = []
        all_formatted = []
        errors = []
        
        for feed, result in zip(feeds, results):
            if isinstance(result, Exception):
                errors.append(f"{feed.get('name', feed['url'])}: {str(result)}")
            elif result.success:
                all_items.extend(result.data.get("items", []))
                all_formatted.append(result.data.get("formatted", ""))
            else:
                errors.append(f"{feed.get('name', feed['url'])}: {result.error}")
        
        return ToolResult(
            success=len(all_items) > 0,
            data={
                "items": all_items,
                "formatted": "\n\n".join(all_formatted),
                "total_items": len(all_items),
                "feeds_fetched": len(feeds) - len(errors),
                "errors": errors,
            },
            error="; ".join(errors) if errors else None
        )


# Note: RSS tools are NOT auto-registered with ToolRegistry because:
# 1. ToolRegistry.register is a decorator, not a direct method call
# 2. These tools are instantiated directly in DailyBriefWorker._init_tools()
# To use via registry, add: @ToolRegistry.register("rss_feed") above the class
