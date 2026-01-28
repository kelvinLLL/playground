"""
Search Skill - Web search capabilities.

Provides unified access to multiple search backends:
- DuckDuckGo (free, no API key)
- Tavily (optional, higher quality)

This is a foundational Skill used by many Workers.
"""

from typing import List, Optional

from ai_worker.skills.base import BaseSkill, SkillMetadata, SkillRegistry
from ai_worker.tools.base import BaseTool
from ai_worker.tools.web_search import WebSearchTool
from ai_worker.tools.registry import ToolRegistry


@SkillRegistry.register
class SearchSkill(BaseSkill):
    """
    Web search capability.
    
    Provides access to web search with time filtering support.
    """
    
    def __init__(self, tavily_api_key: Optional[str] = None):
        self._tavily_api_key = tavily_api_key
        self._tools: Optional[List[BaseTool]] = None
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="Search",
            description="Search the web for information, news, and answers",
            category="Information",
            emoji="🔍",
            trigger_phrases=[
                "search for",
                "look up",
                "find information about",
                "what is",
                "搜索",
                "查一下",
            ],
        )
    
    def get_tools(self) -> List[BaseTool]:
        if self._tools is None:
            self._tools = []
            
            # Local WebSearchTool
            self._tools.append(WebSearchTool(tavily_api_key=self._tavily_api_key))
            
            # Try to get MCP-based DuckDuckGo if available
            try:
                ddg_tool = ToolRegistry.create_tool("duckduckgo__search")
                self._tools.append(ddg_tool)
            except Exception:
                pass  # MCP not available, use local tool
        
        return self._tools
    
    def get_instructions(self) -> str:
        return """### Search Best Practices
- Use `timelimit='d'` for time-sensitive queries (news, trending topics)
- For site-specific search, use `site:domain.com` in the query
- Prefer specific, focused queries over broad ones
- If results are stale, add "2024" or "today" to the query
"""
