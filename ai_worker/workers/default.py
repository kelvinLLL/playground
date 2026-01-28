"""
Smart Router Worker - LLM-based intelligent routing.

Uses function calling to decide which worker/tool to invoke.
"""

import logging
from typing import Any, Callable, Optional

from ai_worker.core.message import (
    MessageType,
    StandardMessage,
    StandardResponse,
)
from ai_worker.llm.base import BaseLLM, Message, ToolDefinition, ToolCall
from ai_worker.llm.openai_client import OpenAIClient
from ai_worker.workers.base import BaseWorker, WorkerConfig
from ai_worker.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


ROUTER_SYSTEM_PROMPT = """You are an intelligent AI assistant router. You analyze user requests and decide how to handle them.

You have access to the following capabilities:

## Workers (Sub-agents)
- daily_brief: Generate daily intelligence reports with AI/tech news, GitHub trending, ArXiv papers
- web_search: Search the web for current information using Tavily or DuckDuckGo
- game: Game guides, walkthroughs, boss strategies, builds
- research: Analyze PDFs, papers, documents (especially from ArXiv)
- intel: Fetch market data and financial information
- strategy: Run backtests and trading strategy analysis

## MCP Servers (Direct tools)
- self_hosted: web_search, read_pdf, fetch_market_data, run_backtest
- filesystem: Read/write files in reports directory
- playwright: Browser automation (navigate, click, screenshot)
- duckduckgo: Free web search
- brave_search: Brave search engine

## How to decide:
1. If the user asks for daily brief/news/summary → call worker "daily_brief"
2. If the user asks to search something → call worker "web_search" OR tool "duckduckgo__search"
3. If the user asks about game guides/strategies → call worker "game"
4. If the user sends PDF/ArXiv link → call worker "research"
5. If the user asks about stocks/market data → call worker "intel"
6. If the user asks for backtest → call worker "strategy"
7. For complex multi-step tasks → call appropriate workers in sequence
8. For simple questions → respond directly without tools

Always prefer workers for complex tasks. Use MCP tools directly for simple operations.
Respond in the user's language (Chinese if they use Chinese).
"""


def get_router_tools() -> list[ToolDefinition]:
    """Define tools for the router LLM."""
    return [
        ToolDefinition(
            name="call_worker",
            description="Call a specialized worker to handle the task",
            parameters={
                "type": "object",
                "properties": {
                    "worker_name": {
                        "type": "string",
                        "enum": ["daily_brief", "web_search", "game", "research", "intel", "strategy"],
                        "description": "Name of the worker to call"
                    },
                    "task_description": {
                        "type": "string",
                        "description": "Description of what the worker should do"
                    }
                },
                "required": ["worker_name", "task_description"]
            }
        ),
        ToolDefinition(
            name="call_mcp_tool",
            description="Call an MCP tool directly for simple operations",
            parameters={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Full MCP tool name like 'duckduckgo__search' or 'playwright__browser_navigate'"
                    },
                    "arguments": {
                        "type": "object",
                        "description": "Arguments to pass to the tool"
                    }
                },
                "required": ["tool_name", "arguments"]
            }
        ),
        ToolDefinition(
            name="respond_directly",
            description="Respond directly to the user without calling other workers or tools",
            parameters={
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "Direct response to the user"
                    }
                },
                "required": ["response"]
            }
        )
    ]


class DefaultWorker(BaseWorker):
    """
    Smart Router Worker - uses LLM function calling to route requests.
    
    This is the main entry point that decides which worker or tool to invoke
    based on user intent, replacing hardcoded keyword matching.
    """

    def __init__(self, llm: BaseLLM, workers: Optional[dict[str, BaseWorker]] = None):
        config = WorkerConfig(
            name="Router",
            description="Intelligent router that uses LLM to decide how to handle requests.",
            system_prompt=ROUTER_SYSTEM_PROMPT,
        )
        super().__init__(config)
        self.llm = llm
        self.workers = workers or {}
        self.router_tools = get_router_tools()

    def set_workers(self, workers: dict[str, BaseWorker]) -> None:
        """Set available workers for routing."""
        self.workers = workers

    async def process(
        self, 
        message: StandardMessage, 
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        """
        Process a message using LLM-based routing.

        The LLM decides whether to:
        1. Call a specialized worker
        2. Call an MCP tool directly
        3. Respond directly
        """
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
        """Use LLM with function calling to route the request."""
        
        system_content = self.system_prompt
        user_context = message.metadata.get("user_context", "") if message.metadata else ""
        if user_context:
            system_content += f"\n\nContext about this user:\n{user_context}"

        messages = [Message(role="system", content=system_content)]
        
        conversation_history = message.metadata.get("conversation_history", []) if message.metadata else []
        for msg in conversation_history[:-1]:
            messages.append(Message(role=msg["role"], content=msg["content"]))
        
        messages.append(Message(role="user", content=message.content))

        if not isinstance(self.llm, OpenAIClient):
            logger.warning("LLM does not support function calling, falling back to direct response")
            response = await self.llm.chat(messages)
            return StandardResponse(content=response.content, message_type=MessageType.TEXT)

        llm_response = await self.llm.chat_with_tools(
            messages=messages,
            tools=self.router_tools,
            tool_choice="auto"
        )

        if not llm_response.tool_calls:
            return StandardResponse(
                content=llm_response.content or "I'm not sure how to help with that.",
                message_type=MessageType.TEXT
            )

        tool_call = llm_response.tool_calls[0]
        return await self._execute_tool_call(tool_call, message, notifier)

    async def _execute_tool_call(
        self,
        tool_call: ToolCall,
        original_message: StandardMessage,
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        """Execute the tool call decided by the LLM."""
        
        if tool_call.name == "respond_directly":
            return StandardResponse(
                content=tool_call.arguments.get("response", ""),
                message_type=MessageType.TEXT
            )

        if tool_call.name == "call_worker":
            worker_name = tool_call.arguments.get("worker_name")
            task_desc = tool_call.arguments.get("task_description", original_message.content)
            
            worker = self.workers.get(worker_name)
            if not worker:
                return StandardResponse(
                    content=f"Worker '{worker_name}' not available.",
                    message_type=MessageType.TEXT
                )
            
            if notifier:
                await notifier(f"🔄 Routing to **{worker_name}** worker...")
            
            logger.info(f"Routing to worker: {worker_name}")
            
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

        if tool_call.name == "call_mcp_tool":
            tool_name = tool_call.arguments.get("tool_name")
            tool_args = tool_call.arguments.get("arguments", {})
            
            if notifier:
                await notifier(f"🔧 Calling MCP tool: **{tool_name}**...")
            
            logger.info(f"Calling MCP tool: {tool_name} with args: {tool_args}")
            
            try:
                tool = ToolRegistry.create_tool(tool_name)
                result = await tool.execute(**tool_args)
                
                if result.success:
                    return StandardResponse(
                        content=str(result.data),
                        message_type=MessageType.TEXT
                    )
                else:
                    return StandardResponse(
                        content=f"Tool error: {result.error}",
                        message_type=MessageType.TEXT
                    )
            except Exception as e:
                logger.error(f"MCP tool call failed: {e}")
                return StandardResponse(
                    content=f"Failed to call tool '{tool_name}': {str(e)}",
                    message_type=MessageType.TEXT
                )

        return StandardResponse(
            content=f"Unknown action: {tool_call.name}",
            message_type=MessageType.TEXT
        )
