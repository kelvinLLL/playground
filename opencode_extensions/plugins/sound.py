"""
Sound plugin for opencode_extensions.
Plays a sound on task completion.
"""

import logging
import subprocess
import sys
from typing import Any


logger = logging.getLogger(__name__)


class SoundPlugin:
    """
    A plugin that plays a system sound when a task finishes.
    """

    def on_finish(self, **kwargs: Any) -> None:
        """
        Triggered when a task completes.

        Args:
            **kwargs: Event data (ignored by this plugin).
        """
        platform = sys.platform
        try:
            if platform == "darwin":
                self._play_mac()
            elif platform == "win32":
                self._play_windows()
            elif platform.startswith("linux"):
                self._play_linux()
            else:
                logger.warning("Sound plugin: Unsupported platform '%s'", platform)
        except Exception as e:
            logger.warning("Sound plugin: Failed to play sound: %s", e)

    def _play_mac(self) -> None:
        """Plays a sound on macOS using afplay."""
        sound_path = "/System/Library/Sounds/Glass.aiff"
        subprocess.run(["afplay", sound_path], check=False)

    def _play_windows(self) -> None:
        """Plays a sound on Windows using PowerShell."""
        sound_path = "C:\\Windows\\Media\\notify.wav"
        # PowerShell command to play sound
        ps_command = (
            f'(New-Object Media.SoundPlayer "{sound_path}").PlaySync()'
        )
        subprocess.run(
            ["powershell", "-c", ps_command],
            check=False,
            capture_output=True
        )

    def _play_linux(self) -> None:
        """Plays a sound on Linux using aplay or paplay."""
        # Try aplay first (ALSA), then paplay (PulseAudio)
        try:
            # Note: Linux system sound paths vary wildly, 
            # so we just try to run the command if it exists.
            # This is a best-effort attempt.
            subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"], 
                           check=False, capture_output=True)
        except FileNotFoundError:
            try:
                subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"], 
                               check=False, capture_output=True)
            except FileNotFoundError:
                logger.debug("Linux: Neither aplay nor paplay found.")
