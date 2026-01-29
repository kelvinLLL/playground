"""
Smart Router Worker - LLM-based intelligent routing.

Uses function calling to decide whether to:
1. Execute a Skill directly (atomic capability)
2. Route to a specialized Worker (complex workflow)
3. Respond directly
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from ai_worker.core.message import (
    MessageType,
    StandardMessage,
    StandardResponse,
)
from ai_worker.llm.base import BaseLLM, Message, ToolDefinition, ToolCall
from ai_worker.llm.openai_client import OpenAIClient
from ai_worker.workers.base import BaseWorker, WorkerConfig
from ai_worker.tools.base import BaseTool

# Skills
from ai_worker.skills.base import BaseSkill, combine_skill_tools, combine_skill_instructions
from ai_worker.skills.search import SearchSkill
from ai_worker.skills.browser import BrowserSkill
from ai_worker.skills.realtime_intel import RealtimeIntelSkill
from ai_worker.skills.deep_research import DeepResearchSkill
from ai_worker.skills.local_script import LocalScriptSkill

logger = logging.getLogger(__name__)

# Retry configuration
LLM_MAX_RETRIES = 3
LLM_RETRY_DELAY = 2.0  # seconds


ROUTER_BASE_PROMPT = """You are Sisyphus, an intelligent AI employee. 
You have access to a suite of Tools (Skills) and Specialized Workers.

## Your Capabilities
1. **Direct Action**: You can perform many tasks directly using your tools (Search, Browser, Analysis).
   - "Search for X" -> Use search tool
   - "Read this link" -> Use browser tool
   - "What's trending" -> Use realtime intel tool
   
2. **Delegation**: For complex, multi-step workflows, delegate to a Specialist.
   - "Generate a daily brief" -> Delegate to DailyBrief Worker
   - "Help me beat Malenia in Elden Ring" -> Delegate to Game Worker
   - "Analyze this PDF and write a report" -> Use your Browser Skill (read_pdf) directly

## Guidelines
- **Prefer Direct Action**: If you can solve it with your tools, do it. Don't delegate trivial tasks.
- **Complex Workflows**: Delegate tasks that require maintaining state or following a strict process.
- **Language**: Respond in the same language as the user (default to Chinese for Chinese queries).
"""


class DefaultWorker(BaseWorker):
    """
    Smart Router Worker - The "Head" of the AI Agent.
    
    It is both a Router and a Capable Agent.
    - Loads common Skills (Search, Browser, etc.)
    - Routes to specialized Workers when necessary
    """

    def __init__(self, llm: BaseLLM, workers: Optional[dict[str, BaseWorker]] = None):
        config = WorkerConfig(
            name="Router",
            description="Intelligent router that uses LLM to decide how to handle requests.",
            system_prompt=ROUTER_BASE_PROMPT,
        )
        super().__init__(config)
        self.llm = llm
        self.workers = workers or {}
        
        # Initialize Skills
        self.skills: List[BaseSkill] = [
            SearchSkill(),
            BrowserSkill(),
            RealtimeIntelSkill(),
            DeepResearchSkill(),
            LocalScriptSkill(),
        ]
        
        # Load tools from skills
        self._tools = {}
        for skill in self.skills:
            for tool in skill.get_tools():
                self._tools[tool.name] = tool
        
        # Build tool definitions for LLM
        self.router_tools = self._build_router_tools()

    def set_workers(self, workers: dict[str, BaseWorker]) -> None:
        """Set available workers for routing."""
        self.workers = workers
        # Re-build tools to ensure worker list is up-to-date
        self.router_tools = self._build_router_tools()

    def _build_router_tools(self) -> List[ToolDefinition]:
        """Combine Skill tools + Routing tools."""
        tools = []
        
        # 1. Add tools from Skills
        for tool in self._tools.values():
            tools.append(ToolDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters
            ))
        
        # 2. Add routing tool with detailed worker descriptions
        worker_names = list(self.workers.keys())
        if worker_names:
            # Build worker descriptions for LLM to understand routing
            worker_descriptions = {
                "daily_brief": "Generate a comprehensive daily intelligence briefing with news, research papers, and tech trends",
                "game": "Help with video game strategies, boss fights, builds, and gaming questions",
                "intel": "Analyze stocks, market data, and investment opportunities",
                "strategy": "Design and backtest quantitative trading strategies",
            }
            
            # Build description with worker capabilities
            worker_info = ", ".join([
                f"{name}: {worker_descriptions.get(name, 'General tasks')}"
                for name in worker_names if name != "default"
            ])
            
            tools.append(ToolDefinition(
                name="call_worker",
                description=f"Delegate to a specialized worker. Available workers: {worker_info}",
                parameters={
                    "type": "object",
                    "properties": {
                        "worker_name": {
                            "type": "string",
                            "enum": [n for n in worker_names if n != "default"],
                            "description": "Name of the specialized worker to delegate to"
                        },
                        "task_description": {
                            "type": "string",
                            "description": "Specific instruction for the worker (in user's language)"
                        }
                    },
                    "required": ["worker_name", "task_description"]
                }
            ))
            
        return tools

    async def process(
        self, 
        message: StandardMessage, 
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        """Process message with Skills + Routing."""
        try:
            return await self._route_with_llm(message, notifier)
        except Exception as e:
            logger.error(f"Router error: {e}")
            return StandardResponse(
                content=f"Sorry, I encountered an error: {str(e)}",
                message_type=MessageType.TEXT,
            )

    async def _route_with_llm(
        self,
        message: StandardMessage,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        """Use LLM to route or execute."""
        
        # 1. Build System Prompt with Skill Instructions
        skill_instructions = combine_skill_instructions(self.skills)
        system_content = f"{self.system_prompt}\n\n## Skill Instructions\n{skill_instructions}"
        
        user_context = message.metadata.get("user_context", "") if message.metadata else ""
        if user_context:
            system_content += f"\n\n## User Context\n{user_context}"
        
        # 2. Inject Context Links (for reference resolution)
        context_links = message.metadata.get("context_links", []) if message.metadata else []
        if context_links:
            links_section = "\n\n## Active Context (Recent Links)\n"
            links_section += "The user may refer to these items by number or description:\n"
            for i, link in enumerate(context_links[:15], 1):  # Limit to 15
                title = link.get("title", "Untitled")[:60]
                url = link.get("url", "")
                links_section += f"{i}. [{title}]({url})\n"
            system_content += links_section

        messages = [Message(role="system", content=system_content)]
        
        # 3. Add History
        conversation_history = message.metadata.get("conversation_history", []) if message.metadata else []
        for msg in conversation_history[:-1]:
            messages.append(Message(role=msg["role"], content=msg["content"]))
        
        messages.append(Message(role="user", content=message.content))

        # 4. Call LLM with retry logic
        if not isinstance(self.llm, OpenAIClient):
            logger.warning("LLM does not support function calling, falling back to direct response")
            response = await self.llm.chat(messages)
            return StandardResponse(content=response.content, message_type=MessageType.TEXT)

        # Call LLM with retries for connection errors
        llm_response = None
        last_error = None
        for attempt in range(LLM_MAX_RETRIES):
            try:
                llm_response = await self.llm.chat_with_tools(
                    messages=messages,
                    tools=self.router_tools,
                    tool_choice="auto"
                )
                break  # Success
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                # Only retry on connection/network errors
                if any(keyword in error_str for keyword in ["connection", "timeout", "network", "refused"]):
                    logger.warning(f"LLM connection error (attempt {attempt + 1}/{LLM_MAX_RETRIES}): {e}")
                    if attempt < LLM_MAX_RETRIES - 1:
                        await asyncio.sleep(LLM_RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    # Non-retryable error, raise immediately
                    raise
        
        if llm_response is None:
            logger.error(f"LLM call failed after {LLM_MAX_RETRIES} retries: {last_error}")
            raise last_error  # type: ignore

        if not llm_response.tool_calls:
            return StandardResponse(
                content=llm_response.content or "I'm not sure how to help with that.",
                message_type=MessageType.TEXT
            )

        # 4. Execute Tool
        # Handle the first tool call
        tool_call = llm_response.tool_calls[0]
        
        if tool_call.name == "call_worker":
            return await self._execute_worker_call(tool_call, message, notifier)
        else:
            return await self._execute_local_tool(tool_call, messages, notifier)

    async def _execute_worker_call(
        self,
        tool_call: ToolCall,
        original_message: StandardMessage,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        """Delegate to another worker."""
        worker_name = tool_call.arguments.get("worker_name")
        task_desc = tool_call.arguments.get("task_description", original_message.content)
        
        worker = self.workers.get(worker_name)
        if not worker:
            return StandardResponse(content=f"Worker '{worker_name}' not available.")
        
        if notifier:
            await notifier(f"🔄 Delegating to **{worker_name}**...")
        
        logger.info(f"Delegating to worker: {worker_name}")
        
        routed_message = StandardMessage(
            id=original_message.id,
            content=task_desc,
            message_type=original_message.message_type,
            platform=original_message.platform,
            author=original_message.author,
            channel=original_message.channel,
            timestamp=original_message.timestamp,
            raw_data=original_message.raw_data,
            metadata=original_message.metadata,
            attachments=original_message.attachments,
        )
        
        return await worker.process(routed_message, notifier=notifier)

    async def _execute_local_tool(
        self,
        tool_call: ToolCall,
        history: List[Message],
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        """Execute a local tool (from a Skill) and get final answer."""
        tool_name = tool_call.name
        tool_args = tool_call.arguments
        
        tool = self._tools.get(tool_name)
        if not tool:
            return StandardResponse(content=f"Error: Tool '{tool_name}' not found.")
        
        if notifier:
            await notifier(f"🔧 Using tool: **{tool_name}**...")
            
        logger.info(f"Executing tool: {tool_name} args={tool_args}")
        
        try:
            result = await tool.execute(**tool_args)
            tool_output = str(result.data) if result.success else f"Error: {result.error}"
            
            # Feed result back to LLM for final answer
            history.append(Message(
                role="assistant",
                content=None,
                tool_calls=[tool_call]
            ))
            history.append(Message(
                role="tool",
                content=tool_output,
                tool_call_id=tool_call.id
            ))
            
            final_response = await self.llm.chat_with_tools(
                messages=history,
                tools=self.router_tools,
                tool_choice="none" # Force text response
            )
            
            return StandardResponse(
                content=final_response.content,
                message_type=MessageType.TEXT
            )
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return StandardResponse(content=f"Tool execution failed: {str(e)}")
