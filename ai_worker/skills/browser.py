"""
Browser Skill - Web browsing and content extraction.

Provides capabilities for:
- Navigating to URLs
- Taking snapshots of page content
- Reading PDF documents
- Extracting structured data from pages

Requires Playwright MCP server for browser operations.
"""

from typing import List, Optional

from ai_worker.skills.base import BaseSkill, SkillMetadata, SkillRegistry
from ai_worker.tools.base import BaseTool
from ai_worker.tools.pdf_reader import PDFReaderTool
from ai_worker.tools.registry import ToolRegistry


@SkillRegistry.register
class BrowserSkill(BaseSkill):
    """
    Web browsing and document reading capability.
    
    Enables deep content extraction from URLs and documents.
    """
    
    def __init__(self):
        self._tools: Optional[List[BaseTool]] = None
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="Browser",
            description="Navigate websites, read pages, and extract content from PDFs",
            category="Research",
            emoji="🌐",
            trigger_phrases=[
                "open this link",
                "read this page",
                "what does this article say",
                "summarize this PDF",
                "打开链接",
                "看看这个网页",
            ],
        )
    
    def get_tools(self) -> List[BaseTool]:
        if self._tools is None:
            self._tools = []
            
            # PDF Reader (local)
            self._tools.append(PDFReaderTool())
            
            # Playwright browser tools (MCP)
            try:
                nav_tool = ToolRegistry.create_tool("playwright__browser_navigate")
                self._tools.append(nav_tool)
            except Exception:
                pass
            
            try:
                snapshot_tool = ToolRegistry.create_tool("playwright__browser_snapshot")
                self._tools.append(snapshot_tool)
            except Exception:
                pass
            
            try:
                click_tool = ToolRegistry.create_tool("playwright__browser_click")
                self._tools.append(click_tool)
            except Exception:
                pass
        
        return self._tools
    
    def get_instructions(self) -> str:
        return """### Browser Best Practices
- Always use `browser_navigate` before `browser_snapshot` to load a page
- For dynamic pages, wait a moment after navigation before taking snapshot
- Use `browser_snapshot` to get page content as readable text
- For PDFs, use the `pdf_reader` tool directly with the file path or URL
- Extract key information and summarize - don't dump raw HTML to user
"""
