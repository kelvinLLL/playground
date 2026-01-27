"""
Task Runner for opencode_extensions.
Wraps execution of commands or functions to trigger plugin events automatically.
"""

import logging
import subprocess
import time
import shlex
from typing import List, Union, Callable, Any, Optional
from .manager import PluginManager

logger = logging.getLogger(__name__)


class TaskRunner:
    """
    Executes tasks and triggers plugin events (on_start, on_finish).
    """

    def __init__(self, plugin_manager: PluginManager) -> None:
        """
        Args:
            plugin_manager: Configured PluginManager instance.
        """
        self.pm = plugin_manager

    def run_command(self, command: Union[str, List[str]]) -> int:
        """
        Runs a shell command and triggers events.

        Args:
            command: Command string or list of arguments.

        Returns:
            Exit code of the process.
        """
        if isinstance(command, str):
            # Split string command safely
            args = shlex.split(command)
        else:
            args = command

        command_str = " ".join(args)
        logger.info("Runner starting command: %s", command_str)

        self.pm.trigger("on_start", command=command_str)
        
        start_time = time.time()
        success = False
        return_code = 1

        try:
            # Run the command, allowing stdout/stderr to passthrough to console
            # so the user sees the 'opencode' output in real-time.
            process = subprocess.run(args, check=False)
            return_code = process.returncode
            success = (return_code == 0)
        except FileNotFoundError:
            logger.error("Command not found: %s", args[0])
            return_code = 127
        except Exception as e:
            logger.error("Error executing command: %s", e)
            return_code = 1
        finally:
            duration = time.time() - start_time
            self.pm.trigger(
                "on_finish", 
                success=success, 
                duration=duration, 
                return_code=return_code
            )
            
        return return_code

    def run_function(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Runs a Python function and triggers events.

        Args:
            func: The function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The return value of the function.
        """
        func_name = getattr(func, "__name__", str(func))
        logger.info("Runner starting function: %s", func_name)

        self.pm.trigger("on_start", function=func_name)

        start_time = time.time()
        success = False
        result = None

        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            logger.error("Error executing function '%s': %s", func_name, e)
            # Re-raise after triggering finish? 
            # Ideally yes, but we want to ensure on_finish fires.
            duration = time.time() - start_time
            self.pm.trigger(
                "on_finish", 
                success=False, 
                duration=duration, 
                error=e
            )
            raise e
        
        duration = time.time() - start_time
        self.pm.trigger(
            "on_finish", 
            success=True, 
            duration=duration, 
            result=result
        )

        return result
