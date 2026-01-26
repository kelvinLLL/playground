"""
PDF Reader Tool.

Allows AI workers to read content from PDF files (local or URL).
"""

import io
import os
import aiohttp
from typing import Any
from pypdf import PdfReader

from ai_worker.tools.base import BaseTool, ToolResult


class PDFReaderTool(BaseTool):
    """Tool for reading text from PDF files."""

    def __init__(self):
        super().__init__(
            name="read_pdf",
            description="Extract text content from a PDF file provided by URL or local path.",
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Local file path or URL to the PDF file",
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Maximum number of pages to read (default: 20)",
                    "default": 20,
                }
            },
            "required": ["file_path"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("file_path")
        max_pages = kwargs.get("max_pages", 20)

        if not file_path:
            return ToolResult(success=False, data=None, error="Missing file_path")

        try:
            pdf_file = None
            
            # Check if it's a URL
            if file_path.startswith("http://") or file_path.startswith("https://"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(file_path) as response:
                        if response.status != 200:
                            return ToolResult(
                                success=False, 
                                data=None, 
                                error=f"Failed to download PDF: HTTP {response.status}"
                            )
                        content = await response.read()
                        pdf_file = io.BytesIO(content)
            else:
                # Local file
                if not os.path.exists(file_path):
                    return ToolResult(success=False, data=None, error="File not found")
                pdf_file = open(file_path, "rb")

            # Read PDF
            try:
                reader = PdfReader(pdf_file)
                text_content = []
                
                num_pages = len(reader.pages)
                pages_to_read = min(num_pages, max_pages)
                
                for i in range(pages_to_read):
                    page = reader.pages[i]
                    text = page.extract_text()
                    if text:
                        text_content.append(f"--- Page {i+1} ---\n{text}")
                
                full_text = "\n".join(text_content)
                
                if num_pages > max_pages:
                    full_text += f"\n\n[Warning: Only read first {max_pages} pages of {num_pages}]"
                
                return ToolResult(
                    success=True,
                    data=full_text
                )
                
            finally:
                if pdf_file and not isinstance(pdf_file, io.BytesIO):
                    pdf_file.close()

        except Exception as e:
            return ToolResult(success=False, data=None, error=f"PDF reading failed: {str(e)}")
