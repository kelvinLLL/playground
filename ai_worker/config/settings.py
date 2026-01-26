"""
Settings management for AI Worker.

Handles loading configuration from environment variables and .env files.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv


@dataclass
class DiscordConfig:
    """Discord platform configuration."""

    token: str = ""
    command_prefix: str = "!"


@dataclass
class FeishuConfig:
    """Feishu (Lark) platform configuration."""

    app_id: str = ""
    app_secret: str = ""
    verification_token: str = ""
    encrypt_key: str = ""


@dataclass
class OpenAIConfig:
    """OpenAI LLM configuration."""

    api_key: str = ""
    base_url: Optional[str] = None  # Added base_url support
    model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class SearchConfig:
    """Web search configuration."""

    tavily_api_key: str = ""  # Tavily API key for web search


@dataclass
class Settings:
    """
    Main settings class for AI Worker.

    Loads configuration from environment variables.
    """

    discord: DiscordConfig = field(default_factory=DiscordConfig)
    feishu: FeishuConfig = field(default_factory=FeishuConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    debug: bool = False

    @classmethod
    def from_env(cls, env_path: Optional[str] = None) -> "Settings":
        """
        Load settings from environment variables.

        Args:
            env_path: Optional path to .env file. If not provided,
                     will look for .env in current directory.

        Returns:
            Settings instance with loaded configuration.
        """
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        return cls(
            discord=DiscordConfig(
                token=os.getenv("DISCORD_TOKEN", ""),
                command_prefix=os.getenv("DISCORD_PREFIX", "!"),
            ),
            feishu=FeishuConfig(
                app_id=os.getenv("FEISHU_APP_ID", ""),
                app_secret=os.getenv("FEISHU_APP_SECRET", ""),
                verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN", ""),
                encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY", ""),
            ),
            openai=OpenAIConfig(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4096")),
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            ),
            search=SearchConfig(
                tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
            ),
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )

    def validate(self) -> list[str]:
        """
        Validate settings and return list of missing required fields.

        Returns:
            List of error messages for missing/invalid configuration.
        """
        errors = []

        # Check Discord config if token is partially set
        if not self.discord.token:
            errors.append("DISCORD_TOKEN is not set")

        # Check OpenAI config
        if not self.openai.api_key:
            errors.append("OPENAI_API_KEY is not set")

        return errors


# Global settings instance
_settings: Optional[Settings] = None


def get_settings(env_path: Optional[str] = None) -> Settings:
    """
    Get or create the global settings instance.

    Args:
        env_path: Optional path to .env file.

    Returns:
        Global Settings instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_env(env_path)
    return _settings
