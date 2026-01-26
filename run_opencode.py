"""
Demo script for the opencode_extensions plugin system.
Shows how to register and trigger plugins.
"""

import logging
import time
from opencode_extensions.manager import PluginManager
from opencode_extensions.plugins.sound import SoundPlugin
from opencode_extensions.plugins.voice import VoicePlugin


# Configure logging to show plugin activity in the console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    Main execution flow for the plugin system demonstration.
    """
    # 1. Initialize the PluginManager
    manager = PluginManager()

    # 2. Register plugins
    # To add more plugins, simply create a class with event methods 
    # (e.g., on_start, on_finish) and register an instance here.
    manager.register_plugin(SoundPlugin())
    manager.register_plugin(VoicePlugin())

    logger.info("Starting task simulation...")

    # 3. Trigger 'on_start' event
    # This will initialize the voice listener (if dependencies are met)
    manager.trigger("on_start")

    # 4. Simulate application work
    logger.info("Working on a complex coding task...")
    time.sleep(2)

    # 5. Trigger 'on_finish' event
    # This will play a completion sound and perform other cleanup
    logger.info("Task completed successfully.")
    manager.trigger("on_finish", status="success", duration=2.0)


if __name__ == "__main__":
    main()
