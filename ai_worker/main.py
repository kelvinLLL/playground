"""
AI Worker Main Entry Point.

This module provides the main entry point for running AI Worker
with one or more platform adapters.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from ai_worker.config import get_settings
from ai_worker.adapters.discord_adapter import DiscordAdapter
from ai_worker.core.message import StandardMessage, StandardResponse
from ai_worker.llm.openai_client import OpenAIClient
# Import tools to trigger registration
import ai_worker.tools  # noqa: F401
from ai_worker.workers.default import DefaultWorker
from ai_worker.workers.quant.intel_worker import IntelWorker
from ai_worker.workers.quant.strategy_worker import StrategyWorker
from ai_worker.workers.research_worker import ResearchWorker
from ai_worker.workers.web_search_worker import WebSearchWorker
from ai_worker.workers.game_worker import GameWorker
from ai_worker.memory import ConversationMemory, PersistentMemory
from ai_worker.mcp_client import MCPClientManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ai_worker.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


class AIWorkerApp:
    """
    Main application class for AI Worker.

    Manages adapters, workers, and message routing.
    """

    def __init__(self):
        """Initialize the AI Worker application."""
        self.settings = get_settings()
        self.adapters: list = []
        self._shutdown_event = asyncio.Event()
        
        # Memory systems
        self.conversation_memory = ConversationMemory(
            max_messages_per_conversation=20,
            max_age_seconds=3600,
        )
        self.persistent_memory = PersistentMemory()
        
        # MCP Client Manager
        self.mcp_client_manager = MCPClientManager()
        
        # Workers map
        self.workers = {}
        self.default_worker = None

    def setup_workers(self) -> None:
        """Set up all AI workers."""
        if not self.settings.openai.api_key:
            logger.warning("OpenAI API key missing! Workers will be disabled.")
            return

        llm = OpenAIClient(self.settings.openai)
        
        # Initialize workers
        self.default_worker = DefaultWorker(llm)
        intel_worker = IntelWorker(llm)
        strategy_worker = StrategyWorker(llm)
        research_worker = ResearchWorker(llm)
        web_search_worker = WebSearchWorker(
            llm,
            tavily_api_key=self.settings.search.tavily_api_key or None
        )
        game_worker = GameWorker(
            llm,
            tavily_api_key=self.settings.search.tavily_api_key or None
        )
        
        self.workers = {
            "default": self.default_worker,
            "intel": intel_worker,
            "strategy": strategy_worker,
            "research": research_worker,
            "web_search": web_search_worker,
            "game": game_worker,
        }
        
        logger.info(f"Initialized workers: {list(self.workers.keys())}")

    async def handle_message(self, message: StandardMessage) -> None:
        """
        Handle an incoming message from any adapter.

        Args:
            message: Incoming standardized message
        """
        logger.info(
            f"[{message.platform.value}] {message.author.name}: {message.content}"
        )

        if not message.content or message.content.startswith("!"):
            return

        # Find the adapter for this platform first
        current_adapter = None
        for adapter in self.adapters:
            if adapter.name.lower() == message.platform.value:
                current_adapter = adapter
                break
        
        if not current_adapter:
            logger.error(f"No adapter found for platform {message.platform}")
            return

        # Define progress notifier
        async def progress_notifier(text: str):
            # Create a temporary response for status update
            response = StandardResponse(content=text)
            # Try to reply (which might just send a new message)
            await current_adapter.reply(message, response)

        # --- ROUTING LOGIC ---
        content_lower = message.content.lower()
        target_worker = self.default_worker
        
        # 1. Priority: Attachments or PDF URLs -> ResearchWorker
        has_pdf = False
        if message.attachments:
            for att in message.attachments:
                if att.filename.lower().endswith(".pdf"):
                    has_pdf = True
                    break
        
        if has_pdf or ("http" in content_lower and ".pdf" in content_lower) or ("arxiv.org/abs/" in content_lower):
            target_worker = self.workers["research"]
            logger.info("Routing to ResearchWorker (PDF/Arxiv detected)")
        
        # 2. Explicit routing by keyword
        elif "fetch" in content_lower or "data" in content_lower:
            target_worker = self.workers["intel"]
            logger.info("Routing to IntelWorker")
        elif "backtest" in content_lower or "strategy" in content_lower:
            target_worker = self.workers["strategy"]
            logger.info("Routing to StrategyWorker")
        elif "paper" in content_lower or "research" in content_lower or "summarize" in content_lower:
            target_worker = self.workers["research"]
            logger.info("Routing to ResearchWorker (Intent detected)")
        
        # 3. Game Strategy routing
        elif any(kw in content_lower for kw in [
            "guide", "walkthrough", "build", "boss", "level", 
            "zelda", "mario", "elden ring", "pokemon", "game",
            "攻略", "怎么打", "通关"
        ]):
            target_worker = self.workers["game"]
            logger.info("Routing to GameWorker")
            
        # 4. Web search routing
        elif any(kw in content_lower for kw in [
            "search", "look up", "lookup", "find", "google",
            "what is", "who is", "latest", "news", "current"
        ]):
            target_worker = self.workers["web_search"]
            logger.info("Routing to WebSearchWorker")
        
        if target_worker:
            # Store user message in conversation memory
            user_id = message.author.id
            channel_id = message.channel.id
            self.conversation_memory.add_user_message(user_id, channel_id, message.content)
            
            # Get conversation context for the worker
            conversation_context = self.conversation_memory.get_conversation(
                user_id, channel_id, limit=10
            )
            
            # Get persistent memory context
            persistent_context = self.persistent_memory.get_context_for_llm(user_id)
            
            # Inject context into message metadata (workers can use this)
            message.metadata = message.metadata or {}
            message.metadata["conversation_history"] = conversation_context
            message.metadata["user_context"] = persistent_context
            
            # Pass the notifier to process()
            response = await target_worker.process(message, notifier=progress_notifier)
            
            # Store assistant response in memory
            self.conversation_memory.add_assistant_message(
                user_id, channel_id, response.content
            )
        else:
            response = StandardResponse(
                content="System Error: No workers available."
            )

        # Send final response
        await current_adapter.reply(message, response)

    def setup_discord(self) -> Optional[DiscordAdapter]:
        """
        Set up the Discord adapter if configured.

        Returns:
            DiscordAdapter instance or None if not configured
        """
        if not self.settings.discord.token:
            logger.warning("Discord token not configured, skipping Discord adapter")
            return None

        adapter = DiscordAdapter(
            token=self.settings.discord.token,
            command_prefix=self.settings.discord.command_prefix,
        )
        adapter.set_message_handler(self.handle_message)

        # Add a hello command for testing
        @adapter.bot.command(name="hello")
        async def hello_command(ctx):
            """Say hello to the bot."""
            await ctx.send(f"Hello, {ctx.author.display_name}! I'm your AI Worker.")

        @adapter.bot.command(name="ping")
        async def ping_command(ctx):
            """Check if the bot is responsive."""
            latency = round(adapter.bot.latency * 1000)
            await ctx.send(f"Pong! Latency: {latency}ms")

        @adapter.bot.command(name="remember")
        async def remember_command(ctx, key: str, *, value: str):
            """Store a fact about yourself. Usage: !remember name John"""
            user_id = str(ctx.author.id)
            self.persistent_memory.remember_fact(user_id, key, value)
            await ctx.send(f"Got it! I'll remember that your {key} is: {value}")

        @adapter.bot.command(name="recall")
        async def recall_command(ctx, key: str):
            """Recall a stored fact. Usage: !recall name"""
            user_id = str(ctx.author.id)
            value = self.persistent_memory.recall_fact(user_id, key)
            if value:
                await ctx.send(f"Your {key} is: {value}")
            else:
                await ctx.send(f"I don't have any information about your {key}.")

        @adapter.bot.command(name="forget")
        async def forget_command(ctx, key: str):
            """Forget a specific fact. Usage: !forget name"""
            user_id = str(ctx.author.id)
            if self.persistent_memory.forget(user_id, key):
                await ctx.send(f"I've forgotten about your {key}.")
            else:
                await ctx.send(f"I didn't have any information about your {key}.")

        @adapter.bot.command(name="memory")
        async def memory_command(ctx):
            """Show what I remember about you."""
            user_id = str(ctx.author.id)
            context = self.persistent_memory.get_context_for_llm(user_id)
            stats = self.conversation_memory.get_stats()
            
            if context:
                await ctx.send(f"**What I know about you:**\n{context}\n\n"
                               f"**Active conversations:** {stats['active_conversations']}")
            else:
                await ctx.send(f"I don't have any stored memories about you yet.\n"
                               f"Use `!remember <key> <value>` to teach me something!")

        @adapter.bot.command(name="clearhistory")
        async def clearhistory_command(ctx):
            """Clear your conversation history in this channel."""
            user_id = str(ctx.author.id)
            channel_id = str(ctx.channel.id)
            self.conversation_memory.clear_conversation(user_id, channel_id)
            await ctx.send("Your conversation history in this channel has been cleared.")

        @adapter.bot.command(name="clearall")
        async def clearall_command(ctx):
            """Clear ALL your memory (conversation + persistent + worker memory)."""
            user_id = str(ctx.author.id)
            channel_id = str(ctx.channel.id)
            
            # 1. Clear conversation memory for this channel
            self.conversation_memory.clear_conversation(user_id, channel_id)
            
            # 2. Clear persistent memory (SQLite)
            deleted_count = self.persistent_memory.clear_all_user(user_id)
            
            # 3. Clear worker internal memory
            for worker in self.workers.values():
                worker.clear_memory()
            if self.default_worker:
                self.default_worker.clear_memory()
            
            await ctx.send(
                f"🧹 **Memory cleared!**\n"
                f"- Conversation history: cleared\n"
                f"- Persistent memories: {deleted_count} items deleted\n"
                f"- Worker memory: all cleared"
            )

        @adapter.bot.command(name="tools")
        async def tools_command(ctx):
            """List all registered tools (local + MCP)."""
            from ai_worker.tools.registry import ToolRegistry
            tools = ToolRegistry.list_tools()
            local_tools = [t for t in tools if "__" not in t]
            mcp_tools = [t for t in tools if "__" in t]
            
            msg = f"**Local Tools ({len(local_tools)}):** {', '.join(local_tools)}\n"
            msg += f"**MCP Tools ({len(mcp_tools)}):** {', '.join(mcp_tools)}"
            await ctx.send(msg)

        @adapter.bot.command(name="mcp_test")
        async def mcp_test_command(ctx, *, query: str = "Python programming"):
            """Test MCP tool call. Usage: !mcp_test <query>"""
            from ai_worker.tools.registry import ToolRegistry
            
            await ctx.send(f"🔄 Testing MCP tool `self_hosted__web_search` with query: `{query}`...")
            
            try:
                # Get the MCP proxy tool
                tool = ToolRegistry.create_tool("self_hosted__web_search")
                
                # Call the tool
                result = await tool.execute(query=query, max_results=3)
                
                if result.success:
                    # Truncate if too long
                    data = str(result.data)
                    if len(data) > 1800:
                        data = data[:1800] + "...(truncated)"
                    await ctx.send(f"✅ **MCP Tool Success!**\n```\n{data}\n```")
                else:
                    await ctx.send(f"❌ **MCP Tool Error:** {result.error}")
                    
            except Exception as e:
                await ctx.send(f"❌ **Exception:** {str(e)}")

        return adapter

    async def run(self) -> None:
        """Run the AI Worker application."""
        logger.info("Starting AI Worker...")

        # Validate settings
        errors = self.settings.validate()
        if errors:
            for error in errors:
                logger.warning(f"Configuration warning: {error}")

        # Start MCP Client Manager FIRST (so MCP tools are registered before workers)
        try:
            await self.mcp_client_manager.start()
        except Exception as e:
            logger.error(f"Failed to start MCP Client Manager: {e}")

        # Set up workers (now they can use MCP tools via ToolRegistry)
        self.setup_workers()

        # Set up adapters
        discord_adapter = self.setup_discord()
        if discord_adapter:
            self.adapters.append(discord_adapter)

        if not self.adapters:
            logger.error("No adapters configured! Please set up at least one platform.")
            logger.info("Copy .env.example to .env and configure your credentials.")
            return

        # Start all adapters
        try:
            tasks = [adapter.start() for adapter in self.adapters]
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully shutdown all adapters."""
        logger.info("Shutting down AI Worker...")
        
        # Stop MCP Client Manager
        try:
            await self.mcp_client_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping MCP Client Manager: {e}")
            
        for adapter in self.adapters:
            try:
                await adapter.stop()
            except Exception as e:
                logger.error(f"Error stopping {adapter.name}: {e}")


def main() -> None:
    """Main entry point."""
    app = AIWorkerApp()

    # Handle graceful shutdown
    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
