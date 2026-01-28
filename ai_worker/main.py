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
from ai_worker.workers.game_worker import GameWorker
from ai_worker.workers.daily_brief_worker import DailyBriefWorker
from ai_worker.config.curated_sources import (
    get_all_sources,
    DEFAULT_PROFILE,
    QUICK_PROFILE,
    CHINESE_PROFILE,
    RESEARCH_PROFILE,
    DEVELOPER_PROFILE,
)
from ai_worker.memory import ConversationMemory, PersistentMemory
from ai_worker.mcp_client import MCPClientManager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

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
        
        # Scheduler for daily tasks
        self.scheduler = AsyncIOScheduler()
        
        # Workers map
        self.workers = {}
        self.default_worker = None
        
        # Context links cache: channel_id -> list of {title, url}
        # Used for context-aware follow-up questions
        self.context_links_cache: dict[str, list[dict[str, str]]] = {}
        
        # Load notification channel from config (persisted in .env)
        self.notification_channel_id: Optional[str] = (
            self.settings.scheduler.notification_channel_id or None
        )
        
        # Daily brief enabled flag
        self.daily_brief_enabled: bool = self.settings.scheduler.daily_brief_enabled

    def setup_workers(self) -> None:
        """Set up all AI workers."""
        if not self.settings.openai.api_key:
            logger.warning("OpenAI API key missing! Workers will be disabled.")
            return

        llm = OpenAIClient(self.settings.openai)
        
        # Initialize specialized workers
        intel_worker = IntelWorker(llm)
        strategy_worker = StrategyWorker(llm)
        game_worker = GameWorker(
            llm,
            tavily_api_key=self.settings.search.tavily_api_key or None
        )
        daily_brief_worker = DailyBriefWorker(llm)
        
        # Register workers (for routing)
        self.workers = {
            "intel": intel_worker,
            "strategy": strategy_worker,
            "game": game_worker,
            "daily_brief": daily_brief_worker,
        }
        
        # Initialize the smart router (DefaultWorker) with access to other workers
        self.default_worker = DefaultWorker(llm, workers=self.workers)
        self.workers["default"] = self.default_worker
        
        logger.info(f"Initialized workers: {list(self.workers.keys())}")

    def _update_env_file(self, key: str, value: str) -> None:
        """Update a key in the .env file."""
        import os
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        
        lines = []
        found = False
        
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                found = True
                break
        
        if not found:
            lines.append(f"{key}={value}\n")
        
        with open(env_path, "w") as f:
            f.writelines(lines)
        
        logger.info(f"Persisted {key}={value} to .env")

    async def handle_message(self, message: StandardMessage) -> None:
        """
        Handle an incoming message from any adapter.

        Uses LLM-based smart routing via DefaultWorker.
        """
        logger.info(
            f"[{message.platform.value}] {message.author.name}: {message.content}"
        )

        if not message.content or message.content.startswith("!"):
            return

        # Find the adapter for this platform
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
            response = StandardResponse(content=text)
            await current_adapter.reply(message, response)

        # --- SMART ROUTING via DefaultWorker (LLM-based) ---
        if not self.default_worker:
            response = StandardResponse(content="System Error: No workers available.")
            await current_adapter.reply(message, response)
            return

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
        
        # Inject context into message metadata
        message.metadata = message.metadata or {}
        message.metadata["conversation_history"] = conversation_context
        message.metadata["user_context"] = persistent_context
        
        # Inject context links from recent interactions (e.g., daily brief)
        if channel_id in self.context_links_cache:
            message.metadata["context_links"] = self.context_links_cache[channel_id]
        
        # Route via smart router (DefaultWorker with LLM function calling)
        response = await self.default_worker.process(message, notifier=progress_notifier)
        
        # Store assistant response in memory
        self.conversation_memory.add_assistant_message(
            user_id, channel_id, response.content
        )
        
        # If response contains context_links (e.g., from DailyBrief), cache them
        if response.extras and response.extras.get("context_links"):
            self.context_links_cache[channel_id] = response.extras["context_links"]
            logger.info(f"Cached {len(response.extras['context_links'])} context links for channel {channel_id}")

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

        @adapter.bot.command(name="skills")
        async def skills_command(ctx):
            """List available skills and capabilities."""
            from ai_worker.skills.base import SkillRegistry
            
            skills = SkillRegistry.list_skills()
            
            # Group by category
            by_category = {}
            for skill in skills:
                cat = skill.category
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(skill)
            
            msg = "**🧠 AI Worker Skills Matrix**\n\n"
            
            for cat, cat_skills in by_category.items():
                msg += f"**{cat}**\n"
                for s in cat_skills:
                    msg += f"{s.emoji} **{s.name}**: {s.description}\n"
                msg += "\n"
                
            msg += "**Specialized Workers:**\n"
            for name, worker in self.workers.items():
                if name != "default":
                    msg += f"🤖 **{name.title()}**: {worker.config.description[:50]}...\n"
            
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

        @adapter.bot.command(name="sources")
        async def sources_command(ctx, profile: str = None):
            """List available sources. Usage: !sources [profile]"""
            all_sources = get_all_sources()
            
            # Profile info
            profiles = {
                "default": ("Default", DEFAULT_PROFILE, "Full daily brief (priority 1-2)"),
                "quick": ("Quick", QUICK_PROFILE, "Fast mode (priority 1 only)"),
                "chinese": ("Chinese", CHINESE_PROFILE, "Chinese-focused"),
                "research": ("Research", RESEARCH_PROFILE, "Papers and research"),
                "developer": ("Developer", DEVELOPER_PROFILE, "GitHub + Community"),
            }
            
            if profile and profile.lower() in profiles:
                # Show specific profile
                name, sources, desc = profiles[profile.lower()]
                msg = f"**📋 {name} Profile** ({len(sources)} sources)\n{desc}\n\n"
                
                # Group by category
                by_category = {}
                for s in sources:
                    cat = s.category
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append(s)
                
                for cat, cat_sources in by_category.items():
                    msg += f"**{cat}:**\n"
                    for s in cat_sources:
                        status = "✅" if s.enabled else "❌"
                        msg += f"  {s.emoji} {s.name} ({s.source_type.value}) {status}\n"
                    msg += "\n"
                
                if len(msg) > 1900:
                    msg = msg[:1900] + "..."
                await ctx.send(msg)
            else:
                # Show profiles overview
                msg = "**📚 Source Profiles**\n\n"
                for key, (name, sources, desc) in profiles.items():
                    msg += f"**`!sources {key}`** - {name} ({len(sources)} sources)\n  {desc}\n\n"
                
                msg += "**Usage:**\n"
                msg += "`!sources` - Show this overview\n"
                msg += "`!sources quick` - List Quick profile sources\n"
                msg += "`!brief quick` - Generate brief with Quick profile\n"
                
                await ctx.send(msg)

        @adapter.bot.command(name="brief")
        async def brief_command(ctx, profile: str = None):
            """Generate a Daily Intelligence Brief. Usage: !brief [profile]
            
            Profiles: quick, research, chinese, developer (default: full)
            """
            # Determine profile
            profiles_map = {
                "quick": (QUICK_PROFILE, "Quick"),
                "research": (RESEARCH_PROFILE, "Research"),
                "chinese": (CHINESE_PROFILE, "Chinese"),
                "developer": (DEVELOPER_PROFILE, "Developer"),
            }
            
            if profile and profile.lower() in profiles_map:
                sources, profile_name = profiles_map[profile.lower()]
                await ctx.send(f"📋 **Starting {profile_name} Brief** ({len(sources)} sources)...\nThis may take 1-2 minutes.")
                quick_mode = profile.lower() == "quick"
            else:
                sources = DEFAULT_PROFILE
                profile_name = "Default"
                quick_mode = False
                await ctx.send(f"📋 **Starting Daily Brief** ({len(sources)} sources)...\nThis may take 1-2 minutes.")
            
            try:
                # Create a new DailyBriefWorker with the selected profile
                llm = self.workers.get("daily_brief").llm
                worker = DailyBriefWorker(llm, use_curated_sources=True, quick_mode=quick_mode)
                worker.sources = sources  # Override with selected profile
                
                # Create a notifier that sends updates to the channel
                async def discord_notifier(text: str):
                    await ctx.send(text)
                
                # Generate the brief
                response = await worker.generate_brief(notifier=discord_notifier)
                
                # Cache context_links for follow-up queries
                channel_id = str(ctx.channel.id)
                if response.extras and response.extras.get("context_links"):
                    self.context_links_cache[channel_id] = response.extras["context_links"]
                    logger.info(f"[!brief] Cached {len(response.extras['context_links'])} context links for channel {channel_id}")
                
                # Send file attachment if available
                file_path = response.extras.get("file_path")
                if file_path:
                    import discord
                    try:
                        file_obj = discord.File(file_path)
                        await ctx.send(content=response.content, file=file_obj)
                    except Exception as e:
                        await ctx.send(f"{response.content}\n\n⚠️ 文件发送失败: {e}\n📁 本地路径: `{file_path}`")
                else:
                    # Fallback: send text only
                    content = response.content
                    if len(content) > 1900:
                        content = content[:1900] + "...\n\n*See full report in file*"
                    await ctx.send(content)
                
            except Exception as e:
                await ctx.send(f"❌ **Brief generation failed:** {str(e)}")

        @adapter.bot.command(name="setchannel")
        async def setchannel_command(ctx):
            """Set this channel for scheduled notifications. Usage: !setchannel"""
            self.notification_channel_id = str(ctx.channel.id)
            
            # Persist to .env file
            self._update_env_file("NOTIFICATION_CHANNEL_ID", self.notification_channel_id)
            
            hour = self.settings.scheduler.daily_brief_hour
            minute = self.settings.scheduler.daily_brief_minute
            await ctx.send(
                f"✅ **Notification channel set!**\n"
                f"Channel: {ctx.channel.name} (`{self.notification_channel_id}`)\n"
                f"Daily briefs will be sent here at {hour:02d}:{minute:02d}.\n"
                f"*(Setting persisted - will survive restarts)*"
            )

        @adapter.bot.command(name="settime")
        async def settime_command(ctx, hour: int, minute: int = 0):
            """Set daily brief time. Usage: !settime 9 30"""
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                await ctx.send("❌ Invalid time. Hour: 0-23, Minute: 0-59")
                return
            
            # Update settings
            self.settings.scheduler.daily_brief_hour = hour
            self.settings.scheduler.daily_brief_minute = minute
            tz = self.settings.scheduler.timezone
            
            # Persist to .env
            self._update_env_file("DAILY_BRIEF_HOUR", str(hour))
            self._update_env_file("DAILY_BRIEF_MINUTE", str(minute))
            
            # Reschedule the job
            self.scheduler.reschedule_job(
                "daily_brief",
                trigger=CronTrigger(hour=hour, minute=minute, timezone=tz)
            )
            
            await ctx.send(
                f"✅ **Schedule updated!**\n"
                f"Daily brief now scheduled for **{hour:02d}:{minute:02d}** ({tz})\n"
                f"*(Setting persisted - will survive restarts)*"
            )

        @adapter.bot.command(name="schedule")
        async def schedule_command(ctx):
            """Show scheduled tasks. Usage: !schedule"""
            jobs = self.scheduler.get_jobs()
            tz = self.settings.scheduler.timezone
            
            if not jobs:
                await ctx.send("No scheduled tasks.")
                return
            
            msg = f"**📅 Scheduled Tasks** (Timezone: {tz}):\n"
            for job in jobs:
                next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M") if job.next_run_time else "N/A"
                msg += f"- **{job.name}** (ID: `{job.id}`): Next run at {next_run}\n"
            
            if self.notification_channel_id:
                msg += f"\n**Notification Channel:** <#{self.notification_channel_id}>"
            else:
                msg += "\n⚠️ **No notification channel set.** Use `!setchannel` to configure."
            
            await ctx.send(msg)

        @adapter.bot.command(name="enablebrief")
        async def enablebrief_command(ctx):
            """Enable scheduled daily brief. Usage: !enablebrief"""
            if not self.notification_channel_id:
                await ctx.send(
                    "❌ **Please set a notification channel first!**\n"
                    "Use `!setchannel` in the channel where you want to receive daily briefs."
                )
                return
            
            self.daily_brief_enabled = True
            self._update_env_file("DAILY_BRIEF_ENABLED", "true")
            
            # Add the job if not exists
            hour = self.settings.scheduler.daily_brief_hour
            minute = self.settings.scheduler.daily_brief_minute
            tz = self.settings.scheduler.timezone
            
            try:
                self.scheduler.add_job(
                    self._run_daily_brief,
                    CronTrigger(hour=hour, minute=minute, timezone=tz),
                    id="daily_brief",
                    name="Daily Intelligence Brief",
                    replace_existing=True
                )
            except Exception:
                pass  # Job may already exist
            
            await ctx.send(
                f"✅ **Daily Brief ENABLED!**\n"
                f"Schedule: **{hour:02d}:{minute:02d}** ({tz})\n"
                f"Channel: <#{self.notification_channel_id}>\n"
                f"Use `!disablebrief` to turn off."
            )

        @adapter.bot.command(name="disablebrief")
        async def disablebrief_command(ctx):
            """Disable scheduled daily brief. Usage: !disablebrief"""
            self.daily_brief_enabled = False
            self._update_env_file("DAILY_BRIEF_ENABLED", "false")
            
            # Remove the job
            try:
                self.scheduler.remove_job("daily_brief")
            except Exception:
                pass  # Job may not exist
            
            await ctx.send(
                "✅ **Daily Brief DISABLED!**\n"
                "No scheduled briefs will run. Use `!enablebrief` to reactivate.\n"
                "You can still use `!brief` for manual generation."
            )

        @adapter.bot.command(name="aihelp")
        async def help_command(ctx):
            """Show all available commands and features."""
            help1 = """**🤖 AI Worker - 命令帮助**

**━━━ 基础命令 ━━━**
`!ping` - 检查机器人响应延迟
`!hello` - 打个招呼
`!aihelp` - 显示此帮助信息

**━━━ 记忆系统 ━━━**
`!remember <key> <value>` - 记住一个事实
`!recall <key>` - 回忆一个事实
`!forget <key>` - 忘记一个事实
`!memory` - 显示所有记忆
`!clearhistory` - 清除当前频道对话历史
`!clearall` - 清除所有记忆"""

            help2 = """**━━━ 每日简报 (Daily Brief) ━━━**
`!brief` - 生成默认每日智能简报（24个源）
`!brief quick` - 快速模式（11个高优先级源）
`!brief research` - 论文研究模式
`!brief chinese` - 中文资讯模式
`!brief developer` - 开发者模式 (GitHub + 社区)

**━━━ 信息源管理 ━━━**
`!sources` - 显示所有可用 Profile
`!sources quick` - 查看 Quick Profile 的源列表
`!sources research` - 查看 Research Profile 的源列表

**━━━ 定时任务 ━━━**
`!setchannel` - 设置当前频道为通知频道
`!settime <时> <分>` - 设置发送时间（北京时间）
  └ 例: `!settime 8 30` = 每天早上 8:30
`!enablebrief` - 启用定时简报
`!disablebrief` - 禁用定时简报
`!schedule` - 查看当前定时任务状态

**设置步骤**: 1️⃣ `!setchannel` → 2️⃣ `!settime 8 0` → 3️⃣ `!enablebrief`"""

            help3 = """**━━━ 工具调试 ━━━**
`!skills` - 列出所有技能和能力
`!mcp_test <query>` - 测试 MCP 调用

**━━━ 智能对话 (无需命令) ━━━**
直接用自然语言交流，Bot 会自动理解：
• "帮我搜索最新的 AI 新闻"
• "黑神话悟空怎么打杨戬"
• "分析这篇论文 [链接]"
• "生成今天的日报" """

            await ctx.send(help1)
            await ctx.send(help2)
            await ctx.send(help3)

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

        # Set up scheduler for daily brief
        self._setup_scheduler()

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
        
        # Stop scheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
        
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

    def _setup_scheduler(self) -> None:
        """Set up APScheduler for daily tasks."""
        hour = self.settings.scheduler.daily_brief_hour
        minute = self.settings.scheduler.daily_brief_minute
        tz = self.settings.scheduler.timezone
        
        # Only add job if enabled
        if self.daily_brief_enabled:
            self.scheduler.add_job(
                self._run_daily_brief,
                CronTrigger(hour=hour, minute=minute, timezone=tz),
                id="daily_brief",
                name="Daily Intelligence Brief",
                replace_existing=True
            )
            logger.info(f"Daily brief ENABLED, scheduled for {hour:02d}:{minute:02d} ({tz})")
        else:
            logger.info("Daily brief DISABLED. Use !enablebrief to activate.")
        
        self.scheduler.start()

    async def _run_daily_brief(self) -> None:
        """Execute daily brief and send to notification channel."""
        # Double-check enabled flag
        if not self.daily_brief_enabled:
            logger.info("Daily brief skipped - disabled")
            return
            
        logger.info("Executing scheduled daily brief...")
        
        daily_brief_worker = self.workers.get("daily_brief")
        if not daily_brief_worker:
            logger.error("DailyBriefWorker not available for scheduled run")
            return
        
        try:
            # Generate the brief
            response = await daily_brief_worker.generate_brief()
            
            # Send to Discord if notification channel is set
            if self.notification_channel_id and self.adapters:
                discord_adapter = self.adapters[0]  # Assuming first adapter is Discord
                
                # Send with file attachment
                file_path = response.extras.get("file_path")
                if file_path:
                    response_with_file = StandardResponse(
                        content=response.content,
                        message_type=response.message_type,
                        extras={"file_path": file_path}
                    )
                    await discord_adapter.send_message(
                        self.notification_channel_id,
                        response_with_file
                    )
                else:
                    await discord_adapter.send_message(
                        self.notification_channel_id,
                        StandardResponse(content=f"📋 **Scheduled Daily Brief**\n\n{response.content[:1800]}")
                    )
                logger.info(f"Daily brief sent to channel {self.notification_channel_id}")
            else:
                logger.warning("No notification channel set. Use !setchannel to configure.")
                
        except Exception as e:
            logger.error(f"Scheduled daily brief failed: {e}")


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
