import asyncio
import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.getcwd())

from ai_worker.config import get_settings
from ai_worker.core.message import (
    StandardMessage,
    MessageType,
    Platform,
    User,
    Channel,
)
from ai_worker.llm.openai_client import OpenAIClient
from ai_worker.workers.default import DefaultWorker
from ai_worker.workers.office_worker import OfficeWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PPTX_Experiment")


async def run_experiment():
    settings = get_settings()
    if not settings.openai.api_key:
        logger.error("OpenAI API Key not found!")
        return

    logger.info("🚀 Starting PPTX Comparison Experiment")

    # Force Pro model for better code generation
    settings.openai.model = "antigravity-gemini-3-pro"
    logger.info(f"Using Model: {settings.openai.model}")

    # Initialize LLM
    llm = OpenAIClient(settings.openai)

    # Initialize Workers
    # 1. Office Worker (Specialist)
    office_worker = OfficeWorker(llm)

    # 2. Default Worker (Generalist)
    # We need to give it access to OfficeWorker for routing test?
    # Or just test its direct ability?
    # The experiment is "Generalist vs Specialist".
    # Generalist should try to do it itself using tools (PPTXSkill), NOT delegate.
    # To force this, we won't give it any other workers to delegate to.
    default_worker = DefaultWorker(llm, workers={})

    # Define Test Message
    prompt = (
        "创建一个关于 'Kimi 2.5 模型调研' 的 PPT，包含：核心功能、性能亮点、应用场景。"
        "要求：非常简洁，只需要 1-2 页幻灯片。"
        "请生成 PPT 文件。"
        "注意：所有临时文件请保存在 ai_worker/outputs/pptx/temp_html/ 目录下，最终 PPT 保存在 ai_worker/outputs/pptx/ 目录下。"
    )

    message = StandardMessage(
        id="test_msg_1",
        content=prompt,
        message_type=MessageType.TEXT,
        platform=Platform.DISCORD,
        author=User(id="user1", name="Tester"),
        channel=Channel(id="channel1", name="testing"),
        timestamp=datetime.now(),
    )

    # Define notifier
    async def console_notifier(text: str):
        print(f"   📣 {text}")

    # === Run Experiment A: Office Worker (Specialist) ===
    logger.info("\n🧪 === Experiment A: Office Worker (Specialist) ===")
    start_time = datetime.now()
    try:
        response_a = await office_worker.process(message, notifier=console_notifier)
        logger.info(f"✅ Office Worker Finished:\n{response_a.content}")
    except Exception as e:
        logger.error(f"❌ Office Worker Failed: {e}")
    logger.info(f"⏱️ Duration: {datetime.now() - start_time}")

    # === Run Experiment B: Default Worker (Generalist) ===
    logger.info("\n🧪 === Experiment B: Default Worker (Generalist) ===")
    # Update message ID to avoid caching issues if any
    message.id = "test_msg_2"
    start_time = datetime.now()
    try:
        # DefaultWorker usually needs a nudge to use tools directly if it's chatty.
        # But let's see how it handles the prompt.
        response_b = await default_worker.process(message, notifier=console_notifier)
        logger.info(f"✅ Default Worker Finished:\n{response_b.content}")
    except Exception as e:
        logger.error(f"❌ Default Worker Failed: {e}")
    logger.info(f"⏱️ Duration: {datetime.now() - start_time}")


if __name__ == "__main__":
    asyncio.run(run_experiment())
