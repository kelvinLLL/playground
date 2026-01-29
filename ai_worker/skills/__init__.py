"""
Skills module for AI Worker.

Skills are modular capability packages that can be loaded by Workers.
Each Skill encapsulates:
- A set of related Tools
- Domain-specific instructions (prompt fragments)
- Best practices for using those tools together

Skills are ATOMIC and REUSABLE - they don't maintain state.
Workers are STATEFUL and orchestrate Skills for complex workflows.
"""

from .base import BaseSkill, SkillRegistry
from .search import SearchSkill
from .browser import BrowserSkill
from .realtime_intel import RealtimeIntelSkill
from .deep_research import DeepResearchSkill
from .local_script import LocalScriptSkill

__all__ = [
    "BaseSkill",
    "SkillRegistry",
    "SearchSkill",
    "BrowserSkill",
    "RealtimeIntelSkill",
    "DeepResearchSkill",
    "LocalScriptSkill",
]
