import sys
import os
import subprocess
import logging
import json
from typing import List, Dict, Any, Optional

from ai_worker.skills.base import BaseSkill, SkillMetadata, SkillRegistry
from ai_worker.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class CreatePresentationFromHtmlTool(BaseTool):
    name = "create_presentation_from_html"
    description = "Create a PowerPoint presentation from HTML files using html2pptx.js"
    parameters = {
        "type": "object",
        "properties": {
            "html_file": {
                "type": "string",
                "description": "Path to the source HTML file",
            },
            "output_file": {
                "type": "string",
                "description": "Path where the output .pptx file should be saved",
            },
        },
        "required": ["html_file", "output_file"],
    }

    def __init__(self, script_path: str):
        super().__init__(self.name, self.description)
        self.script_path = script_path

    async def execute(self, html_file: str, output_file: str) -> ToolResult:
        # Resolve absolute paths
        if not os.path.isabs(html_file):
            html_file = os.path.abspath(html_file)
        if not os.path.isabs(output_file):
            output_file = os.path.abspath(output_file)

        if not os.path.exists(html_file):
            return ToolResult(
                success=False, data=None, error=f"HTML file not found: {html_file}"
            )

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        cmd = ["node", self.script_path, html_file, output_file]

        try:
            logger.info(f"Running html2pptx: {cmd}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # Allow time for rendering
                cwd=os.getcwd(),
            )

            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    data={
                        "output_file": output_file,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"html2pptx failed (code {result.returncode}):\nStdout: {result.stdout}\nStderr: {result.stderr}",
                )
        except Exception as e:
            return ToolResult(
                success=False, data=None, error=f"Execution error: {str(e)}"
            )


class GenerateThumbnailTool(BaseTool):
    name = "generate_thumbnail"
    description = "Generate a thumbnail grid image for a PowerPoint presentation"
    parameters = {
        "type": "object",
        "properties": {
            "pptx_file": {
                "type": "string",
                "description": "Path to the source .pptx file",
            },
            "output_prefix": {
                "type": "string",
                "description": "Prefix for output image (e.g. 'thumbnails')",
            },
            "cols": {
                "type": "integer",
                "description": "Number of columns in grid (default: 5)",
                "default": 5,
            },
        },
        "required": ["pptx_file", "output_prefix"],
    }

    def __init__(self, script_path: str):
        super().__init__(self.name, self.description)
        self.script_path = script_path

    async def execute(
        self, pptx_file: str, output_prefix: str, cols: int = 5
    ) -> ToolResult:
        # Resolve absolute paths
        if not os.path.isabs(pptx_file):
            pptx_file = os.path.abspath(pptx_file)
        # output_prefix might be a path prefix
        if not os.path.isabs(output_prefix):
            output_prefix = os.path.abspath(output_prefix)

        if not os.path.exists(pptx_file):
            return ToolResult(
                success=False, data=None, error=f"PPTX file not found: {pptx_file}"
            )

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_prefix), exist_ok=True)

        cmd = [
            sys.executable,
            self.script_path,
            pptx_file,
            output_prefix,
            "--cols",
            str(cols),
        ]

        try:
            logger.info(f"Running thumbnail generation: {cmd}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, cwd=os.getcwd()
            )

            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    data={
                        "output_prefix": output_prefix,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Thumbnail generation failed (code {result.returncode}):\nStdout: {result.stdout}\nStderr: {result.stderr}",
                )
        except Exception as e:
            return ToolResult(
                success=False, data=None, error=f"Execution error: {str(e)}"
            )


@SkillRegistry.register
class PPTXSkill(BaseSkill):
    """
    Skill for creating and manipulating PowerPoint presentations.
    Wraps local scripts for html2pptx and thumbnail generation.
    """

    def __init__(self):
        self.base_dir = os.path.join(
            os.path.dirname(__file__), "local", "pptx", "scripts"
        )
        self.html2pptx_script = os.path.join(self.base_dir, "cli_html2pptx.js")
        self.thumbnail_script = os.path.join(self.base_dir, "thumbnail.py")
        self._tools = None

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="PPTX",
            description="Create, edit, and analyze PowerPoint presentations. Can convert HTML slides to PPTX.",
            category="Creative",
            emoji="📊",
            trigger_phrases=[
                "create ppt",
                "make presentation",
                "generate slides",
                "powerpoint",
            ],
        )

    def get_tools(self) -> List[BaseTool]:
        if self._tools is None:
            self._tools = [
                CreatePresentationFromHtmlTool(self.html2pptx_script),
                GenerateThumbnailTool(self.thumbnail_script),
            ]
        return self._tools

    def get_instructions(self) -> str:
        return """
### PPTX Creation Workflow (HTML to PPTX)

1. **Design Principles**:
   - Use web-safe fonts: Arial, Helvetica, Times New Roman, Georgia, Verdana.
   - Use simple HTML structure: `<body>`, `<h1>`, `<p>`, `<ul>`/`<ol>`, `<div>`.
   - **Critical**: `<body>` must have inline styles for dimensions: `width: 720pt; height: 405pt;` (for 16:9).
   - Use flexbox for layout.
   - **Images**: Must be local paths.
   - **Charts**: Use `class="placeholder"` divs to reserve space.

2. **Creation Process**:
   - Create HTML file(s) for slides.
   - Use `create_presentation_from_html` tool to convert HTML to .pptx.
   - Use `generate_thumbnail` tool to verify the visual layout.

3. **Example HTML**:
   ```html
   <!DOCTYPE html>
   <html>
   <body style="width: 720pt; height: 405pt; margin: 0; padding: 40pt; font-family: Arial, sans-serif;">
     <h1 style="color: #333;">Slide Title</h1>
     <ul>
       <li>Bullet point 1</li>
       <li>Bullet point 2</li>
     </ul>
   </body>
   </html>
   ```
"""
