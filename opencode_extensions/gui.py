"""
GUI configuration tool for opencode_extensions.
Allows users to enable/disable plugins via a Tkinter interface.
"""

import json
import logging
import os
import tkinter as tk
from tkinter import messagebox
from typing import Dict


logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "plugins_config.json"
)

DEFAULT_CONFIG = {
    "SoundPlugin": True,
    "VoicePlugin": False
}


class PluginConfigGUI:
    """
    Tkinter GUI for managing plugin configuration.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Plugin Manager")
        self.root.geometry("300x200")

        self.config = self._load_config()
        self.vars: Dict[str, tk.BooleanVar] = {}

        self._build_ui()

    def _load_config(self) -> Dict[str, bool]:
        """Loads configuration from JSON file or returns defaults."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to load config: %s", e)
        return DEFAULT_CONFIG.copy()

    def _save_config(self) -> None:
        """Saves current GUI state to JSON file."""
        new_config = {name: var.get() for name, var in self.vars.items()}
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(new_config, f, indent=4)
            messagebox.showinfo("Success", "Configuration saved successfully!")
        except Exception as e:
            logger.error("Failed to save config: %s", e)
            messagebox.showerror("Error", f"Failed to save config: {e}")

    def _build_ui(self) -> None:
        """Constructs the Tkinter interface."""
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        tk.Label(
            main_frame,
            text="Enable/Disable Plugins",
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 10))

        # Create checkboxes for each plugin
        for plugin_name, enabled in self.config.items():
            var = tk.BooleanVar(value=enabled)
            self.vars[plugin_name] = var
            cb = tk.Checkbutton(
                main_frame,
                text=plugin_name,
                variable=var,
                anchor="w"
            )
            cb.pack(fill="x")

        # Save button
        save_btn = tk.Button(
            main_frame,
            text="Save Configuration",
            command=self._save_config,
            bg="#4CAF50",
            fg="black"
        )
        save_btn.pack(pady=(20, 0))


def main() -> None:
    """Main entry point for the GUI tool."""
    root = tk.Tk()
    app = PluginConfigGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
