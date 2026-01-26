"""
Test LLM connection independently.
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_worker.config import get_settings
from ai_worker.llm.openai_client import OpenAIClient
from ai_worker.llm.base import Message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_llm():
    print("=== Testing LLM Connection ===")
    
    # 1. Load Settings
    settings = get_settings()
    print(f"Base URL: {settings.openai.base_url}")
    print(f"Model: {settings.openai.model}")
    print(f"API Key: {settings.openai.api_key[:5]}... (masked)")
    
    # 2. Initialize Client
    client = OpenAIClient(settings.openai)
    
    # 3. Send Request
    messages = [Message(role="user", content="Hello! Who are you and what model are you running on?")]
    
    print("\nSending request...")
    try:
        response = await client.chat(messages)
        print(f"\n✅ Success! Response:\n{response.content}")
        print(f"\nModel used: {response.model}")
        print(f"Usage: {response.usage}")
    except Exception as e:
        print(f"\n❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
