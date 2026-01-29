# Local Script Skill System (Claude Code Compatible)

## Overview
This system allows the AI Agent to extend its capabilities using local Python scripts defined by a simple Markdown file. This architecture is designed to be fully compatible with the "Claude Code" skill format.

## Directory Structure
All local skills reside in:
`ai_worker/skills/local/`

Each skill consists of two files:
1.  `myskill.md` - The definition (System Prompt injection)
2.  `myskill.py` - The implementation (Executable script)

## The Protocol

### 1. Definition (`*.md`)
This file explains **when** and **how** to use the skill to the LLM.

**Format:**
```markdown
# Skill: [Name]
Description: [Short summary]

## When to use
[Detailed instructions on when this skill is relevant]

## Usage
Run the script with:
`python ai_worker/skills/local/[script_name].py --arg <value>`
```

### 2. Implementation (`*.py`)
A standard, standalone Python script.

**Requirements:**
-   Must be executable via `python script.py`.
-   Should use `argparse` for argument parsing.
-   Must print the result to `stdout` (standard output).
-   Errors should be printed to `stderr` or exit with non-zero code.

**Environment:**
-   The script runs in the **same virtual environment** as the main application.
-   It has access to all installed libraries (`pandas`, `aiohttp`, etc.).
-   It inherits **environment variables** (API Keys, Configs) from the main process.

## Architecture

### The Loader (`LocalScriptSkill`)
-   Scans `skills/local/*.md`.
-   Injects the MD content directly into the Agent's System Prompt.
-   Registers a single bridge tool: `run_local_script`.

### The Bridge (`run_local_script`)
-   **Function**: Safely executes the target python script in a subprocess.
-   **Security**:
    -   Prevents directory traversal (`..`).
    -   Only allows execution of scripts within `skills/local/`.
    -   (Future) Intercepts execution for permission checks.

## Security & Permissions
To maintain compatibility with standard skill files (which lack metadata), permissions are managed **externally** or **implicitly**.

-   **Current State**: All scripts in `skills/local/` are trusted (Safe Mode).
-   **Future State**: A `permissions.yaml` file in the project root will define policies:
    ```yaml
    scripts:
      duckduckgo.py: allow
      delete_db.py: ask_user
    ```

## Example: DuckDuckGo Search
**duckduckgo.md**:
```markdown
# Skill: DuckDuckGo Search
Description: Search the web using DuckDuckGo.

## Usage
`python ai_worker/skills/local/duckduckgo.py --query "search term"`
```

**duckduckgo.py**:
```python
import argparse
from duckduckgo_search import DDGS

if __name__ == "__main__":
    # ... search logic ...
    print(results)
```
