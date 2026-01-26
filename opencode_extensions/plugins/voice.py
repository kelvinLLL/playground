"""
Voice plugin for opencode_extensions.
Provides background voice listening capabilities.
"""

import logging
import threading
from typing import Any, Optional


logger = logging.getLogger(__name__)

try:
    import speech_recognition as sr
except ImportError:
    sr = None


class VoicePlugin:
    """
    A plugin that listens for voice commands in the background.
    """

    def __init__(self) -> None:
        """
        Initializes the VoicePlugin and checks for required dependencies.
        """
        self.has_audio: bool = sr is not None
        self.is_listening: bool = False
        self._thread: Optional[threading.Thread] = None

        if not self.has_audio:
            logger.warning(
                "Voice control disabled. Install 'SpeechRecognition' and "
                "'pyaudio' to enable voice features."
            )

    def on_start(self, **kwargs: Any) -> None:
        """
        Triggered when the application starts.
        Starts the background listener thread.

        Args:
            **kwargs: Event data (ignored by this plugin).
        """
        if self.is_listening:
            logger.debug("Voice listener already running.")
            return

        self.is_listening = True
        self._thread = threading.Thread(
            target=self._background_listener,
            daemon=True,
            name="VoiceListenerThread"
        )
        self._thread.start()
        logger.info("Voice plugin background listener started.")

    def _background_listener(self) -> None:
        """
        Simulation of a background listener loop.
        """
        if not self.has_audio:
            logger.info("Voice plugin active (mock mode). No audio libraries found.")
            self.is_listening = False
            return

        # Hypothetical implementation if SR was available
        # recognizer = sr.Recognizer()
        # with sr.Microphone() as source:
        #     while self.is_listening:
        #         audio = recognizer.listen(source)
        #         # Process audio...
        
        logger.debug("Background listener thread exiting (mock logic).")
        self.is_listening = False
