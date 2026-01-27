"""
Web Search Worker implementation.

Specialized in searching the web and providing real-time information.
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


class WebSearchWorker(BaseWorker):
    """
    Web Search Specialist.

    Responsible for finding real-time information from the web.
    """

    def __init__(self, llm: BaseLLM, tavily_api_key: Optional[str] = None):
        config = WorkerConfig(
            name="WebSearcher",
            description="Web Search Specialist. Finds real-time information from the internet.",
            system_prompt=(
                "You are a Web Research Assistant. "
                "Your role is to search the web and provide accurate, up-to-date information. "
                "When presenting search results:\n"
                "1. Synthesize information from multiple sources when possible\n"
                "2. Cite sources with URLs\n"
                "3. Distinguish between facts and opinions\n"
                "4. Highlight key findings clearly\n"
                "5. If results are insufficient, suggest alternative search queries\n"
                "Be concise but thorough. Always prioritize accuracy over speed."
            ),
            tools=["web_search"],
        )
        super().__init__(config)
        self.llm = llm

        # Use registry to create tool with configuration
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
            query = self._extract_search_query(message.content)

            if notifier:
                await notifier(f"Searching the web for: **{query}**...")

            tool = self._tools["web_search"]
            result = await tool.execute(query=query, max_results=5)

            if result.success and result.data:
                search_results = result.data

                if notifier:
                    await notifier("Analyzing search results...")

                analysis_prompt = (
                    f"User asked: {message.content}\n\n"
                    f"Here are the web search results:\n\n{search_results}\n\n"
                    "Please provide a helpful response based on these search results. "
                    "Synthesize the information and cite sources where appropriate."
                )

                response = await self.llm.complete(analysis_prompt, max_tokens=1500)
                response_text = response.content

            else:
                fallback_msg = (
                    f"Web search didn't return useful results for '{query}'. "
                    f"Error: {result.error or 'No results found'}"
                )

                messages = [Message(role="system", content=self.system_prompt)]
                messages.append(Message(
                    role="user",
                    content=f"{message.content}\n\n(Note: {fallback_msg})"
                ))
                response = await self.llm.chat(messages)
                response_text = response.content

            self.add_to_memory("user", message.content)
            self.add_to_memory("assistant", response_text)

            return StandardResponse(
                content=response_text,
                message_type=MessageType.TEXT
            )

        except Exception as e:
            logger.error(f"Error in WebSearchWorker: {e}")
            return StandardResponse(content=f"Search error: {str(e)}")

    def _extract_search_query(self, content: str) -> str:
        """Extract the actual search query from user message."""
        content_lower = content.lower()

        prefixes_to_remove = [
            "search for", "search", "look up", "lookup", "find",
            "google", "what is", "what are", "who is", "who are",
            "tell me about", "information on", "info on",
        ]

        query = content
        for prefix in prefixes_to_remove:
            if content_lower.startswith(prefix):
                query = content[len(prefix):].strip()
                break

        return query.strip() if query else content
