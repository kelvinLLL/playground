"""Adapters module for AI Worker - platform-specific implementations."""

from .base import BaseAdapter
from .discord_adapter import DiscordAdapter

__all__ = ["BaseAdapter", "DiscordAdapter"]
