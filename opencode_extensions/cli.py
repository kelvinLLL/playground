"""
Command Line Interface for opencode_extensions.
Usage: python cli.py [command]

Example:
    python cli.py python my_script.py
    python cli.py echo "Hello World"
"""

import sys
import os
import argparse
import logging

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from manager import PluginManager
from runner import TaskRunner
from plugins.sound import SoundPlugin
from plugins.voice import VoicePlugin

def main() -> None:
    """
    Main entry point for the CLI wrapper.
    """
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    parser = argparse.ArgumentParser(
        description="Run a command with opencode_extensions plugins (Sound, Voice)."
    )
    parser.add_argument(
        "command", 
        nargs=argparse.REMAINDER, 
        help="The command to run (e.g., python script.py)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize System
    manager = PluginManager()
    
    # Register Plugins (Could be dynamic based on config, but explicit here for demo)
    manager.register_plugin(SoundPlugin())
    manager.register_plugin(VoicePlugin())
    
    runner = TaskRunner(manager)
    
    # Run the wrapped command
    # The runner handles on_start/on_finish triggering
    exit_code = runner.run_command(args.command)
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
