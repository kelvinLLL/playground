"""
Test script for AI Workers.
"""

import asyncio
import logging
from ai_worker.config import get_settings
from ai_worker.core.message import StandardMessage, MessageType, Platform, User, Channel
from ai_worker.main import AIWorkerApp

logging.basicConfig(level=logging.INFO)

async def test_workers():
    app = AIWorkerApp()
    app.setup_workers()
    
    # Mock user
    user = User(id="test_user", name="TestUser", platform=Platform.UNKNOWN)
    channel = Channel(id="test_channel", name="TestChannel")
    
    # Test 1: Fetch Data (Intel)
    print("\n=== Test 1: Fetch Data (Intel) ===")
    msg1 = StandardMessage(
        id="1",
        content="Please fetch market data for AAPL from 2023-01-01 to 2023-12-31",
        message_type=MessageType.TEXT,
        author=user,
        channel=channel,
        platform=Platform.UNKNOWN
    )
    # Simulate routing
    if "fetch" in msg1.content.lower():
        response = await app.workers["intel"].process(msg1)
        print(f"Response: {response.content}")

    # Test 2: Run Backtest (Strategy)
    print("\n=== Test 2: Run Backtest (Strategy) ===")
    msg2 = StandardMessage(
        id="2",
        content="Run a backtest for AAPL strategy",
        message_type=MessageType.TEXT,
        author=user,
        channel=channel,
        platform=Platform.UNKNOWN
    )
    if "backtest" in msg2.content.lower():
        response = await app.workers["strategy"].process(msg2)
        print(f"Response: {response.content}")

if __name__ == "__main__":
    asyncio.run(test_workers())
