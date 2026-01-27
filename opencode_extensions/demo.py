"""
Demo script for the opencode_extensions plugin system.
Shows how to use TaskRunner to execute tasks with automatic plugin triggers.
"""

import logging
import time
import sys
import os

# Ensure project root is in path so we can import opencode_extensions
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from opencode_extensions.manager import PluginManager
from opencode_extensions.plugins.sound import SoundPlugin
from opencode_extensions.plugins.voice import VoicePlugin
from opencode_extensions.runner import TaskRunner


# Configure logging to show plugin activity in the console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def complex_task(duration: float) -> str:
    """
    Simulates a complex task that takes some time to complete.
    """
    logger.info("Starting complex task logic...")
    time.sleep(duration)
    logger.info("Complex task logic finished.")
    return "Task Result Data"


def main() -> None:
    """
    Main execution flow for the plugin system demonstration.
    """
    # 1. Initialize the PluginManager
    manager = PluginManager()

    # 2. Register plugins
    manager.register_plugin(SoundPlugin())
    manager.register_plugin(VoicePlugin())

    # 3. Initialize TaskRunner
    runner = TaskRunner(manager)

    logger.info("--- Demo: Running a Python Function ---")
    
    # 4. Run a function via TaskRunner
    # This automatically triggers 'on_start' before and 'on_finish' after
    result = runner.run_function(complex_task, duration=2.0)
    logger.info("Function returned: %s", result)

    logger.info("\n--- Demo: Running a Shell Command ---")

    # 5. Run a command via TaskRunner
    # This also triggers the events
    exit_code = runner.run_command("echo 'Hello from shell!'")
    logger.info("Command exited with code: %d", exit_code)


if __name__ == "__main__":
    main()
