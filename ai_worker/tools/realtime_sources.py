"""
Real-time Data Source Tools.

Provides guaranteed fresh content from sources that support time-based filtering:
- Hacker News (Algolia API) - Today's stories with timestamp filtering
- Reddit (JSON API) - Top posts from last 24 hours
- GitHub Trending - Daily trending repos via scraping

All sources are FREE and require NO API keys.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional, List

import aiohttp

from ai_worker.tools.base import BaseTool, ToolResult
from ai_worker.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@ToolRegistry.register("hackernews_today")
class HackerNewsTodayTool(BaseTool):
    """
    Fetch today's Hacker News stories using Algolia API.
    
    Uses server-side timestamp filtering to guarantee freshness.
    Free, no API key required.
    """

    def __init__(self):
        super().__init__(
            name="hackernews_today",
            description="Get today's top Hacker News stories about AI/ML/tech",
        )
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
                    "description": "Search query (e.g., 'AI', 'LLM', 'machine learning')",
                    "default": "AI OR LLM OR machine learning",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results (1-30)",
                    "default": 15,
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "AI OR LLM OR machine learning")
        max_results = min(kwargs.get("max_results", 15), 30)

        try:
            session = await self._get_session()
            
            # Calculate start of today (UTC) as Unix timestamp
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            timestamp_threshold = int(today_start.timestamp())

            # Algolia API with time filter
            url = "https://hn.algolia.com/api/v1/search_by_date"
            params = {
                "query": query,
                "tags": "story",
                "numericFilters": f"created_at_i>{timestamp_threshold}",
                "hitsPerPage": max_results,
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(url, params=params, timeout=timeout) as response:
                if response.status != 200:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"Hacker News API error: {response.status}",
                    )

                data = await response.json()
                hits = data.get("hits", [])

                if not hits:
                    return ToolResult(
                        success=True,
                        data=f"No Hacker News stories found today for '{query}'",
                    )

                # Format results
                lines = [f"**🔥 Today's Hacker News** ({len(hits)} stories about '{query}')\n"]
                
                for i, hit in enumerate(hits, 1):
                    title = hit.get("title", "Untitled")
                    url = hit.get("url", "")
                    points = hit.get("points", 0)
                    comments = hit.get("num_comments", 0)
                    hn_url = f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                    
                    lines.append(f"{i}. **{title}**")
                    lines.append(f"   ⬆️ {points} points | 💬 {comments} comments")
                    if url:
                        lines.append(f"   🔗 {url}")
                    lines.append(f"   📰 {hn_url}")
                    lines.append("")

                return ToolResult(success=True, data="\n".join(lines))

        except Exception as e:
            logger.error(f"Hacker News error: {e}")
            return ToolResult(success=False, data=None, error=str(e))


@ToolRegistry.register("reddit_daily")
class RedditDailyTool(BaseTool):
    """
    Fetch today's top Reddit posts using JSON API.
    
    Uses t=day parameter to guarantee last 24 hours.
    Free, no API key required (just needs User-Agent).
    """

    def __init__(self):
        super().__init__(
            name="reddit_daily",
            description="Get today's top Reddit posts from AI/ML subreddits",
        )
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {"User-Agent": "AI-Worker-Bot/1.0 (Educational Research)"}
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subreddit": {
                    "type": "string",
                    "description": "Subreddit name (e.g., 'MachineLearning', 'LocalLLaMA')",
                    "default": "MachineLearning",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results (1-25)",
                    "default": 10,
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        subreddit = kwargs.get("subreddit", "MachineLearning")
        max_results = min(kwargs.get("max_results", 10), 25)

        try:
            session = await self._get_session()
            
            # t=day guarantees last 24 hours
            url = f"https://www.reddit.com/r/{subreddit}/top.json"
            params = {"t": "day", "limit": max_results}

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(url, params=params, timeout=timeout) as response:
                if response.status != 200:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"Reddit API error: {response.status}",
                    )

                data = await response.json()
                posts = data.get("data", {}).get("children", [])

                if not posts:
                    return ToolResult(
                        success=True,
                        data=f"No posts found today in r/{subreddit}",
                    )

                # Format results
                lines = [f"**💬 Today's Top r/{subreddit}** ({len(posts)} posts)\n"]
                
                for i, post in enumerate(posts, 1):
                    p = post.get("data", {})
                    title = p.get("title", "Untitled")
                    score = p.get("score", 0)
                    comments = p.get("num_comments", 0)
                    url = p.get("url", "")
                    permalink = f"https://reddit.com{p.get('permalink', '')}"
                    flair = p.get("link_flair_text", "")
                    
                    lines.append(f"{i}. **{title}**")
                    if flair:
                        lines.append(f"   🏷️ [{flair}]")
                    lines.append(f"   ⬆️ {score} upvotes | 💬 {comments} comments")
                    lines.append(f"   🔗 {permalink}")
                    if url and not url.startswith("https://www.reddit.com"):
                        lines.append(f"   📎 {url}")
                    lines.append("")

                return ToolResult(success=True, data="\n".join(lines))

        except Exception as e:
            logger.error(f"Reddit error: {e}")
            return ToolResult(success=False, data=None, error=str(e))


@ToolRegistry.register("github_trending")
class GitHubTrendingTool(BaseTool):
    """
    Fetch GitHub Trending repositories.
    
    Scrapes github.com/trending page for today's trending repos.
    Free, no API key required.
    """

    def __init__(self):
        super().__init__(
            name="github_trending",
            description="Get today's trending GitHub repositories",
        )
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "Programming language filter (e.g., 'python', 'typescript', or empty for all)",
                    "default": "",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results (1-25)",
                    "default": 15,
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        language = kwargs.get("language", "")
        max_results = min(kwargs.get("max_results", 15), 25)

        try:
            session = await self._get_session()
            
            # Build URL with language filter
            if language:
                url = f"https://github.com/trending/{language.lower()}?since=daily"
            else:
                url = "https://github.com/trending?since=daily"

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    return ToolResult(
                        success=False,
                        data=None,
                        error=f"GitHub Trending error: {response.status}",
                    )

                html = await response.text()
                repos = self._parse_trending_html(html, max_results)

                if not repos:
                    return ToolResult(
                        success=True,
                        data=f"No trending repos found for {language or 'all languages'}",
                    )

                # Format results
                lang_str = f" ({language})" if language else ""
                lines = [f"**📊 GitHub Trending Today{lang_str}** ({len(repos)} repos)\n"]
                
                for i, repo in enumerate(repos, 1):
                    lines.append(f"{i}. **{repo['name']}**")
                    if repo.get('description'):
                        lines.append(f"   {repo['description'][:150]}")
                    lines.append(f"   ⭐ {repo['stars']} | 🍴 {repo['forks']} | +{repo['stars_today']} today")
                    lines.append(f"   🔗 https://github.com/{repo['name']}")
                    if repo.get('language'):
                        lines.append(f"   📝 {repo['language']}")
                    lines.append("")

                return ToolResult(success=True, data="\n".join(lines))

        except Exception as e:
            logger.error(f"GitHub Trending error: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def _parse_trending_html(self, html: str, max_results: int) -> List[dict]:
        """Parse GitHub trending page HTML to extract repo info."""
        repos = []
        
        try:
            # Simple regex-based parsing (avoids BeautifulSoup dependency)
            import re
            
            # Find all repo articles
            article_pattern = r'<article class="Box-row">(.*?)</article>'
            articles = re.findall(article_pattern, html, re.DOTALL)
            
            for article in articles[:max_results]:
                repo = {}
                
                # Extract repo name (org/repo format)
                name_match = re.search(r'href="/([^"]+)"[^>]*>\s*<span[^>]*>([^<]+)</span>\s*/\s*<span[^>]*>([^<]+)</span>', article)
                if name_match:
                    org = name_match.group(2).strip()
                    name = name_match.group(3).strip()
                    repo['name'] = f"{org}/{name}"
                else:
                    # Alternative pattern
                    alt_match = re.search(r'href="/([^/]+/[^"]+)"', article)
                    if alt_match:
                        repo['name'] = alt_match.group(1)
                    else:
                        continue
                
                # Extract description
                desc_match = re.search(r'<p class="[^"]*text-gray[^"]*"[^>]*>\s*(.*?)\s*</p>', article, re.DOTALL)
                if desc_match:
                    desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
                    repo['description'] = desc
                
                # Extract language
                lang_match = re.search(r'itemprop="programmingLanguage">([^<]+)</span>', article)
                if lang_match:
                    repo['language'] = lang_match.group(1).strip()
                
                # Extract stars
                stars_match = re.search(r'href="/[^"]+/stargazers"[^>]*>\s*([0-9,]+)\s*</a>', article)
                if stars_match:
                    repo['stars'] = stars_match.group(1).strip()
                else:
                    repo['stars'] = "0"
                
                # Extract forks
                forks_match = re.search(r'href="/[^"]+/forks"[^>]*>\s*([0-9,]+)\s*</a>', article)
                if forks_match:
                    repo['forks'] = forks_match.group(1).strip()
                else:
                    repo['forks'] = "0"
                
                # Extract stars today
                today_match = re.search(r'([0-9,]+)\s*stars?\s*today', article)
                if today_match:
                    repo['stars_today'] = today_match.group(1).strip()
                else:
                    repo['stars_today'] = "0"
                
                repos.append(repo)
            
        except Exception as e:
            logger.warning(f"HTML parsing error: {e}")
        
        return repos


@ToolRegistry.register("multi_realtime")
class MultiRealtimeTool(BaseTool):
    """
    Fetch from multiple real-time sources in parallel.
    
    Combines: Hacker News + Reddit + GitHub Trending for comprehensive coverage.
    """

    def __init__(self):
        super().__init__(
            name="multi_realtime",
            description="Get today's top stories from HN, Reddit, and GitHub Trending",
        )
        self._hn_tool = HackerNewsTodayTool()
        self._reddit_tool = RedditDailyTool()
        self._github_tool = GitHubTrendingTool()

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "max_per_source": {
                    "type": "integer",
                    "description": "Maximum results per source (1-15)",
                    "default": 10,
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        max_per = min(kwargs.get("max_per_source", 10), 15)

        try:
            # Run all sources in parallel
            results = await asyncio.gather(
                self._hn_tool.execute(max_results=max_per),
                self._reddit_tool.execute(subreddit="MachineLearning", max_results=max_per),
                self._reddit_tool.execute(subreddit="LocalLLaMA", max_results=max_per // 2),
                self._github_tool.execute(max_results=max_per),
                return_exceptions=True,
            )

            combined = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Source {i} failed: {result}")
                    continue
                if result.success and result.data:
                    combined.append(result.data)

            if not combined:
                return ToolResult(
                    success=False,
                    data=None,
                    error="All real-time sources failed",
                )

            return ToolResult(
                success=True,
                data="\n\n---\n\n".join(combined),
            )

        except Exception as e:
            logger.error(f"Multi-realtime error: {e}")
            return ToolResult(success=False, data=None, error=str(e))
