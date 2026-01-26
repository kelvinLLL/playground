"""
Lightweight plugin system for opencode_extensions.
"""

import logging
from typing import Any, List


logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages lightweight plugins for opencode_extensions.
    """

    def __init__(self) -> None:
        """
        Initializes the PluginManager with an empty list of plugins.
        """
        self.plugins: List[Any] = []

    def register_plugin(self, plugin: Any) -> None:
        """
        Registers a plugin instance.

        Args:
            plugin: An object instance that may implement event hooks.
        """
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
