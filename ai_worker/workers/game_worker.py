"""
Game Guide Worker implementation.

Specialized in generating concise, high-quality game guides and walkthroughs.
"""

import logging
from typing import Any, Callable, Optional

from ai_worker.core.message import (
    MessageType,
    StandardMessage,
    StandardResponse,
)
from ai_worker.llm.base import BaseLLM, Message
from ai_worker.workers.base import BaseWorker, WorkerConfig
from ai_worker.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class GameWorker(BaseWorker):
    """
    Game Strategy Guide Specialist.

    Responsible for creating compact, actionable game guides.
    """

    def __init__(self, llm: BaseLLM, tavily_api_key: Optional[str] = None):
        config = WorkerConfig(
            name="GameGuide",
            description="Expert Game Guide writer. Creates compact, actionable walkthroughs.",
            system_prompt=(
                "You are an Elite Game Guide Editor (IGN/Fandom/Wiki veteran). "
                "Your goal is to write 'Small but Precise' (小而精) game guides. "
                "Output Guidelines:\n"
                "1. **Structure**: Use clear headers (e.g., 'Loadout', 'Mechanics', 'Phase 1', 'Tips').\n"
                "2. **Concise**: Bullet points over paragraphs. No fluff.\n"
                "3. **Actionable**: Tell the user exactly what to do (e.g., 'Dodge left when he raises sword').\n"
                "4. **Data-driven**: Include specific stats, weak points, or drop rates if found.\n"
                "5. **Formatting**: Use bolding for key items/enemies.\n"
                "If the user asks about a game, search for the latest meta/strategies and synthesize a guide."
            ),
            tools=["web_search"],
        )
        super().__init__(config)
        self.llm = llm

        # Use registry - GameWorker reuses web_search tool but as 'game_guide' logic
        # Note: In ToolRegistry.create_tool, we map 'game_guide' logic if needed,
        # but here the config says tools=["web_search"].
        # So we should request "web_search" from registry.
        
        tool_config = {}
        if tavily_api_key:
            tool_config["tavily_api_key"] = tavily_api_key
            
        tool = ToolRegistry.create_tool("web_search", config=tool_config)
        self._tools[tool.name] = tool

    async def process(
        self,
        message: StandardMessage,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        try:
            query = message.content
            
            # Enhance query for better game results
            search_query = f"{query} guide walkthrough reddit wiki"
            
            if notifier:
                await notifier(f"🎮 Searching game databases for: **{query}**...")

            tool = self._tools["web_search"]
            # Get more results for games to cover different wikis
            result = await tool.execute(query=search_query, max_results=6)

            if result.success and result.data:
                if notifier:
                    await notifier("⚔️ Compiling battle strategy...")

                analysis_prompt = (
                    f"User Request: {query}\n\n"
                    f"Search Results:\n{result.data}\n\n"
                    "Write a 'Small and Precise' Game Guide based on these results. "
                    "Focus on the solution, strategy, and key tips. "
                    "Ignore irrelevant search SEO text."
                )

                response = await self.llm.complete(analysis_prompt, max_tokens=1500)
                response_text = response.content

            else:
                # Fallback if search fails
                response_text = (
                    f"Couldn't find specific guides for '{query}'. "
                    "Try specifying the game name or checking if it's released yet."
                )

            # Update memory
            self.add_to_memory("user", message.content)
            self.add_to_memory("assistant", response_text)

            return StandardResponse(
                content=response_text,
                message_type=MessageType.TEXT
            )

        except Exception as e:
            logger.error(f"Error in GameWorker: {e}")
            return StandardResponse(content=f"Game Guide Error: {str(e)}")
