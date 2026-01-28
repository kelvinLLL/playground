"""
Web Search Tool.

Allows AI workers to search the web for real-time information.
Supports multiple search backends: Tavily (default), DuckDuckGo (fallback).
"""

import logging
from typing import Any, Optional

import aiohttp

from ai_worker.tools.base import BaseTool, ToolResult
from ai_worker.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@ToolRegistry.register("web_search")
class WebSearchTool(BaseTool):
    """
    Tool for searching the web.

    Uses Tavily API as primary backend (requires API key).
    Falls back to DuckDuckGo search (free, no key needed).
    """

    def __init__(self, tavily_api_key: Optional[str] = None):
        super().__init__(
            name="web_search",
            description="Search the web for real-time information, news, and data.",
        )
        self.tavily_api_key = tavily_api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1-10)",
                    "default": 5,
                },
                "timelimit": {
                    "type": "string",
                    "description": "Time filter: 'd' (day), 'w' (week), 'm' (month), or None for all time",
                    "default": None,
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query")
        max_results = min(kwargs.get("max_results", 5), 10)
        timelimit = kwargs.get("timelimit")  # 'd', 'w', 'm', or None

        if not query:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: query",
            )

        try:
            if self.tavily_api_key:
                result = await self._search_tavily(query, max_results)
                if result.success:
                    return result
                logger.warning(f"Tavily search failed: {result.error}, falling back")

            return await self._search_duckduckgo(query, max_results, timelimit)

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    async def _search_tavily(self, query: str, max_results: int) -> ToolResult:
        session = await self._get_session()

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": True,
            "include_raw_content": False,
        }

        timeout = aiohttp.ClientTimeout(total=30)
        async with session.post(url, json=payload, timeout=timeout) as response:
            if response.status != 200:
                error_text = await response.text()
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Tavily API error ({response.status}): {error_text}",
                )

            data = await response.json()
            results = []

            if data.get("answer"):
                results.append({
                    "type": "answer",
                    "content": data["answer"],
                })

            for item in data.get("results", []):
                results.append({
                    "type": "result",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "score": item.get("score", 0),
                })

            formatted_output = self._format_results(query, results)
            return ToolResult(success=True, data=formatted_output)

    async def _search_duckduckgo(self, query: str, max_results: int, timelimit: str = None) -> ToolResult:
        """
        Search using DuckDuckGo.
        
        Args:
            query: Search query
            max_results: Max results to return
            timelimit: Time filter - 'd' (day), 'w' (week), 'm' (month), or None
        """
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                return ToolResult(
                    success=False,
                    data=None,
                    error="ddgs not installed. Run: pip install ddgs",
                )

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Build search kwargs with optional timelimit
            search_kwargs = {"max_results": max_results}
            if timelimit in ('d', 'w', 'm'):
                search_kwargs["timelimit"] = timelimit
                logger.info(f"DuckDuckGo search with timelimit='{timelimit}' for query: {query}")
            
            search_results = await loop.run_in_executor(
                None,
                lambda: list(DDGS().text(query, **search_kwargs))
            )

            if not search_results:
                return ToolResult(
                    success=True,
                    data=f"No results found for '{query}'. Try a different query.",
                )

            results = []
            for item in search_results:
                results.append({
                    "type": "result",
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                })

            formatted_output = self._format_results(query, results)
            return ToolResult(success=True, data=formatted_output)

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"DuckDuckGo search error: {str(e)}",
            )

    def _format_results(self, query: str, results: list[dict]) -> str:
        lines = [f"**Web Search Results for:** {query}\n"]

        for i, result in enumerate(results, 1):
            if result.get("type") == "answer":
                lines.append(f"**Summary:** {result['content']}\n")
            else:
                title = result.get("title", "Untitled")
                url = result.get("url", "")
                snippet = result.get("snippet", "")

                lines.append(f"{i}. **{title}**")
                if url:
                    lines.append(f"   URL: {url}")
                if snippet:
                    lines.append(f"   {snippet[:300]}{'...' if len(snippet) > 300 else ''}")
                lines.append("")

        return "\n".join(lines)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
