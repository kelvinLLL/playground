"""
Deep Research Skill - In-depth analysis of web resources.

This skill enables the agent to perform deep analysis on URLs, papers, and repos.
It is PROMPT-DRIVEN: the LLM decides how to approach each resource based on guidance,
not hardcoded if/else rules in Python.

Provides:
- Browser tools (navigate, snapshot)
- PDF reader
- Strategic instructions for deep reading

The LLM is taught to:
1. Identify resource type (paper, repo, article, etc.)
2. Choose appropriate extraction strategy
3. Synthesize findings focusing on user's query
"""

from typing import List, Optional

from ai_worker.skills.base import BaseSkill, SkillMetadata, SkillRegistry
from ai_worker.tools.base import BaseTool
from ai_worker.tools.pdf_reader import PDFReaderTool
from ai_worker.tools.registry import ToolRegistry


@SkillRegistry.register
class DeepResearchSkill(BaseSkill):
    """
    Deep analysis capability for web resources.
    
    Combines browser automation and document reading with
    strategic prompting for thorough analysis.
    """
    
    def __init__(self):
        self._tools: Optional[List[BaseTool]] = None
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="DeepResearch",
            description="Deeply analyze URLs, papers, repos - extract key insights",
            category="Research",
            emoji="🔬",
            trigger_phrases=[
                "analyze this",
                "read this paper",
                "explain this repo",
                "what does this article say",
                "deep dive",
                "详细分析",
                "仔细看看",
            ],
        )
    
    def get_tools(self) -> List[BaseTool]:
        if self._tools is None:
            self._tools = []
            
            # PDF Reader (local)
            self._tools.append(PDFReaderTool())
            
            # Browser tools (MCP)
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
        
        return self._tools
    
    def get_instructions(self) -> str:
        return """### Deep Research Strategy

When asked to deeply analyze a URL or resource, follow this approach:

**1. Identify Resource Type**
- ArXiv/PDF link → Use pdf_reader tool
- GitHub repo → Navigate to README, then snapshot
- Blog/Article → Navigate then snapshot the content
- HuggingFace model → Navigate to model card

**2. ArXiv URL Handling**
If the URL contains "arxiv.org/abs/", convert it to PDF:
- Change `/abs/` to `/pdf/`
- Add `.pdf` extension if missing
- Example: arxiv.org/abs/2401.12345 → arxiv.org/pdf/2401.12345.pdf

**3. Analysis Framework**
After fetching content, structure your analysis:

For **Papers/Research**:
- One-liner: What is this paper about?
- Key Innovation: What's new or different?
- Method: How does it work (high-level)?
- Results: What did they achieve?
- Relevance: Why should the user care?

For **GitHub Repos**:
- Purpose: What problem does it solve?
- Tech Stack: Languages, frameworks
- Usage: How to get started (from README)
- Activity: Recent commits, stars, maintenance status

For **Articles/Blog Posts**:
- Summary: Main argument or announcement
- Key Points: Bullet the important takeaways
- Source Credibility: Who wrote it, when

**4. Focus on User Query**
If the user asks about a specific aspect (e.g., "how does it handle memory?"),
prioritize finding and explaining that specific detail.

**5. Error Handling**
If a page is blocked or PDF fails to load:
- Try the web search tool to find alternative sources
- Inform the user about the limitation
- Offer to search for related content

**6. References & Citations**
Always include a References section at the end of your analysis:
- List all sources consulted (URLs, papers, repos)
- For papers: Include title, authors (if available), and ArXiv/DOI link
- For repos: Include name, owner, and GitHub URL
- For articles: Include title, publication, date, and URL

Format:
```
## References
1. [Paper Title](url) - Authors (Year)
2. [Repo Name](github-url) - Brief description
3. [Article Title](url) - Publication, Date
```
"""
