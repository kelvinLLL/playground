"""
External Monitor for OpenCode.
Run this script in a separate terminal window to:
1. Play a sound when OpenCode finishes a task (by watching logs).
2. Enable Voice Input (copies recognized text to clipboard).
"""

import time
import os
import sys
import logging
import re
import threading
from typing import Optional

# Add current directory to path to import plugins
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plugins.sound import SoundPlugin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Monitor: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None


class LogWatcher:
    """Watches a log file for specific patterns."""

    def __init__(self, log_path: str, sound_plugin: SoundPlugin):
        self.log_path = log_path
        self.sound_plugin = sound_plugin
        self.last_position = 0
        self.running = False
        
        # Pattern to detect task completion (LLM response success)
        # Adjust this regex based on your actual log format
        self.completion_pattern = re.compile(r"HTTP Request: POST .*completions.* 200 OK")

    def start(self):
        """Starts the log watcher loop."""
        if not os.path.exists(self.log_path):
            logger.error(f"Log file not found: {self.log_path}")
            return

        logger.info(f"Watching log file: {self.log_path}")
        
        # Seek to end of file initially
        with open(self.log_path, 'r') as f:
            f.seek(0, 2)
            self.last_position = f.tell()

        self.running = True
        self._loop()

    def _loop(self):
        while self.running:
            try:
                with open(self.log_path, 'r') as f:
                    f.seek(self.last_position)
                    lines = f.readlines()
                    self.last_position = f.tell()

                    if lines:
                        for line in lines:
                            if self.completion_pattern.search(line):
                                logger.info("Detected Task Completion!")
                                self.sound_plugin.on_finish()
            except FileNotFoundError:
                # Log rotation or file missing
                pass
            except Exception as e:
                logger.error(f"Error reading log: {e}")

            time.sleep(1)

    def stop(self):
        self.running = False


class VoiceListener:
    """Listens for voice and copies text to clipboard."""

    def __init__(self):
        self.recognizer = sr.Recognizer() if sr else None
        self.microphone = sr.Microphone() if sr else None
        self.running = False

    def start(self):
        if not sr or not pyperclip:
            logger.warning("Voice/Clipboard features disabled. Install 'SpeechRecognition', 'pyaudio', and 'pyperclip'.")
            return

        logger.info("Voice Listener active. Say something...")
        self.running = True
        
        # Run in a separate thread to not block log watcher
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
            while self.running:
                try:
                    # Listen for a short phrase
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    logger.info("Processing audio...")
                    
                    text = self.recognizer.recognize_google(audio)
                    if text:
                        logger.info(f"Recognized: '{text}'")
                        pyperclip.copy(text)
                        logger.info("Copied to clipboard!")
                        # Optional: Play a subtle sound to confirm copy
                        
                except sr.WaitTimeoutError:
                    pass  # No speech detected, continue listening
                except sr.UnknownValueError:
                    pass  # Could not understand audio
                except Exception as e:
                    logger.error(f"Voice error: {e}")


def find_latest_log(search_dir: str) -> Optional[str]:
    """Finds the most recently modified .log file in the directory."""
    logs = []
    try:
        for root, _, files in os.walk(search_dir):
            for file in files:
                if file.endswith(".log"):
                    full_path = os.path.join(root, file)
                    logs.append((full_path, os.path.getmtime(full_path)))
    except Exception as e:
        logger.error(f"Error searching logs: {e}")
        return None

    if not logs:
        return None

    # Sort by modification time, newest first
    logs.sort(key=lambda x: x[1], reverse=True)
    return logs[0][0]


def main():
    # 1. Setup Plugins
    sound = SoundPlugin()
    
    # 2. Find Log File
    # Search in parent directory (assuming opencode_extensions is inside project)
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    log_file = find_latest_log(parent_dir)
    
    if not log_file:
        logger.warning("No log files found. Sound notifications will not work.")
        # Create a dummy watcher if needed, or just skip
    
    # 3. Start Watcher
    watcher = None
    if log_file:
        watcher = LogWatcher(log_file, sound)
        watcher_thread = threading.Thread(target=watcher.start, daemon=True)
        watcher_thread.start()

    # 4. Start Voice Listener
    voice = VoiceListener()
    voice.start()

    # Keep main thread alive
    logger.info("Monitor running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping...")
        if watcher:
            watcher.stop()


if __name__ == "__main__":
    main()
