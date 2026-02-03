"""
Curated high-quality sources for Daily Brief.

Sources are organized by category and include:
- Direct URLs for scraping (Playwright)
- RSS feeds for subscription
- Site-specific search queries as fallback

Based on research of top AI/ML/Tech news sources.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class SourceType(Enum):
    """Type of source determines how to fetch content."""

    RSS = "rss"  # RSS/Atom feed - use feedparser
    SCRAPE = "scrape"  # Direct URL scraping - use Playwright
    SEARCH = "search"  # Site-specific search - use DuckDuckGo
    API = "api"  # API endpoint - custom handler


@dataclass
class Source:
    """
    Represents a single information source.

    Attributes:
        name: Display name of the source
        url: Main URL of the source
        source_type: How to fetch content (RSS, SCRAPE, SEARCH, API)
        category: Category for grouping in report
        emoji: Emoji for display
        language: Content language (en, zh)
        priority: 1=high, 2=medium, 3=low (affects inclusion in quick mode)
        rss_url: RSS feed URL if different from main URL
        search_query: Site-specific search query template
        max_items: Maximum items to fetch from this source
        enabled: Whether to include this source
    """

    name: str
    url: str
    source_type: SourceType
    category: str
    emoji: str
    language: str = "en"
    priority: int = 1
    rss_url: Optional[str] = None
    search_query: Optional[str] = None
    max_items: int = 5
    enabled: bool = True


# ============================================================
# AI/ML News Sources (Global)
# ============================================================

AI_NEWS_SOURCES = [
    # --- High Priority (Official Blogs) ---
    Source(
        name="OpenAI Blog",
        url="https://openai.com/blog",
        source_type=SourceType.SCRAPE,  # Cloudflare blocks RSS
        category="AI Research",
        emoji="🔬",
        language="en",
        priority=1,
    ),
    Source(
        name="Google AI Blog",
        url="https://ai.googleblog.com/",
        source_type=SourceType.RSS,
        rss_url="http://googleaiblog.blogspot.com/atom.xml",
        category="AI Research",
        emoji="🔬",
        language="en",
        priority=1,
    ),
    Source(
        name="DeepMind Blog",
        url="https://deepmind.com/blog",
        source_type=SourceType.RSS,
        rss_url="https://deepmind.com/blog/feed/basic/",
        category="AI Research",
        emoji="🔬",
        language="en",
        priority=1,
    ),
    Source(
        name="Anthropic",
        url="https://www.anthropic.com/news",
        source_type=SourceType.SCRAPE,
        category="AI Research",
        emoji="🔬",
        language="en",
        priority=1,
    ),
    Source(
        name="HuggingFace Blog",
        url="https://huggingface.co/blog",
        source_type=SourceType.RSS,
        rss_url="https://huggingface.co/blog/feed.xml",
        category="AI Research",
        emoji="🤗",
        language="en",
        priority=1,
    ),
    # --- Medium Priority (News Sites) ---
    Source(
        name="VentureBeat AI",
        url="https://venturebeat.com/category/ai/",
        source_type=SourceType.RSS,
        rss_url="https://venturebeat.com/category/ai/feed/",
        category="AI News",
        emoji="🤖",
        language="en",
        priority=2,
    ),
    Source(
        name="MIT Tech Review",
        url="https://www.technologyreview.com/",
        source_type=SourceType.RSS,
        rss_url="https://www.technologyreview.com/feed/",
        category="AI News",
        emoji="🤖",
        language="en",
        priority=2,
    ),
    Source(
        name="Wired AI",
        url="https://www.wired.com/tag/ai/",
        source_type=SourceType.RSS,
        rss_url="https://www.wired.com/feed/tag/ai/latest/rss",
        category="AI News",
        emoji="🤖",
        language="en",
        priority=2,
    ),
    Source(
        name="MarkTechPost",
        url="https://www.marktechpost.com/",
        source_type=SourceType.RSS,
        rss_url="https://www.marktechpost.com/feed",
        category="AI News",
        emoji="🤖",
        language="en",
        priority=2,
    ),
    # --- Low Priority (Newsletters/Blogs) ---
    Source(
        name="The Batch (Andrew Ng)",
        url="https://www.deeplearning.ai/the-batch/",
        source_type=SourceType.SCRAPE,
        category="AI Newsletter",
        emoji="📰",
        language="en",
        priority=3,
    ),
    Source(
        name="Latent Space",
        url="https://www.latent.space/",
        source_type=SourceType.RSS,
        rss_url="https://www.latent.space/feed",
        category="AI Newsletter",
        emoji="📰",
        language="en",
        priority=3,
    ),
]


# ============================================================
# Chinese AI/Tech News Sources
# ============================================================

CHINESE_SOURCES = [
    Source(
        name="AIBase",
        url="https://www.aibase.com/zh/news",
        source_type=SourceType.SCRAPE,
        category="AI News (中文)",
        emoji="🤖",
        language="zh",
        priority=1,
        max_items=15,
    ),
    Source(
        name="机器之心 (Synced)",
        url="https://www.jiqizhixin.com/",
        source_type=SourceType.SCRAPE,
        category="AI News (中文)",
        emoji="🤖",
        language="zh",
        priority=1,
    ),
    Source(
        name="量子位 (QbitAI)",
        url="https://www.qbitai.com/",
        source_type=SourceType.SCRAPE,
        category="AI News (中文)",
        emoji="🤖",
        language="zh",
        priority=1,
    ),
    Source(
        name="36氪",
        url="https://36kr.com/",
        source_type=SourceType.RSS,
        rss_url="https://36kr.com/feed",
        category="Tech Investment (中文)",
        emoji="💼",
        language="zh",
        priority=2,
    ),
    Source(
        name="虎嗅",
        url="https://www.huxiu.com/",
        source_type=SourceType.RSS,
        rss_url="https://www.huxiu.com/rss/0.xml",
        category="Tech Investment (中文)",
        emoji="💼",
        language="zh",
        priority=2,
    ),
]


# ============================================================
# GitHub / Open Source
# ============================================================

GITHUB_SOURCES = [
    Source(
        name="GitHub Trending (All)",
        url="https://github.com/trending",
        source_type=SourceType.SCRAPE,
        category="GitHub Trending",
        emoji="📊",
        language="en",
        priority=1,
        max_items=25,
    ),
    Source(
        name="GitHub Trending (Python)",
        url="https://github.com/trending/python?since=daily",
        source_type=SourceType.SCRAPE,
        category="GitHub Trending",
        emoji="🐍",
        language="en",
        priority=2,
    ),
    Source(
        name="GitHub Trending (TypeScript)",
        url="https://github.com/trending/typescript?since=daily",
        source_type=SourceType.SCRAPE,
        category="GitHub Trending",
        emoji="📘",
        language="en",
        priority=3,
    ),
]


# ============================================================
# Research Papers
# ============================================================

RESEARCH_SOURCES = [
    Source(
        name="HuggingFace Daily Papers",
        url="https://huggingface.co/papers",
        source_type=SourceType.SCRAPE,
        category="HuggingFace Papers",
        emoji="🤗",
        language="en",
        priority=1,
        max_items=15,
    ),
    Source(
        name="Papers With Code",
        url="https://paperswithcode.com/",
        source_type=SourceType.SCRAPE,
        category="Research Papers",
        emoji="📄",
        language="en",
        priority=1,
    ),
    Source(
        name="arXiv cs.LG (Machine Learning)",
        url="https://arxiv.org/list/cs.LG/recent",
        source_type=SourceType.RSS,
        rss_url="https://arxiv.org/rss/cs.LG",
        category="arXiv Papers",
        emoji="📄",
        language="en",
        priority=2,
        max_items=10,
    ),
    Source(
        name="arXiv cs.CL (NLP)",
        url="https://arxiv.org/list/cs.CL/recent",
        source_type=SourceType.RSS,
        rss_url="https://arxiv.org/rss/cs.CL",
        category="arXiv Papers",
        emoji="📄",
        language="en",
        priority=3,
    ),
    Source(
        name="arXiv cs.CV (Computer Vision)",
        url="https://arxiv.org/list/cs.CV/recent",
        source_type=SourceType.RSS,
        rss_url="https://arxiv.org/rss/cs.CV",
        category="arXiv Papers",
        emoji="📄",
        language="en",
        priority=3,
    ),
]


# ============================================================
# Tech Community / Discussion
# ============================================================

COMMUNITY_SOURCES = [
    Source(
        name="Hacker News",
        url="https://news.ycombinator.com/",
        source_type=SourceType.SEARCH,
        search_query="site:news.ycombinator.com AI machine learning today",
        category="Tech Community",
        emoji="🔥",
        language="en",
        priority=2,
    ),
    Source(
        name="Reddit r/MachineLearning",
        url="https://www.reddit.com/r/MachineLearning/",
        source_type=SourceType.RSS,
        rss_url="https://www.reddit.com/r/MachineLearning/top/.rss?t=day",
        category="Tech Community",
        emoji="💬",
        language="en",
        priority=2,
    ),
    Source(
        name="Reddit r/LocalLLaMA",
        url="https://www.reddit.com/r/LocalLLaMA/",
        source_type=SourceType.RSS,
        rss_url="https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day",
        category="Tech Community",
        emoji="💬",
        language="en",
        priority=2,
        max_items=8,
    ),
    Source(
        name="Reddit r/algotrading",
        url="https://www.reddit.com/r/algotrading/",
        source_type=SourceType.RSS,
        rss_url="https://www.reddit.com/r/algotrading/top/.rss?t=day",
        category="Tech Community",
        emoji="📈",
        language="en",
        priority=2,
        max_items=6,
    ),
    Source(
        name="Reddit r/ChatGPT",
        url="https://www.reddit.com/r/ChatGPT/",
        source_type=SourceType.RSS,
        rss_url="https://www.reddit.com/r/ChatGPT/top/.rss?t=day",
        category="Tech Community",
        emoji="🤖",
        language="en",
        priority=2,
        max_items=6,
    ),
    Source(
        name="Reddit r/startups",
        url="https://www.reddit.com/r/startups/",
        source_type=SourceType.RSS,
        rss_url="https://www.reddit.com/r/startups/top/.rss?t=day",
        category="Tech Community",
        emoji="🚀",
        language="en",
        priority=2,
        max_items=6,
    ),
    Source(
        name="Product Hunt AI",
        url="https://www.producthunt.com/topics/artificial-intelligence",
        source_type=SourceType.SCRAPE,
        category="AI Products",
        emoji="🚀",
        language="en",
        priority=3,
    ),
]


# ============================================================
# Investment / Business
# ============================================================

INVESTMENT_SOURCES = [
    Source(
        name="TechCrunch",
        url="https://techcrunch.com/",
        source_type=SourceType.RSS,
        rss_url="https://techcrunch.com/feed/",
        category="Tech Investment",
        emoji="💼",
        language="en",
        priority=2,
    ),
    Source(
        name="Crunchbase News",
        url="https://news.crunchbase.com/",
        source_type=SourceType.RSS,
        rss_url="https://news.crunchbase.com/feed",
        category="Tech Investment",
        emoji="💼",
        language="en",
        priority=2,
    ),
    Source(
        name="Bloomberg Technology",
        url="https://www.bloomberg.com/technology",
        source_type=SourceType.RSS,
        rss_url="https://feeds.bloomberg.com/technology/news.rss",
        category="Tech Investment",
        emoji="💼",
        language="en",
        priority=3,
    ),
]


# ============================================================
# Source Profiles (Preset Combinations)
# ============================================================


def get_all_sources() -> List[Source]:
    """Get all defined sources."""
    return (
        AI_NEWS_SOURCES
        + CHINESE_SOURCES
        + GITHUB_SOURCES
        + RESEARCH_SOURCES
        + COMMUNITY_SOURCES
        + INVESTMENT_SOURCES
    )


def get_sources_by_priority(max_priority: int = 2) -> List[Source]:
    """Get sources up to a certain priority level (1=high, 2=medium, 3=low)."""
    return [s for s in get_all_sources() if s.priority <= max_priority and s.enabled]


def get_sources_by_category(category: str) -> List[Source]:
    """Get sources for a specific category."""
    return [s for s in get_all_sources() if s.category == category and s.enabled]


def get_sources_by_language(language: str) -> List[Source]:
    """Get sources for a specific language (en, zh)."""
    return [s for s in get_all_sources() if s.language == language and s.enabled]


# ============================================================
# Pre-built Source Profiles
# ============================================================

# Full daily brief - all high and medium priority sources
DEFAULT_PROFILE: List[Source] = get_sources_by_priority(2)

# Quick daily brief - only high priority sources (faster)
QUICK_PROFILE: List[Source] = get_sources_by_priority(1)

# Chinese-focused profile
CHINESE_PROFILE: List[Source] = (
    CHINESE_SOURCES
    + [s for s in GITHUB_SOURCES if s.priority == 1]
    + [s for s in RESEARCH_SOURCES if s.priority == 1]
)

# Research-focused profile
RESEARCH_PROFILE: List[Source] = RESEARCH_SOURCES + [
    s for s in AI_NEWS_SOURCES if "Research" in s.category
]

# Developer-focused profile
DEVELOPER_PROFILE: List[Source] = (
    GITHUB_SOURCES
    + COMMUNITY_SOURCES
    + [s for s in AI_NEWS_SOURCES if s.priority == 1][:3]
)


# ============================================================
# Legacy SEARCH_TOPICS compatibility
# ============================================================


def sources_to_search_topics(sources: List[Source]) -> List[dict]:
    """
    Convert Source objects to legacy SEARCH_TOPICS format for backward compatibility.

    This allows gradual migration - you can use either the new Source-based system
    or fall back to the old search-based approach.
    """
    topics = []
    for source in sources:
        if source.source_type == SourceType.SEARCH:
            query = (
                source.search_query or f"site:{source.url.split('//')[1].split('/')[0]}"
            )
        else:
            # For RSS/SCRAPE sources, create a site-specific search as fallback
            domain = source.url.split("//")[1].split("/")[0]
            query = f"site:{domain} latest news today"

        topics.append(
            {
                "category": source.category,
                "query": query,
                "emoji": source.emoji,
                "source": source,  # Include source object for enhanced processing
            }
        )

    return topics
