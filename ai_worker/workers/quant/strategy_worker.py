"""
Strategy Worker implementation.

Specialized in running backtests and strategy analysis.
"""

import logging

from ai_worker.core.message import (
    MessageType,
    StandardMessage,
    StandardResponse,
)
from ai_worker.llm.base import BaseLLM, Message
from ai_worker.workers.base import BaseWorker, WorkerConfig
from ai_worker.tools.registry import ToolRegistry

from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class StrategyWorker(BaseWorker):
    """
    Quant Strategy Researcher.
    
    Responsible for running backtests and evaluating strategies.
    """

    def __init__(self, llm: BaseLLM):
        config = WorkerConfig(
            name="StrategyDev",
            description="Strategy Specialist. Runs backtests and evaluates performance.",
            system_prompt=(
                "You are a Quantitative Strategy Researcher. "
                "Your role is to run backtests on strategies and explain the results. "
                "You have access to the 'run_backtest' tool. "
                "When asked to test a strategy, always use the tool."
            ),
            tools=["run_backtest"],
        )
        super().__init__(config)
        self.llm = llm
        
        # Register tools
        tool = ToolRegistry.create_tool("run_backtest")
        self.register_tool(tool, as_name="run_backtest")

    async def process(
        self, 
        message: StandardMessage, 
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        try:
            # Similar simplified tool logic as IntelWorker
            content = message.content.lower()
            
            if "backtest" in content or "test strategy" in content or "run strategy" in content:
                if notifier:
                    await notifier("🔍 Analyzing backtest request...")
                
                # Naive parameter extraction
                extraction_prompt = (
                    f"Extract stock symbol from: '{message.content}'. "
                    "Return strictly the SYMBOL only. "
                    "Example: AAPL"
                )
                
                symbol = await self.llm.chat_simple(extraction_prompt)
                symbol = symbol.strip().replace("Symbol:", "").strip()
                
                # Execute tool
                if notifier:
                    await notifier(f"📈 Running backtest for {symbol} (this may take a moment)...")
                
                tool = self._tools["run_backtest"]
                result = await tool.execute(symbol=symbol)
                
                if result.success:
                    if notifier:
                        await notifier("📊 Analyzing results...")
                    
                    # Summarize the result with LLM
                    summary_prompt = (
                        f"Here is the backtest result for {symbol}:\n{result.data}\n\n"
                        "Please provide a concise summary of the performance (Total Return, Sharpe Ratio, Max Drawdown). "
                        "Do not output the raw data."
                    )
                    summary = await self.llm.chat_simple(summary_prompt)
                    response_text = f"**Backtest Results for {symbol}**\n\n{summary}\n\n*Raw logs available in system*"
                else:
                    response_text = f"Backtest failed: {result.error}"
                    
            else:
                messages = [Message(role="system", content=self.system_prompt)]
                messages.extend([Message(role=m["role"], content=m["content"]) for m in self.get_memory(5)])
                messages.append(Message(role="user", content=message.content))
                
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
            logger.error(f"Error in StrategyWorker: {e}")
            return StandardResponse(content=f"Error: {str(e)}")
