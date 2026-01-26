"""
Research Worker implementation.

Specialized in deep reading and analyzing academic papers/documents.
"""

import logging

from ai_worker.core.message import (
    MessageType,
    StandardMessage,
    StandardResponse,
)
from ai_worker.llm.base import BaseLLM, Message
from ai_worker.workers.base import BaseWorker, WorkerConfig
from ai_worker.tools.pdf_reader import PDFReaderTool

from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ResearchWorker(BaseWorker):
    """
    Academic Researcher.
    
    Responsible for reading papers and generating detailed reports.
    """

    def __init__(self, llm: BaseLLM):
        config = WorkerConfig(
            name="Researcher",
            description="Academic Researcher. Reads papers and generates deep insights.",
            system_prompt=(
                "You are a Senior Academic Researcher. "
                "Your role is to deeply analyze academic papers and technical documents. "
                "When provided with a paper, you must generate a comprehensive report including:\n"
                "1. Abstract Summary\n"
                "2. Key Methodology\n"
                "3. Experiments & Results\n"
                "4. Novelty & Contributions\n"
                "5. Limitations & Future Work\n"
                "Your tone should be objective, critical, and scholarly."
            ),
            tools=["read_pdf"],
        )
        super().__init__(config)
        self.llm = llm
        
        # Register tools
        self.register_tool(PDFReaderTool())

    async def process(
        self, 
        message: StandardMessage, 
        notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        try:
            target_file = None
            
            # 1. Check for attachments
            if message.attachments:
                # Find first PDF
                for att in message.attachments:
                    if att.filename.lower().endswith(".pdf"):
                        target_file = att.url
                        break
            
            # 2. Check for URLs in text if no attachment
            if not target_file and ("http" in message.content):
                words = message.content.split()
                for word in words:
                    clean_word = word.strip("<>\"'")  # Remove common markdown/embed characters
                    
                    # Case A: Explicit PDF link
                    if clean_word.startswith("http") and clean_word.lower().endswith(".pdf"):
                        target_file = clean_word
                        break
                    
                    # Case B: ArXiv Abstract link (convert to PDF)
                    # e.g., https://arxiv.org/abs/1706.03762 -> https://arxiv.org/pdf/1706.03762.pdf
                    if "arxiv.org/abs/" in clean_word:
                        target_file = clean_word.replace("/abs/", "/pdf/")
                        if not target_file.endswith(".pdf"):
                            target_file += ".pdf"
                        break
                    
                    # Case C: ArXiv PDF link without extension
                    if "arxiv.org/pdf/" in clean_word and not clean_word.endswith(".pdf"):
                        target_file = clean_word + ".pdf"
                        break

            if target_file:
                # Inform user we are reading
                if notifier:
                    await notifier(f"📄 Found paper link. Downloading and extracting text...")
                
                tool = self._tools["read_pdf"]
                result = await tool.execute(file_path=target_file)
                
                if result.success:
                    paper_text = result.data
                    
                    # Truncate if too long
                    if len(paper_text) > 100000:
                        paper_text = paper_text[:100000] + "\n\n[Truncated due to length...]"
                    
                    # Generate Report
                    if notifier:
                        est_time = max(30, int(len(paper_text) / 2000))  # Rough estimate: 2000 chars per second (very optimistic) -> actually LLM generation is slower
                        # GPT-4o output speed is ~50-100 tokens/s. 
                        # But input processing is fast. The bottleneck is generation length.
                        # If we ask for a long report (2000 tokens), it takes ~20-40s.
                        # Let's say 45s base + extra for long context.
                        est_time = 60
                        await notifier(f"🧠 Reading {len(paper_text)} characters... analyzing structure and content...\n(This usually takes about {est_time} seconds)")
                    
                    analysis_prompt = (
                        f"Please analyze the following paper content and generate a detailed report:\n\n"
                        f"{paper_text}"
                    )
                    
                    # We use a large max_tokens for the report
                    response = await self.llm.complete(analysis_prompt, max_tokens=2000)
                    response_text = f"**Paper Analysis Report**\n\n{response.content}"
                    
                else:
                    response_text = f"Failed to read PDF: {result.error}"
            
            else:
                # No file found, just chat
                messages = [Message(role="system", content=self.system_prompt)]
                messages.extend([Message(role=m["role"], content=m["content"]) for m in self.get_memory(5)])
                messages.append(Message(role="user", content=message.content))
                
                response = await self.llm.chat(messages)
                response_text = response.content

            # Update memory
            self.add_to_memory("user", message.content)
            self.add_to_memory("assistant", response_text)

            return StandardResponse(
                content=response_text,
                message_type=MessageType.TEXT
            )

        except Exception as e:
            logger.error(f"Error in ResearchWorker: {e}")
            return StandardResponse(content=f"Error: {str(e)}")
