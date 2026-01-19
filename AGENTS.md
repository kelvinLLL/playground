# AGENT CODING GUIDELINES for simple_quant

This document serves as the canonical source for all agentic coding tasks within the \`simple_quant\` repository. Agents MUST adhere strictly to these guidelines to maintain code quality, consistency, and compatibility.

---

## 1. PROJECT COMMANDS AND VERIFICATION

Since there are no explicit configuration files (e.g., \`setup.cfg\`, \`pyproject.toml\`, or \`requirements.txt\`), the following standard Python commands are assumed. Agents must use these for verification steps.

| Action | Command | Notes |
| :--- | :--- | :--- |
| **Install Dependencies** | \`pip install -r requirements.txt\` | Must be run if new packages are introduced. If \`requirements.txt\` is missing, you may create one. |
| **Full Lint Check** | \`flake8 .\` | Executes a full linting pass across the entire codebase. |
| **Lint Single File** | \`flake8 <path/to/file.py>\` | Faster verification for small, localized changes. |
| **Run All Tests** | \`pytest\` | Runs all discovered tests in the repository. |
| **Run Single Test File** | \`pytest <path/to/test_file.py>\` | Runs all tests within a specific file. |
| **Run Single Test Case** | \`pytest <path/to/test_file.py>::<test_function_name>\` | Runs an isolated test function. |

**Agent Verification Protocol:**
1.  **Before Commit:** Agents must run **Lint Single File** on all modified files and **Run All Tests** if the change impacts core logic or data structures.
2.  **After Feature/Fix:** Agents must ensure all relevant existing tests pass and, if new functionality is added, new tests are created and pass.
3.  **Always use absolute paths for file operations** (Read, Write, Edit) based on the repository root (\`/home/kelvin11888/my_house/playground\`).

---

## 2. CODE STYLE AND CONVENTIONS (PEP 8 Compliant)

All code must strictly adhere to Python's official style guide, PEP 8, unless explicitly overridden below.

### 2.1 Imports

1.  **Grouping:** Imports must be grouped in the following order, with a blank line separating each group:
    *   Standard library imports (e.g., \`os\`, \`sys\`, \`typing\`)
    *   Third-party imports (e.g., \`pandas\`, \`numpy\`)
    *   Local application/library specific imports (e.g., \`from simple_quant.core import ...\`)
2.  **Absolute Imports:** Use absolute imports for local application code (e.g., \`from simple_quant.events import Event\`).
3.  **Wildcard Imports:** Wildcard imports (\`from module import *\`) are forbidden.
4.  **One Import Per Line:** Each import should be on its own line.

**Example Import Order:**
\`\`\`python
# 1. Standard library imports
import sys
from typing import List, Optional

# 2. Third-party imports
import pandas as pd
import numpy as np

# 3. Local application imports
from simple_quant.events import Event
from .base import BaseEngine 
\`\`\`

### 2.2 Formatting and Structure

1.  **Indentation:** Use 4 spaces per indentation level. Tabs are forbidden.
2.  **Line Length:** Lines should not exceed 88 characters. Use black-style formatting.
3.  **Trailing Whitespace:** Forbidden.
4.  **Blank Lines:**
    *   Surround top-level function and class definitions with two blank lines.
    *   Surround method definitions inside classes with a single blank line.
    *   Use one blank line to separate logical sections within functions.

### 2.3 Naming Conventions

| Entity | Convention | Example |
| :--- | :--- | :--- |
| **Modules/Files** | Lowercase with underscores | \`data_handler.py\` |
| **Packages/Directories** | Lowercase without underscores | \`execution\` |
| **Classes** | CapWords (CamelCase) | \`MarketEvent\`, \`BacktestEngine\` |
| **Functions/Methods** | lowercase_with_underscores | \`calculate_pnl\`, \`handle_data\` |
| **Variables** | lowercase_with_underscores | \`current_price\`, \`start_date\` |
| **Constants** | ALL_CAPS_WITH_UNDERSCORES | \`DEFAULT_PORTFOLIO_SIZE\` |
| **Private/Internal** | Prefix with a single underscore | \`_process_event\` |

### 2.4 Typing and Type Hinting

1.  **Mandatory:** All new function signatures and methods must include type hints for parameters and return values.
2.  **Complex Types:** Use the \`typing\` module for complex types (\`List\`, \`Dict\`, \`Optional\`, \`Union\`, etc.).
3.  **Existing Code:** When modifying existing code that lacks type hints, the agent is expected to add hints to the entire modified function/method signature.

### 2.5 Error Handling

1.  **Specific Exceptions:** Agents must raise and catch specific, well-defined exceptions (e.g., \`ValueError\`, \`KeyError\`, \`IOError\`). Catching the generic \`Exception\` is acceptable only as a last resort in top-level execution/logging wrappers.
2.  **Logging:** Use the Python standard \`logging\` module for all operational messages. Avoid using \`print()\` for debugging or status updates in production code.
3.  **Custom Exceptions:** When a change introduces a new type of error, a custom exception class (e.g., \`class MissingDataError(Exception): pass\`) should be defined in a relevant module.

### 2.6 Docstrings and Comments

1.  **Docstrings:** All public classes, methods, and functions **must** have docstrings using the **Google** style (preferred) or **Numpy** style.
2.  **Comments:** Comments should explain *why* code is written, not *what* it does. Use sparingly. Complex or non-obvious logic requires a comment.

---
**END OF AGENTS.MD**
