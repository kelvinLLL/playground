"""
Discord adapter implementation.

Handles all Discord-specific message conversion and API interaction.
"""

import logging
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands

from ai_worker.adapters.base import BaseAdapter
from ai_worker.core.message import (
    Attachment,
    Channel,
    MessageType,
    Platform,
    StandardMessage,
    StandardResponse,
    User,
)

logger = logging.getLogger(__name__)


class DiscordAdapter(BaseAdapter):
    """
    Discord platform adapter.

    Converts Discord messages to StandardMessage format and handles
    sending responses back to Discord.
    """

    def __init__(self, token: str, command_prefix: str = "!"):
        """
        Initialize the Discord adapter.

        Args:
            token: Discord bot token
            command_prefix: Command prefix for bot commands (default: "!")
        """
        super().__init__("Discord")
        self.token = token
        self.command_prefix = command_prefix

        # Set up Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        # intents.members = True  # Requires privileged intent, enable in portal if needed

        # Create the bot client
        self.bot = commands.Bot(command_prefix=command_prefix, intents=intents)
        self._setup_events()

    def _setup_events(self) -> None:
        """Set up Discord event handlers."""

        @self.bot.event
        async def on_ready() -> None:
            """Called when the bot is ready."""
            logger.info(f"Discord bot logged in as {self.bot.user}")
            self._running = True

        @self.bot.event
        async def on_message(message: discord.Message) -> None:
            """Called when a message is received."""
            # Ignore messages from the bot itself
            if message.author == self.bot.user:
                return

            # Convert to StandardMessage and process
            std_message = self._convert_message(message)
            
            # 1. Visual feedback: React with an emoji to show we received it
            try:
                await message.add_reaction("👀")
            except Exception as e:
                logger.warning(f"Failed to add reaction: {e}")

            # 2. Show typing indicator while processing
            async with message.channel.typing():
                await self.on_message(std_message)

            # Also process commands
            await self.bot.process_commands(message)

    def _convert_message(self, message: discord.Message) -> StandardMessage:
        """
        Convert a Discord message to StandardMessage format.

        Args:
            message: Discord message object

        Returns:
            StandardMessage representation
        """
        # Convert author
        author = User(
            id=str(message.author.id),
            name=message.author.name,
            display_name=message.author.display_name,
            is_bot=message.author.bot,
            platform=Platform.DISCORD,
        )

        # Convert channel
        channel = Channel(
            id=str(message.channel.id),
            name=getattr(message.channel, "name", "DM"),
            platform=Platform.DISCORD,
            is_private=isinstance(message.channel, discord.DMChannel),
        )

        # Convert attachments
        attachments = [
            Attachment(
                filename=att.filename,
                url=att.url,
                content_type=att.content_type,
                size=att.size,
            )
            for att in message.attachments
        ]

        # Convert mentions
        mentions = [
            User(
                id=str(user.id),
                name=user.name,
                display_name=user.display_name,
                is_bot=user.bot,
                platform=Platform.DISCORD,
            )
            for user in message.mentions
        ]

        # Determine message type
        msg_type = MessageType.TEXT
        if message.content.startswith(self.command_prefix):
            msg_type = MessageType.COMMAND

        return StandardMessage(
            id=str(message.id),
            content=message.content,
            message_type=msg_type,
            platform=Platform.DISCORD,
            author=author,
            channel=channel,
            timestamp=message.created_at or datetime.now(),
            raw_data=message,
            attachments=attachments,
            mentions=mentions,
            reply_to=str(message.reference.message_id) if message.reference else None,
        )

    async def start(self) -> None:
        """Start the Discord bot."""
        logger.info("Starting Discord adapter...")
        await self.bot.start(self.token)

    async def stop(self) -> None:
        """Stop the Discord bot gracefully."""
        logger.info("Stopping Discord adapter...")
        self._running = False
        await self.bot.close()

    async def send_message(
        self,
        channel_id: str,
        response: StandardResponse,
    ) -> bool:
        """
        Send a message to a Discord channel.

        Args:
            channel_id: Discord channel ID
            response: StandardResponse to send

        Returns:
            True if successful, False otherwise
        """
        try:
            channel = self.bot.get_channel(int(channel_id))
            if channel is None:
                channel = await self.bot.fetch_channel(int(channel_id))

            if channel is None:
                logger.error(f"Could not find channel {channel_id}")
                return False

            # Build the message
            content = response.content

            # Handle embeds if specified in extras
            embed = None
            if "embed" in response.extras:
                embed_data = response.extras["embed"]
                embed = discord.Embed(**embed_data)

            await channel.send(content=content, embed=embed)
            return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def reply(
        self,
        original_message: StandardMessage,
        response: StandardResponse,
    ) -> bool:
        """
        Reply to a Discord message.

        Args:
            original_message: The message to reply to
            response: StandardResponse to send as reply

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the original Discord message from raw_data
            discord_msg: Optional[discord.Message] = original_message.raw_data
            if discord_msg is None:
                # Fall back to sending to channel
                if original_message.channel:
                    return await self.send_message(
                        original_message.channel.id, response
                    )
                return False

            # Build the reply
            content = response.content

            # Handle embeds if specified
            embed = None
            if "embed" in response.extras:
                embed_data = response.extras["embed"]
                embed = discord.Embed(**embed_data)

            # Split message if too long (Discord limit is 2000 chars)
            if len(content) > 2000:
                chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
                
                # Reply to the first chunk
                await discord_msg.reply(content=chunks[0], embed=embed)
                
                # Send remaining chunks to the same channel
                for chunk in chunks[1:]:
                    await discord_msg.channel.send(content=chunk)
            else:
                await discord_msg.reply(content=content, embed=embed)
                
            return True

        except Exception as e:
            logger.error(f"Failed to reply: {e}")
            return False

    def add_command(
        self,
        name: str,
        callback,
        description: str = "",
    ) -> None:
        """
        Add a custom command to the bot.

        Args:
            name: Command name (without prefix)
            callback: Async function to call when command is invoked
            description: Command description for help
        """
        cmd = commands.Command(callback, name=name, help=description)
        self.bot.add_command(cmd)
