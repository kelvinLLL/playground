"""
Test script for monitor.py logic.
Simulates log updates to verify the watcher triggers the sound plugin.
"""

import os
import time
import threading
import logging
import sys
from unittest.mock import MagicMock

# Add path to import monitor
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from opencode_extensions.monitor import LogWatcher
from opencode_extensions.plugins.sound import SoundPlugin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestMonitor")

def test_log_watcher():
    log_file = "test_ai_worker.log"
    
    # 1. Create a dummy log file
    with open(log_file, "w") as f:
        f.write("2026-01-26 10:00:00 [INFO] Startup\n")
    
    # 2. Mock the SoundPlugin
    mock_sound = MagicMock(spec=SoundPlugin)
    
    # 3. Start the watcher
    watcher = LogWatcher(log_file, mock_sound)
    
    # Use a thread so we can write to the file while it watches
    t = threading.Thread(target=watcher.start, daemon=True)
    t.start()
    
    logger.info("Watcher started. Sleeping 2s to let it initialize...")
    time.sleep(2)
    
    # 4. Simulate a log update matching the pattern
    logger.info("Simulating log update...")
    with open(log_file, "a") as f:
        # The pattern in monitor.py is: r"HTTP Request: POST .*completions.* 200 OK"
        f.write("2026-01-26 10:00:05 [INFO] httpx: HTTP Request: POST http://127.0.0.1:8045/v1/chat/completions \"HTTP/1.1 200 OK\"\n")
        f.flush()
    
    # 5. Wait for detection
    logger.info("Waiting for detection...")
    time.sleep(2)
    
    # 6. Verify
    watcher.stop()
    if mock_sound.on_finish.called:
        logger.info("SUCCESS: Sound plugin triggered!")
    else:
        logger.error("FAILURE: Sound plugin was NOT triggered.")
        sys.exit(1)

    # Cleanup
    if os.path.exists(log_file):
        os.remove(log_file)

if __name__ == "__main__":
    test_log_watcher()
