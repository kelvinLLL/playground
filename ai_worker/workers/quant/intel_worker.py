"""
Intel Worker implementation.

Specialized in market data gathering and analysis.
"""

import logging

from ai_worker.core.message import (
    MessageType,
    StandardMessage,
    StandardResponse,
)
from ai_worker.llm.base import BaseLLM, Message
from ai_worker.workers.base import BaseWorker, WorkerConfig
from ai_worker.tools import MarketDataTool

from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class IntelWorker(BaseWorker):
    """
    Quant Intelligence Analyst.
    
    Responsible for fetching market data and providing market insights.
    """

    def __init__(self, llm: BaseLLM):
        config = WorkerConfig(
            name="IntelAnalyst",
            description="Market Data Specialist. Fetches and analyzes market data.",
            system_prompt=(
                "You are a Quantitative Intelligence Analyst. "
                "Your role is to fetch accurate market data using available tools. "
                "When asked for data, use the 'fetch_market_data' tool. "
                "Always confirm when data is successfully fetched."
            ),
            tools=["fetch_market_data"],
        )
        super().__init__(config)
        self.llm = llm
        
        # Register tools
        self.register_tool(MarketDataTool())

    async def process(
        self, 
        message: StandardMessage, 
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        try:
            # 1. Prepare conversation
            messages = [Message(role="system", content=self.system_prompt)]
            messages.extend([Message(role=m["role"], content=m["content"]) for m in self.get_memory(5)])
            messages.append(Message(role="user", content=message.content))

            # 2. First LLM call - decision making (Tool use check)
            # In a real implementation, we would use proper function calling API
            # For this MVP, we'll use a simplified tool use logic or direct tool binding
            # Let's try to use OpenAI's tool calling if available in our client
            
            # Since our BaseLLM doesn't support tools yet, we'll use a hack:
            # We'll ask the LLM if it wants to use a tool.
            
            # TODO: Upgrade BaseLLM to support function calling natively
            
            # For now, let's look for keywords or simple intent parsing
            # This is a temporary simplification for Phase 4 MVP
            content = message.content.lower()
            
            if "fetch" in content or "download" in content or "get data" in content:
                if notifier:
                    await notifier("🔍 analyzing request...")
                
                # Extract parameters (naive extraction)
                # In production, use LLM to extract JSON args
                
                extraction_prompt = (
                    f"Extract stock symbol, start_date, and end_date from: '{message.content}'. "
                    "Return strictly in format: SYMBOL|START_DATE|END_DATE. "
                    "Example: AAPL|2023-01-01|2023-12-31. "
                    "If missing, guess reasonable defaults (last year for dates)."
                )
                
                extraction = await self.llm.chat_simple(extraction_prompt)
                try:
                    parts = extraction.strip().split("|")
                    symbol = parts[0].strip()
                    start_date = parts[1].strip()
                    end_date = parts[2].strip()
                    
                    # Execute tool
                    if notifier:
                        await notifier(f"⬇️ Fetching data for {symbol} ({start_date} to {end_date})...")
                    
                    tool = self._tools["fetch_market_data"]
                    result = await tool.execute(symbol=symbol, start_date=start_date, end_date=end_date)
                    
                    response_text = f"Tool Execution Result: {result.data}"
                    if result.error:
                        response_text += f"\nError: {result.error}"
                        
                except Exception as e:
                    response_text = f"Failed to parse parameters: {extraction}. Error: {e}"
            else:
                # Normal chat
                response = await self.llm.chat(messages)
                response_text = response.content

            # Update memory
            self.add_to_memory("user", message.content)
            self.add_to_memory("assistant", response_text)

            return StandardResponse(
                content=response_text,
                message_type=MessageType.TEXT
            )

        except Exception as e:
            logger.error(f"Error in IntelWorker: {e}")
            return StandardResponse(content=f"Error: {str(e)}")
