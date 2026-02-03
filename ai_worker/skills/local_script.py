import glob
import os
import subprocess
import sys
import logging
import importlib.util
from typing import List, Optional, Dict, Any

from ai_worker.skills.base import BaseSkill, SkillMetadata, SkillRegistry
from ai_worker.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

class RunLocalScriptTool(BaseTool):
    name = "run_local_script"
    description = "Execute a local python script from the skills/local directory"
    parameters = {
        "type": "object",
        "properties": {
            "script_name": {
                "type": "string",
                "description": "Name of the script file to run (e.g. 'analyze_csv.py')"
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of command line arguments to pass to the script"
            }
        },
        "required": ["script_name"]
    }

    def __init__(self, script_dir: str):
        super().__init__(self.name, self.description)
        self.script_dir = script_dir

    def _check_permission(self, script_name: str) -> bool:
        """
        Check if the script is allowed to run.
        
        Architecture Hook for Future Security:
        - Currently returns True (Safe Mode).
        - In the future, this can:
          1. Check a config whitelist.
          2. Check MD frontmatter for 'permission: sensitive'.
          3. Request interactive user approval.
        """
        # TODO: Implement granular permissions (whitelist/interactive)
        return True

    async def execute(self, script_name: str, args: List[str] = None) -> ToolResult:
        if args is None:
            args = []
            
        # Security check: prevent directory traversal
        # Allow internal '/' for subdirectories (e.g. 'my_skill/script.py')
        # BUT strictly ban '..' and absolute paths
        if ".." in script_name or script_name.startswith("/") or script_name.startswith("\\"):
            return ToolResult(success=False, data=None, error="Invalid script name. Cannot contain '..' or start with '/'")
        
        if not self._check_permission(script_name):
            return ToolResult(success=False, data=None, error=f"Permission denied: Script '{script_name}' is not approved for execution.")

        if not script_name.endswith(".py"):
            script_name += ".py"
            
        script_path = os.path.join(self.script_dir, script_name)
        
        if not os.path.exists(script_path):
            return ToolResult(success=False, data=None, error=f"Script '{script_name}' not found in local skills directory ({self.script_dir}).")
        
        # Construct command
        # Inherits os.environ by default, ensuring API keys (OPENAI_API_KEY, TAVILY_API_KEY) are available
        cmd = [sys.executable, script_path] + args
        
        try:
            logger.info(f"Running script: {cmd}")
            # Run with timeout of 60 seconds
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60,
                cwd=os.getcwd() # Run from project root
            )
            
            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    data={
                        "output": result.stdout,
                        "stderr": result.stderr,
                        "status": "success"
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Script failed with code {result.returncode}\nStdout: {result.stdout}\nStderr: {result.stderr}"
                )
                
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, data=None, error="Script execution timed out (limit: 60s)")
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"Execution failed: {str(e)}")


class InspectSkillTool(BaseTool):
    name = "inspect_skill"
    description = "Read the full documentation and usage instructions for a specific local skill."
    parameters = {
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "Name of the skill to inspect (e.g. 'duckduckgo')"
            }
        },
        "required": ["skill_name"]
    }

    def __init__(self, script_dir: str):
        super().__init__(self.name, self.description)
        self.script_dir = script_dir

    async def execute(self, skill_name: str) -> ToolResult:
        # Security check
        if ".." in skill_name or skill_name.startswith("/") or "\\" in skill_name:
            return ToolResult(success=False, data=None, error="Invalid skill name.")
            
        # Determine path (support both folder and flat file conventions)
        # Priority 1: Folder (skills/local/skill_name/*.md)
        folder_path = os.path.join(self.script_dir, skill_name)
        
        content = []
        found = False
        
        if os.path.isdir(folder_path):
            # It's a folder, read all MD files
            md_files = glob.glob(os.path.join(folder_path, "*.md"))
            md_files.sort()
            
            if md_files:
                found = True
                for md_file in md_files:
                    try:
                        filename = os.path.basename(md_file)
                        with open(md_file, "r") as f:
                            file_content = f.read().strip()
                        content.append(f"\n### File: {filename}\n{file_content}\n")
                    except Exception as e:
                        content.append(f"Error reading {md_file}: {e}")
        
        if not found:
            # Priority 2: Flat file (skills/local/skill_name.md)
            file_path = os.path.join(self.script_dir, f"{skill_name}.md")
            if os.path.exists(file_path):
                found = True
                try:
                    with open(file_path, "r") as f:
                        file_content = f.read().strip()
                    content.append(f"\n### File: {skill_name}.md\n{file_content}\n")
                except Exception as e:
                    return ToolResult(success=False, data=None, error=f"Error reading file: {e}")

        if not found:
            return ToolResult(success=False, data=None, error=f"Skill '{skill_name}' not found.")
            
        return ToolResult(success=True, data="\n".join(content))


@SkillRegistry.register
class LocalScriptSkill(BaseSkill):
    """
    Loader for local script-based skills (Claude Code style).
    
    Dynamically loads:
    - Definitions from *.md files
    - Implementations from *.py files
    """
    
    def __init__(self):
        self.local_dir = os.path.join(os.path.dirname(__file__), "local")
        self._tools: Optional[List[BaseTool]] = None
        
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="LocalScripts",
            description="Execute custom local scripts defined in skills/local/",
            category="Utility",
            emoji="🛠️",
            trigger_phrases=["run script", "execute local", "custom tool"]
        )
        
    def get_tools(self) -> List[BaseTool]:
        if self._tools is None:
            self._tools = [
                RunLocalScriptTool(self.local_dir),
                InspectSkillTool(self.local_dir)
            ]
        return self._tools

    def _check_requirements(self, md_path: str) -> Optional[str]:
        """Check for requirements.txt and verify installation."""
        req_path = os.path.join(os.path.dirname(md_path), "requirements.txt")
        if not os.path.exists(req_path):
            return None
            
        missing = []
        try:
            with open(req_path, "r") as f:
                requirements = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Extract package name
                        pkg = line.split("=")[0].split(">")[0].split("<")[0].strip()
                        requirements.append(pkg)
                
            for req in requirements:
                # Basic normalization: standard PyPI packages usually map '-' to '_' in imports
                import_name = req.replace("-", "_")
                if not importlib.util.find_spec(import_name):
                    # Try original name just in case
                    if not importlib.util.find_spec(req):
                        missing.append(req)
        except Exception as e:
            logger.warning(f"Error checking requirements for {md_path}: {e}")
            
        if missing:
            return f"\n\n⚠️ **WARNING**: Missing Python dependencies: {', '.join(missing)}. Scripts may fail."
        return None

    def _scan_skills(self) -> Dict[str, str]:
        """Scan local directory for available skills and descriptions."""
        skills_map = {}
        all_md = glob.glob(os.path.join(self.local_dir, "**/*.md"), recursive=True)
        
        for md_file in sorted(all_md):
            rel_path = os.path.relpath(md_file, self.local_dir)
            parts = rel_path.split(os.sep)
            
            skill_name = None
            is_entry_point = False
            
            # Case 1: Folder/skill.md or Folder/README.md
            if len(parts) >= 2 and parts[-1].lower() in ["skill.md", "readme.md"]:
                skill_name = parts[-2]
                is_entry_point = True
            # Case 2: Top-level file (myskill.md)
            elif len(parts) == 1:
                skill_name = os.path.splitext(parts[0])[0]
                is_entry_point = True
                
            if is_entry_point and skill_name and skill_name not in skills_map:
                desc = self._extract_description(md_file)
                req_warning = self._check_requirements(md_file)
                if req_warning:
                    desc += f" {req_warning}"
                skills_map[skill_name] = desc
        return skills_map

    def get_instructions(self) -> str:
        """
        Dynamically build instructions from local skills (Manifest Only).
        Only lists available skills. LLM must use `inspect_skill` to get full docs.
        """
        instructions = ["### Local Custom Skills\n"]
        instructions.append("You have access to the following local skills.\n")
        instructions.append("⚠️ **IMPORTANT**: To use a skill, you MUST first call `inspect_skill(skill_name)` to read its manual.\n")
        
        skills_map = self._scan_skills()
        
        if not skills_map:
            instructions.append("(No local skills found)")
            return "\n".join(instructions)
            
        for name, desc in sorted(skills_map.items()):
            instructions.append(f"- **{name}**: {desc}")
            
        return "\n".join(instructions)
            
        for name, desc in sorted(skills_map.items()):
            instructions.append(f"- **{name}**: {desc}")
            
        return "\n".join(instructions)

    def _extract_description(self, file_path: str) -> str:
        """Extract a short description from the skill file."""
        try:
            with open(file_path, "r") as f:
                # Read first 20 lines max
                for _ in range(20):
                    line = f.readline().strip()
                    if not line: continue
                    # Check explicit description field
                    if line.lower().startswith("description:"):
                        return line.split(":", 1)[1].strip()
                    # Check first paragraph (not header, not frontmatter delimiters)
                    if not line.startswith("#") and not line.startswith("---") and not line.startswith("name:"):
                        return line[:150] + ("..." if len(line) > 150 else "")
            return "No description available."
        except Exception:
            return "Error reading description."
