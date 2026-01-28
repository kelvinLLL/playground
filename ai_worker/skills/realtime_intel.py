"""
Realtime Intelligence Skill - Fresh data from curated sources.

Provides GUARANTEED fresh content from sources with server-side time filtering:
- Hacker News (Algolia API with timestamp filter)
- Reddit (JSON API with t=day parameter)
- GitHub Trending (Direct scraping with since=daily)
- RSS Feeds (With publication date awareness)

All sources are FREE and require NO API keys.
"""

from typing import List, Optional

from ai_worker.skills.base import BaseSkill, SkillMetadata, SkillRegistry
from ai_worker.tools.base import BaseTool
from ai_worker.tools.rss_feed import RSSFeedTool
from ai_worker.tools.realtime_sources import (
    HackerNewsTodayTool,
    RedditDailyTool,
    GitHubTrendingTool,
)


@SkillRegistry.register
class RealtimeIntelSkill(BaseSkill):
    """
    Real-time intelligence gathering capability.
    
    Fetches today's content from high-quality curated sources.
    All sources have server-side time filtering for guaranteed freshness.
    """
    
    def __init__(self):
        self._tools: Optional[List[BaseTool]] = None
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="RealtimeIntel",
            description="Get today's news from Hacker News, Reddit, GitHub Trending",
            category="Information",
            emoji="🚀",
            trigger_phrases=[
                "what's trending",
                "today's news",
                "latest on hacker news",
                "github trending",
                "今天有什么新闻",
                "最新动态",
            ],
        )
    
    def get_tools(self) -> List[BaseTool]:
        if self._tools is None:
            self._tools = [
                HackerNewsTodayTool(),
                RedditDailyTool(),
                GitHubTrendingTool(),
                RSSFeedTool(),
            ]
        return self._tools
    
    def get_instructions(self) -> str:
        return """### Real-time Intelligence Best Practices
- Use `hackernews_today` for tech discussions and AI/ML news
- Use `reddit_daily` with subreddit="MachineLearning" or "LocalLLaMA" for community insights
- Use `github_trending` for today's hot open source projects
- Use `rss_feed` for official blog posts (may be less fresh)

These tools have SERVER-SIDE time filtering:
- HN: Uses Algolia numericFilters on created_at timestamp
- Reddit: Uses t=day parameter for last 24 hours
- GitHub: Uses since=daily for today's trending

Results are GUARANTEED to be from today/last 24 hours.
"""
