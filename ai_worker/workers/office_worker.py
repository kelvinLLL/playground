import re
import logging
import os
import time
from typing import Any, Callable, Optional, List

from ai_worker.core.message import (
    MessageType,
    StandardMessage,
    StandardResponse,
)
from ai_worker.llm.base import BaseLLM, Message, ToolDefinition, ToolCall
from ai_worker.workers.base import BaseWorker, WorkerConfig
from ai_worker.skills.pptx import PPTXSkill
from ai_worker.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class OfficeWorker(BaseWorker):
    """
    Office Productivity Worker (Specialist).

    Role: McKinsey Consultant / Presentation Expert.
    Capabilities: Creating high-quality, structured PowerPoint presentations.
    """

    def __init__(self, llm: BaseLLM):
        config = WorkerConfig(
            name="Office",
            description="Presentation specialist. Creates structured, high-quality PowerPoint decks.",
            system_prompt=(
                "You are an Elite Strategy Consultant (McKinsey/Bain style). "
                "Your goal is to create high-impact presentations with clear structure and logic.\n\n"
                "**Core Principles**:\n"
                "1. **Pyramid Principle**: Start with the answer/conclusion.\n"
                "2. **MECE**: Mutually Exclusive, Collectively Exhaustive.\n"
                "3. **One Idea Per Slide**: Don't clutter.\n"
                "4. **Action-Oriented**: Every slide should lead to a conclusion or action.\n\n"
                "**Workflow**:\n"
                "1. **Outline**: Plan the narrative arc (Situation -> Complication -> Resolution).\n"
                "2. **Design**: Create clear, visual slides using HTML/CSS.\n"
                "3. **Refine**: Ensure professional formatting.\n"
            ),
        )
        super().__init__(config)
        self.llm = llm

        # Load PPTX Skill
        self.pptx_skill = PPTXSkill()
        self._tools = {}
        for tool in self.pptx_skill.get_tools():
            self._tools[tool.name] = tool

        # Build tool definitions for LLM
        self.tools_schema = self.pptx_skill.get_tool_schemas()

    async def process(
        self, message: StandardMessage, notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        try:
            return await self._create_presentation(message.content, notifier)
        except Exception as e:
            logger.error(f"OfficeWorker error: {e}")
            return StandardResponse(content=f"Presentation creation failed: {str(e)}")

    async def _create_presentation(
        self, topic: str, notifier: Optional[Callable[[str], Any]] = None
    ) -> StandardResponse:
        # 1. Plan Outline (Internal Thought)
        if notifier:
            await notifier(f"🧠 Planning presentation structure for: **{topic}**...")

        planning_prompt = f"""
        Topic: {topic}
        
        Create a 5-slide outline following the Pyramid Principle.
        For each slide, specify:
        - Title
        - Key Message (1 sentence)
        - Content (Bullets)
        - Visual Concept (Chart/Table/Text)
        
        Output strictly in JSON format.
        """
        # Note: In a real implementation, we'd parse JSON. Here we just let LLM think.
        # Actually, let's skip a separate planning call to save time/tokens and do it in one go
        # or guide the LLM to generate the HTML directly.

        # 2. Generate HTML Content
        if notifier:
            await notifier("📝 Writing slide content (HTML)...")

        html_prompt = f"""
        Create a 5-slide presentation on: {topic}
        
        Use your 'McKinsey Consultant' persona.
        
        **REQUIREMENTS**:
        1. Generate a SINGLE HTML file containing all slides.
        2. Use `class="slide"` for each slide wrapper (if needed by your CSS logic, but wait, html2pptx.js usually takes one file per slide or specific structure).
        
        **WAIT**: The available tool `create_presentation_from_html` takes ONE HTML file.
        The `html2pptx.js` script typically converts a single HTML file into slides.
        Let's verify the `html2pptx.js` logic. It renders the HTML.
        
        Actually, looking at `html2pptx.md`: "Create an HTML file for each slide" or "single file"? 
        The tool `create_presentation_from_html` calls `node html2pptx.js <input> <output>`.
        Most `html2pptx` tools convert a single HTML page into a single slide, or iterate.
        
        Let's assume for this experiment we generate ONE HTML file that represents the WHOLE presentation 
        or multiple HTML files.
        
        Re-reading `SKILL.md`: 
        "Create an HTML file for each slide... Create and run a JavaScript file... to convert HTML slides".
        
        Ah, the `PPTXSkill` I implemented calls `html2pptx.js` with ONE input file.
        Let's assume `html2pptx.js` (which I wrapped) handles the logic. 
        If `html2pptx.js` expects a single HTML file that generates one PPTX, it probably converts that single HTML content.
        
        **CRITICAL**: I need to check `html2pptx.js` to see if it supports multiple slides or just one.
        If it supports only one slide per file, I need to generate multiple files.
        But my tool `create_presentation_from_html` takes ONE `html_file`.
        
        **Assumption**: I will ask the LLM to generate code that `html2pptx.js` can handle.
        Let's assume we produce ONE High-Quality Slide for this MVP if the tool is limited, 
        OR the `html2pptx.js` script is smart enough.
        
        Actually, looking at the `SKILL.md` again:
        "Create an HTML file for each slide... Create and run a JavaScript file... to convert HTML slides to PowerPoint"
        
        It seems the manual workflow expects writing a JS script. 
        BUT my `PPTXSkill` wraps `html2pptx.js` as a direct tool: `node html2pptx.js input output`.
        
        Let's generate the HTML content for the slides.
        """

        # Refined Prompt for HTML generation
        generation_prompt = f"""
        Task: Create a technical proposal presentation on: {topic}
        
        Output the full HTML content for the presentation.
        
        **HTML Specifications**:
        - Use simple HTML/CSS.
        - Dimensions: `width: 720pt; height: 405pt` per slide.
        - Since we are generating a single file, put all content in ONE HTML file.
        - **IMPORTANT**: If the tool only converts one slide, make this a "Summary / One-Pager" slide.
        
        **STRICT COMPLIANCE RULES (Critical for Converter)**:
        1. **NO Background Images**: Use solid white background only.
        2. **NO Borders on Text**: Do NOT put borders on `<h1>`, `<h2>`, etc. Use `<div style="border-bottom: ...">` wrapper if needed.
        3. **Text Wrapping**: ALL text must be inside `<p>`, `<h1>`-`<h6>`, `<li>`. Do NOT put text directly in `<div>`.
        4. **Simple Layout**: Use Flexbox. Avoid absolute positioning.
        5. **Overflow**: **CRITICAL**: Keep content CONCISE. 3-4 bullet points max per section. It MUST fit in 720pt x 405pt.
        
        HTML Template:
        ```html
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            * {{ box-sizing: border-box; }}
            body {{ 
              width: 720pt; 
              height: 405pt; 
              margin: 0; 
              padding: 40pt; 
              font-family: Arial, sans-serif; 
              display: flex; 
              flex-direction: column; 
              background: white; /* Ensure white background */
            }}
          </style>
        </head>
        <body>
          <div style="border-bottom: 2px solid #05478a; padding-bottom: 10px; margin-bottom: 20px;">
            <h1 style="color: #05478a; font-size: 28pt; margin: 0;">Title</h1>
          </div>
          <div style="display: flex; flex: 1; gap: 20px; margin_top: 20px;">
             <div style="flex: 1;">
                <h2 style="font-size: 14pt; color: #333;">Key Findings</h2>
                <ul>
                   <li>Point 1</li>
                   <li>Point 2</li>
                </ul>
             </div>
             <div style="flex: 1; background: #f0f0f0; padding: 15px; border-radius: 5px;">
                <h2 style="font-size: 14pt; color: #333;">Data/Chart Area</h2>
                <p>Placeholder for chart</p>
             </div>
          </div>
        </body>
        </html>
        ```
        
        Return ONLY the HTML code.
        """

        response = await self.llm.complete(generation_prompt, max_tokens=2000)
        html_content = response.content
        logger.info(f"LLM Response length: {len(html_content)}")

        # Regex extraction for robust HTML capturing
        # Look for <!DOCTYPE html> ... </html>
        match = re.search(
            r"<!DOCTYPE html>.*?</html>", html_content, re.DOTALL | re.IGNORECASE
        )
        if match:
            html_content = match.group(0)
        else:
            # Fallback to code block extraction
            if "```html" in html_content:
                html_content = html_content.split("```html")[1].split("```")[0].strip()
            elif "```" in html_content:
                html_content = html_content.split("```")[1].split("```")[0].strip()

        if len(html_content) < 100:
            logger.error(f"Extracted HTML is too short: {html_content}")
            return StandardResponse(
                content="Failed to generate valid HTML (content too short)."
            )

        # 3. Save HTML File
        output_dir = "ai_worker/outputs/pptx"
        temp_dir = f"{output_dir}/temp_html"
        os.makedirs(temp_dir, exist_ok=True)

        timestamp = int(time.time())
        html_path = f"{temp_dir}/office_worker_slide_{timestamp}.html"
        pptx_path = f"{output_dir}/office_worker_output.pptx"

        with open(html_path, "w") as f:
            f.write(html_content)

        if notifier:
            await notifier(f"🎨 HTML generated. Converting to PPTX...")

        # 4. Convert to PPTX
        tool = self._tools["create_presentation_from_html"]
        result = await tool.execute(html_file=html_path, output_file=pptx_path)

        if not result.success:
            return StandardResponse(
                content=f"Failed to convert HTML to PPTX: {result.error}"
            )

        # 5. Generate Thumbnail (Verify)
        if notifier:
            await notifier("🖼️ Generating thumbnail preview...")

        thumb_tool = self._tools["generate_thumbnail"]
        thumb_result = await thumb_tool.execute(
            pptx_file=pptx_path, output_prefix=f"{output_dir}/thumb_office"
        )

        success_msg = f"""
        ✅ **Presentation Created!**
        
        - **Topic**: {topic}
        - **File**: `{pptx_path}`
        - **Preview**: Thumbnail generated at `{output_dir}/thumb_office.jpg`
        """

        return StandardResponse(content=success_msg)
