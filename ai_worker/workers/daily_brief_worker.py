"""
Daily Briefing Worker implementation.

Generates daily intelligence reports by searching, scraping, and synthesizing
information from multiple curated high-quality sources.

Supports:
- RSS feeds (official blogs, news sites)
- Direct URL scraping (GitHub Trending, HuggingFace Papers)
- Site-specific search (fallback)
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, List, Optional

from ai_worker.core.message import (
    MessageType,
    StandardMessage,
    StandardResponse,
)
from ai_worker.llm.base import BaseLLM
from ai_worker.workers.base import BaseWorker, WorkerConfig
from ai_worker.tools.registry import ToolRegistry

# Import curated sources config
from ai_worker.config.curated_sources import (
    Source,
    SourceType,
    DEFAULT_PROFILE,
    QUICK_PROFILE,
    get_sources_by_priority,
)

logger = logging.getLogger(__name__)


class DailyBriefWorker(BaseWorker):
    """
    Daily Intelligence Briefing Generator.

    Workflow:
    1. Scouting - Fetch from curated sources (RSS, scrape, search)
    2. Deep Dive - Scrape high-value URLs (Playwright)
    3. Editorial - LLM synthesis
    4. Delivery - Write report + notify
    
    Supports two modes:
    - Curated Sources (NEW): Uses predefined high-quality sources from curated_sources.py
    - Search Topics (LEGACY): Falls back to generic search queries
    """

    # Legacy search topics (fallback if curated sources fail)
    SEARCH_TOPICS = [
        {"category": "AI/Tech News", "query": "AI artificial intelligence news today", "emoji": "🤖"},
        {"category": "GitHub Trending", "query": "site:github.com trending repositories stars today", "emoji": "📊"},
        {"category": "HuggingFace Trending", "query": "site:huggingface.co trending models papers daily", "emoji": "🤗"},
        {"category": "Investment", "query": "tech stock market news today investment", "emoji": "💡"},
    ]

    def __init__(self, llm: BaseLLM, use_curated_sources: bool = True, quick_mode: bool = False):
        """
        Initialize the Daily Brief Worker.
        
        Args:
            llm: LLM client for synthesis
            use_curated_sources: Use new curated sources system (default True)
            quick_mode: Use fewer sources for faster generation (default False)
        """
        config = WorkerConfig(
            name="DailyBrief",
            description="Daily Intelligence Briefing Generator. Creates comprehensive daily reports.",
            system_prompt=(
                "You are an Elite Intelligence Analyst and Editor. "
                "Your role is to synthesize raw information into actionable insights. "
                "Guidelines:\n"
                "1. Be concise but comprehensive\n"
                "2. Highlight key trends and patterns\n"
                "3. Provide actionable takeaways\n"
                "4. Use clear structure with headers\n"
                "5. Cite sources when available"
            ),
            tools=["search", "browser_navigate", "browser_snapshot", "write_file", "rss_feed"],
        )
        super().__init__(config)
        self.llm = llm
        self.use_curated_sources = use_curated_sources
        self.quick_mode = quick_mode
        
        # Select source profile based on mode
        if quick_mode:
            self.sources = QUICK_PROFILE
        else:
            self.sources = DEFAULT_PROFILE
        
        # Register tools
        self._init_tools()

    def _init_tools(self) -> None:
        """Initialize tools from registry."""
        # DuckDuckGo search (free, unlimited)
        try:
            search_tool = ToolRegistry.create_tool("duckduckgo__search")
            self._tools["search"] = search_tool
            logger.info("Registered duckduckgo__search")
        except Exception as e:
            logger.warning(f"Failed to register duckduckgo search: {e}")

        # Playwright browser tools
        try:
            nav_tool = ToolRegistry.create_tool("playwright__browser_navigate")
            self._tools["browser_navigate"] = nav_tool
            logger.info("Registered playwright__browser_navigate")
        except Exception as e:
            logger.warning(f"Failed to register playwright navigate: {e}")

        try:
            snapshot_tool = ToolRegistry.create_tool("playwright__browser_snapshot")
            self._tools["browser_snapshot"] = snapshot_tool
            logger.info("Registered playwright__browser_snapshot")
        except Exception as e:
            logger.warning(f"Failed to register playwright snapshot: {e}")

        # Filesystem write
        try:
            write_tool = ToolRegistry.create_tool("filesystem__write_file")
            self._tools["write_file"] = write_tool
            logger.info("Registered filesystem__write_file")
        except Exception as e:
            logger.warning(f"Failed to register filesystem write: {e}")
        
        # RSS feed tool
        try:
            from ai_worker.tools.rss_feed import RSSFeedTool
            self._tools["rss_feed"] = RSSFeedTool()
            logger.info("Registered rss_feed tool")
        except Exception as e:
            logger.warning(f"Failed to register RSS feed tool: {e}")
        
        # === NEW: Real-time source tools (guaranteed fresh) ===
        try:
            from ai_worker.tools.realtime_sources import (
                HackerNewsTodayTool,
                RedditDailyTool,
                GitHubTrendingTool,
            )
            self._tools["hackernews"] = HackerNewsTodayTool()
            self._tools["reddit"] = RedditDailyTool()
            self._tools["github_trending"] = GitHubTrendingTool()
            logger.info("Registered real-time source tools (HN, Reddit, GitHub Trending)")
        except Exception as e:
            logger.warning(f"Failed to register real-time tools: {e}")

    async def process(
        self,
        message: StandardMessage,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        """
        Process a request to generate daily brief.
        
        Can be triggered manually via Discord or by scheduler.
        """
        try:
            return await self.generate_brief(notifier)
        except Exception as e:
            logger.error(f"Error in DailyBriefWorker: {e}")
            return StandardResponse(content=f"Brief generation failed: {str(e)}")

    async def generate_brief(
        self,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        """
        Generate the daily intelligence brief.
        
        Args:
            notifier: Optional callback for progress updates
            
        Returns:
            StandardResponse with the brief content
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        if notifier:
            await notifier(f"📋 Starting Daily Brief generation for {today}...")

        # Phase 1: Scouting - Search for information
        if notifier:
            await notifier("🔍 **Phase 1/4**: Scouting - Searching for trending topics...")
        
        search_results = await self._phase_scouting(notifier)

        # Phase 2: Deep Dive - Scrape detailed content (optional, can be slow)
        if notifier:
            await notifier("🌐 **Phase 2/4**: Deep Dive - Analyzing top sources...")
        
        detailed_content = await self._phase_deep_dive(search_results, notifier)

        # Phase 3: Editorial - LLM synthesis
        if notifier:
            await notifier("✍️ **Phase 3/4**: Editorial - Synthesizing insights...")
        
        report = await self._phase_editorial(search_results, detailed_content, today, notifier)

        # Phase 4: Delivery - Save and notify
        if notifier:
            await notifier("📤 **Phase 4/4**: Delivery - Saving report...")
        
        file_path = await self._phase_delivery(report, today, notifier)

        # Build response - return file as attachment instead of summary
        response_content = f"📋 **Daily Brief for {today}** generated!"

        return StandardResponse(
            content=response_content,
            message_type=MessageType.FILE,
            extras={"file_path": file_path}
        )

    async def _phase_scouting(
        self,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> dict[str, str]:
        """
        Phase 1: Fetch content from curated sources or search.
        
        Uses the new curated sources system if enabled, otherwise falls back
        to legacy search-based approach.
        
        Returns:
            Dict mapping category to content
        """
        results = {}
        
        if self.use_curated_sources:
            results = await self._fetch_curated_sources(notifier)
            
            # If curated sources yielded no results, fall back to search
            if not results or all(not v for v in results.values()):
                logger.warning("Curated sources returned no data, falling back to search")
                results = await self._fetch_via_search(notifier)
        else:
            results = await self._fetch_via_search(notifier)
        
        return results

    async def _fetch_curated_sources(
        self,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> dict[str, str]:
        """
        Fetch content from curated sources (RSS, scrape, search) + real-time APIs.
        
        Returns:
            Dict mapping category to formatted content
        """
        results = {}
        rss_tool = self._tools.get("rss_feed")
        search_tool = self._tools.get("search")
        
        # === NEW: Fetch from real-time APIs FIRST (guaranteed fresh) ===
        if notifier:
            await notifier("  🚀 Fetching real-time sources (HN, Reddit, GitHub Trending)...")
        
        await self._fetch_realtime_sources(results, notifier)
        
        # Group sources by type for efficient processing
        rss_sources = [s for s in self.sources if s.source_type == SourceType.RSS and s.enabled]
        scrape_sources = [s for s in self.sources if s.source_type == SourceType.SCRAPE and s.enabled]
        search_sources = [s for s in self.sources if s.source_type == SourceType.SEARCH and s.enabled]
        
        # === Fetch RSS feeds in parallel ===
        if rss_sources and rss_tool:
            if notifier:
                await notifier(f"  📡 Fetching {len(rss_sources)} RSS feeds...")
            
            rss_tasks = []
            for source in rss_sources:
                rss_url = source.rss_url or source.url
                task = rss_tool.execute(
                    url=rss_url,
                    max_items=source.max_items,
                    source_name=source.name
                )
                rss_tasks.append((source, task))
            
            # Gather all RSS results
            for source, task in rss_tasks:
                try:
                    result = await task
                    if result.success and result.data:
                        formatted = result.data.get("formatted", "")
                        category = source.category
                        if category not in results:
                            results[category] = ""
                        results[category] += f"\n\n### {source.emoji} {source.name}\n{formatted}"
                        logger.info(f"RSS: Got {result.data.get('item_count', 0)} items from {source.name}")
                    else:
                        logger.warning(f"RSS fetch failed for {source.name}: {result.error}")
                except Exception as e:
                    logger.error(f"RSS error for {source.name}: {e}")
                
                await asyncio.sleep(0.1)  # Small delay
        
        # === Scrape sources (use timelimit='d' search for freshness) ===
        if scrape_sources and search_tool:
            if notifier:
                await notifier(f"  🌐 Fetching {len(scrape_sources)} web sources...")
            
            for source in scrape_sources:
                # Skip GitHub Trending - already fetched via dedicated tool
                if "github.com/trending" in source.url:
                    continue
                    
                try:
                    # Use site-specific search with time filter
                    domain = source.url.split("//")[1].split("/")[0]
                    query = f"site:{domain} latest"
                    
                    if notifier:
                        await notifier(f"    {source.emoji} {source.name}...")
                    
                    # Add timelimit='d' for freshness
                    result = await search_tool.execute(
                        query=query, 
                        max_results=source.max_items,
                        timelimit='d'  # Last 24 hours
                    )
                    
                    if result.success and result.data:
                        category = source.category
                        if category not in results:
                            results[category] = ""
                        results[category] += f"\n\n### {source.emoji} {source.name}\n{result.data}"
                        logger.info(f"Scrape (via search): Got results for {source.name}")
                    else:
                        logger.warning(f"Scrape failed for {source.name}: {result.error}")
                        
                except Exception as e:
                    logger.error(f"Scrape error for {source.name}: {e}")
                
                await asyncio.sleep(0.3)  # Delay between scrapes
        
        # === Site-specific searches (with time filter) ===
        if search_sources and search_tool:
            if notifier:
                await notifier(f"  🔍 Running {len(search_sources)} site searches...")
            
            for source in search_sources:
                # Skip Hacker News - already fetched via dedicated tool
                if "news.ycombinator.com" in source.url:
                    continue
                    
                try:
                    query = source.search_query or f"site:{source.url.split('//')[1].split('/')[0]}"
                    
                    # Add timelimit='d' for freshness
                    result = await search_tool.execute(
                        query=query, 
                        max_results=source.max_items,
                        timelimit='d'  # Last 24 hours
                    )
                    
                    if result.success and result.data:
                        category = source.category
                        if category not in results:
                            results[category] = ""
                        results[category] += f"\n\n### {source.emoji} {source.name}\n{result.data}"
                        logger.info(f"Search: Got results for {source.name}")
                        
                except Exception as e:
                    logger.error(f"Search error for {source.name}: {e}")
                
                await asyncio.sleep(0.3)
        
        return results

    async def _fetch_realtime_sources(
        self,
        results: dict[str, str],
        notifier: Optional[Callable[[str], Any]] = None
    ) -> None:
        """
        Fetch from real-time APIs with guaranteed freshness.
        
        These sources have server-side time filtering:
        - Hacker News Algolia API (timestamp filter)
        - Reddit JSON API (t=day parameter)
        - GitHub Trending (daily since=daily)
        """
        import asyncio
        
        hn_tool = self._tools.get("hackernews")
        reddit_tool = self._tools.get("reddit")
        github_tool = self._tools.get("github_trending")
        
        tasks = []
        
        # Hacker News - today's AI/ML stories
        if hn_tool:
            tasks.append(("Hacker News", "Tech Community", hn_tool.execute(
                query="AI OR LLM OR machine learning OR GPT",
                max_results=15
            )))
        
        # Reddit - today's top from r/MachineLearning and r/LocalLLaMA
        if reddit_tool:
            tasks.append(("r/MachineLearning", "Tech Community", reddit_tool.execute(
                subreddit="MachineLearning",
                max_results=10
            )))
            tasks.append(("r/LocalLLaMA", "Tech Community", reddit_tool.execute(
                subreddit="LocalLLaMA",
                max_results=8
            )))
        
        # GitHub Trending - today's trending repos
        if github_tool:
            tasks.append(("GitHub Trending (All)", "GitHub Trending", github_tool.execute(
                language="",
                max_results=15
            )))
            tasks.append(("GitHub Trending (Python)", "GitHub Trending", github_tool.execute(
                language="python",
                max_results=10
            )))
        
        # Execute all in parallel
        if tasks:
            task_results = await asyncio.gather(
                *[t[2] for t in tasks],
                return_exceptions=True
            )
            
            for i, result in enumerate(task_results):
                name, category, _ = tasks[i]
                
                if isinstance(result, Exception):
                    logger.warning(f"Real-time source {name} failed: {result}")
                    continue
                
                if result.success and result.data:
                    if category not in results:
                        results[category] = ""
                    results[category] += f"\n\n{result.data}"
                    logger.info(f"Real-time: Got fresh data from {name}")
                else:
                    logger.warning(f"Real-time source {name} returned no data: {result.error}")

    async def _fetch_via_search(
        self,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> dict[str, str]:
        """
        Legacy: Fetch content via generic search queries.
        
        Returns:
            Dict mapping category to search results
        """
        results = {}
        search_tool = self._tools.get("search")
        
        if not search_tool:
            logger.warning("Search tool not available")
            return results

        for topic in self.SEARCH_TOPICS:
            category = topic["category"]
            query = topic["query"]
            emoji = topic["emoji"]
            
            try:
                if notifier:
                    await notifier(f"  {emoji} Searching: {category}...")
                
                result = await search_tool.execute(query=query, max_results=5)
                
                if result.success and result.data:
                    results[category] = result.data
                    logger.info(f"Got results for {category}")
                else:
                    results[category] = f"No results found. Error: {result.error}"
                    logger.warning(f"No results for {category}: {result.error}")
                    
            except Exception as e:
                logger.error(f"Search failed for {category}: {e}")
                results[category] = f"Search failed: {str(e)}"
            
            # Small delay to be nice to the API
            await asyncio.sleep(0.5)

        return results

    async def _phase_deep_dive(
        self,
        search_results: dict[str, str],
        notifier: Optional[Callable[[str], Any]] = None
    ) -> dict[str, str]:
        """
        Phase 2: Scrape detailed content from top URLs.
        
        For now, we'll use the search results directly.
        Playwright scraping can be added for specific high-value URLs.
        
        Returns:
            Dict with additional detailed content
        """
        # TODO: Implement Playwright scraping for top URLs
        # For MVP, we return empty dict and rely on search results
        detailed = {}
        
        # Example: Could scrape GitHub trending page
        # nav_tool = self._tools.get("browser_navigate")
        # snapshot_tool = self._tools.get("browser_snapshot")
        # if nav_tool and snapshot_tool:
        #     await nav_tool.execute(url="https://github.com/trending")
        #     result = await snapshot_tool.execute()
        #     detailed["github_trending"] = result.data
        
        return detailed

    async def _phase_editorial(
        self,
        search_results: dict[str, str],
        detailed_content: dict[str, str],
        date: str,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> str:
        """
        Phase 3: LLM synthesis of all gathered information.
        
        Returns:
            Formatted markdown report
        """
        # Build context for LLM
        context_parts = []
        for category, content in search_results.items():
            context_parts.append(f"## {category}\n{content}\n")
        
        for source, content in detailed_content.items():
            context_parts.append(f"## Additional: {source}\n{content}\n")
        
        full_context = "\n".join(context_parts)
        
        # DEBUG: Log context before LLM call
        logger.info(f"[DEBUG] full_context length: {len(full_context)} chars")
        logger.debug(f"[DEBUG] full_context preview: {full_context[:500]}...")
        
        # Truncate if too long
        if len(full_context) > 50000:
            full_context = full_context[:50000] + "\n\n[Content truncated...]"

        prompt = f"""Based on the following search results from today ({date}), create a comprehensive Daily Intelligence Brief.

RAW DATA:
{full_context}

Generate a well-structured report in Markdown format with:

# Daily Brief - {date}

## 🔥 Today's Highlights
(3-5 bullet points of the most important takeaways)

## 🤖 AI/Tech News
(Summarize the top AI and technology news with source links if available)

## 📊 GitHub Trending
(List notable trending repositories with repo names, star counts, and brief descriptions. Focus on AI/ML, dev tools, and interesting new projects. Mention related ecosystem tools if relevant.)

## 🤗 HuggingFace Trending
(List trending models and papers from HuggingFace. Include model names, what they do, and why they're notable.)

## 💡 Investment Insights
(Key observations relevant to tech investing)

## 📝 Editor's Notes
(Your analysis of patterns and trends)

Be concise but informative. Focus on actionable insights."""

        try:
            logger.info(f"[DEBUG] Calling LLM with prompt length: {len(prompt)} chars")
            response = await self.llm.complete(prompt, max_tokens=3000)
            
            # DEBUG: Log raw LLM response
            logger.info(f"[DEBUG] LLM response object: {type(response)}")
            logger.info(f"[DEBUG] LLM response.content type: {type(response.content)}")
            logger.info(f"[DEBUG] LLM response.content length: {len(response.content) if response.content else 0}")
            if response.content:
                logger.debug(f"[DEBUG] LLM response preview: {response.content[:300]}...")
            
            content = response.content.strip() if response.content else ""
            
            # Check if LLM returned empty content (API limit or error)
            if not content:
                logger.warning("LLM returned empty content, using fallback report")
                return self._build_fallback_report(date, search_results)
            
            logger.info(f"LLM generated report with {len(content)} characters")
            return content
            
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            return self._build_fallback_report(date, search_results)

    def _build_fallback_report(self, date: str, search_results: dict[str, str]) -> str:
        """Build a fallback report from raw search results."""
        fallback_report = f"# Daily Brief - {date}\n\n"
        fallback_report += "⚠️ *LLM synthesis unavailable, showing raw search results*\n\n"
        for category, content in search_results.items():
            fallback_report += f"## {category}\n{content}\n\n"
        return fallback_report

    async def _phase_delivery(
        self,
        report: str,
        date: str,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> str:
        """
        Phase 4: Save report to filesystem.
        
        Returns:
            File path where report was saved
        """
        # DEBUG: Log report content before saving
        logger.info(f"[DEBUG] _phase_delivery received report length: {len(report) if report else 0}")
        if report:
            logger.debug(f"[DEBUG] Report preview: {report[:300]}...")
        
        # Use timestamp to avoid overwriting previous reports
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"daily_brief_{timestamp}.md"
        file_path = f"/Users/haojunliu/Easy/Projects/playground/ai_worker/reports/{filename}"
        
        # Validate report content
        if not report or not report.strip():
            logger.error("Report content is empty, cannot save")
            report = f"# Daily Brief - {date}\n\n⚠️ Report generation failed - no content available."
        
        saved = False
        write_tool = self._tools.get("write_file")
        
        # Try MCP tool first
        if write_tool:
            try:
                result = await write_tool.execute(path=file_path, content=report)
                if result.success:
                    logger.info(f"Report saved via MCP to {file_path}")
                    saved = True
                else:
                    logger.warning(f"MCP write failed: {result.error}")
            except Exception as e:
                logger.warning(f"MCP write exception: {e}")
        
        # Fallback to local file write
        if not saved:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                logger.info(f"Report saved locally to {file_path}")
                saved = True
            except Exception as e:
                logger.error(f"Local file write failed: {e}")
        
        return file_path

    def _extract_summary(self, report: str) -> str:
        """Extract the highlights section from the report."""
        lines = report.split("\n")
        summary_lines = []
        in_highlights = False
        
        for line in lines:
            if "Highlights" in line or "highlights" in line:
                in_highlights = True
                continue
            if in_highlights:
                if line.startswith("##"):
                    break
                if line.strip():
                    summary_lines.append(line)
        
        if summary_lines:
            return "\n".join(summary_lines[:5])  # First 5 lines max
        
        # Fallback: first 500 chars
        return report[:500] + "..."
