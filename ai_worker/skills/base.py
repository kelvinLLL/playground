"""
Base Skill class and Skill Registry.

A Skill is a modular capability package containing:
- Tools: Atomic operations the LLM can invoke
- Instructions: Domain-specific guidance for using the tools
- Metadata: Name, description, category for organization

Skills are designed to be:
- ATOMIC: No internal state, pure capability
- COMPOSABLE: Multiple Skills can be loaded together
- REUSABLE: Same Skill used by different Workers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from ai_worker.tools.base import BaseTool


@dataclass
class SkillMetadata:
    """Metadata describing a Skill for display and routing."""
    
    name: str
    description: str
    category: str  # e.g., "Information", "Research", "Development"
    emoji: str = "🔧"
    version: str = "1.0.0"
    
    # When should this skill be activated?
    # Used by Router to match user intent
    trigger_phrases: List[str] = field(default_factory=list)


class BaseSkill(ABC):
    """
    Abstract base class for all Skills.
    
    A Skill bundles related Tools with domain-specific instructions.
    Workers load Skills to gain capabilities without managing individual tools.
    
    Example:
        class SearchSkill(BaseSkill):
            def get_tools(self) -> List[BaseTool]:
                return [DuckDuckGoTool(), TavilyTool()]
            
            def get_instructions(self) -> str:
                return "When searching, prefer DuckDuckGo for general queries..."
    """
    
    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """Return metadata describing this skill."""
        pass
    
    @abstractmethod
    def get_tools(self) -> List[BaseTool]:
        """
        Return the list of Tool instances this Skill provides.
        
        These tools will be made available to the LLM for function calling.
        """
        pass
    
    def get_instructions(self) -> str:
        """
        Return domain-specific instructions for using this Skill's tools.
        
        These instructions are appended to the system prompt when the Skill
        is loaded. Override to provide tool-specific guidance.
        
        Returns:
            Instruction string (can be empty)
        """
        return ""
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get OpenAI function calling schemas for all tools in this Skill.
        
        Returns:
            List of function schemas
        """
        return [tool.to_function_schema() for tool in self.get_tools()]
    
    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """
        Find a tool by name.
        
        Args:
            name: Tool name to find
            
        Returns:
            Tool instance or None
        """
        for tool in self.get_tools():
            if tool.name == name:
                return tool
        return None
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.metadata.name})>"


class SkillRegistry:
    """
    Registry for discovering and loading Skills.
    
    Provides:
    - Registration of Skill classes
    - Lookup by name or category
    - Bulk loading for Workers
    """
    
    _skills: Dict[str, Type[BaseSkill]] = {}
    
    @classmethod
    def register(cls, skill_class: Type[BaseSkill]) -> Type[BaseSkill]:
        """
        Register a Skill class.
        
        Can be used as a decorator:
            @SkillRegistry.register
            class MySkill(BaseSkill):
                ...
        """
        # Create temporary instance to get metadata
        instance = skill_class()
        name = instance.metadata.name
        cls._skills[name] = skill_class
        return skill_class
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseSkill]:
        """
        Get a Skill instance by name.
        
        Args:
            name: Registered skill name
            
        Returns:
            Skill instance or None
        """
        skill_class = cls._skills.get(name)
        if skill_class:
            return skill_class()
        return None
    
    @classmethod
    def list_skills(cls) -> List[SkillMetadata]:
        """
        List all registered Skills with their metadata.
        
        Returns:
            List of SkillMetadata
        """
        result = []
        for skill_class in cls._skills.values():
            instance = skill_class()
            result.append(instance.metadata)
        return result
    
    @classmethod
    def get_by_category(cls, category: str) -> List[BaseSkill]:
        """
        Get all Skills in a category.
        
        Args:
            category: Category name (e.g., "Information", "Research")
            
        Returns:
            List of Skill instances
        """
        result = []
        for skill_class in cls._skills.values():
            instance = skill_class()
            if instance.metadata.category == category:
                result.append(instance)
        return result
    
    @classmethod
    def load_multiple(cls, names: List[str]) -> List[BaseSkill]:
        """
        Load multiple Skills by name.
        
        Args:
            names: List of skill names
            
        Returns:
            List of Skill instances (skips unknown names)
        """
        result = []
        for name in names:
            skill = cls.get(name)
            if skill:
                result.append(skill)
        return result
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered skills (for testing)."""
        cls._skills.clear()


def combine_skill_tools(skills: List[BaseSkill]) -> List[BaseTool]:
    """
    Combine tools from multiple Skills, avoiding duplicates.
    
    Args:
        skills: List of Skill instances
        
    Returns:
        Deduplicated list of Tools
    """
    seen_names = set()
    tools = []
    
    for skill in skills:
        for tool in skill.get_tools():
            if tool.name not in seen_names:
                seen_names.add(tool.name)
                tools.append(tool)
    
    return tools


def combine_skill_instructions(skills: List[BaseSkill]) -> str:
    """
    Combine instructions from multiple Skills.
    
    Args:
        skills: List of Skill instances
        
    Returns:
        Combined instruction string
    """
    instructions = []
    
    for skill in skills:
        inst = skill.get_instructions()
        if inst:
            instructions.append(f"## {skill.metadata.name}\n{inst}")
    
    return "\n\n".join(instructions)
