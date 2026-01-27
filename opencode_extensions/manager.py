"""
Lightweight plugin system for opencode_extensions.
"""

import json
import logging
import os
from typing import Any, Dict, List


logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "plugins_config.json"
)


class PluginManager:
    """
    Manages lightweight plugins for opencode_extensions.
    """

    def __init__(self) -> None:
        """
        Initializes the PluginManager and loads plugin configuration.
        """
        self.plugins: List[Any] = []
        self.config: Dict[str, bool] = self.load_config()

    def load_config(self) -> Dict[str, bool]:
        """
        Loads plugin configuration from JSON file.

        Returns:
            Dict mapping plugin class names to enabled status.
        """
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load plugin config: %s", e)
        return {}

    def register_plugin(self, plugin: Any) -> None:
        """
        Registers a plugin instance if it is enabled in the configuration.

        Args:
            plugin: An object instance that may implement event hooks.
        """
        plugin_name = type(plugin).__name__
        if not self.config.get(plugin_name, True):
            logger.info("Skipping disabled plugin: %s", plugin_name)
            return

        self.plugins.append(plugin)
        logger.debug("Plugin registered: %s", plugin)

    def trigger(self, event_name: str, **kwargs: Any) -> None:
        """
        Triggers an event across all registered plugins.

        If a plugin has a method matching the event_name, it will be called
        with the provided keyword arguments.

        Args:
            event_name: The name of the event to trigger (e.g., 'on_start').
            **kwargs: Arguments to pass to the plugin method.
        """
        for plugin in self.plugins:
            method = getattr(plugin, event_name, None)
            if callable(method):
                try:
                    method(**kwargs)
                except Exception as e:
                    logger.error(
                        "Error in plugin %s during event '%s': %s",
                        plugin,
                        event_name,
                        e,
                        exc_info=True,
                    )
