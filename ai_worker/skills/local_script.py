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
            self._tools = [RunLocalScriptTool(self.local_dir)]
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
                        # Extract package name (ignore version constraints for simple check)
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

    def get_instructions(self) -> str:
        """
        Dynamically build instructions from all .md files in skills/local/
        Supports:
        - Flat files: skills/local/myskill.md
        - Folders: skills/local/myskill/skill.md (or README.md)
        """
        instructions = ["### Local Custom Skills\n"]
        instructions.append("You have access to the following local scripts via `run_local_script`:\n")
        
        # Recursive scan for .md files
        # Note: glob(recursive=True) requires ** pattern
        md_files = glob.glob(os.path.join(self.local_dir, "**/*.md"), recursive=True)
        
        if not md_files:
            instructions.append("(No local skills found)")
            return "\n".join(instructions)
            
        for md_file in sorted(md_files):
            try:
                # Calculate relative path for display/logic
                rel_path = os.path.relpath(md_file, self.local_dir)
                filename = os.path.basename(md_file)
                
                with open(md_file, "r") as f:
                    content = f.read().strip()
                
                # Check for dependencies
                req_warning = self._check_requirements(md_file)
                if req_warning:
                    content += req_warning
                    
                instructions.append(f"\n#### {rel_path}")
                instructions.append(content)
                instructions.append("-" * 30)
                
            except Exception as e:
                logger.warning(f"Failed to load local skill {md_file}: {e}")
                
        return "\n".join(instructions)
