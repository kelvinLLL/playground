# Plan: Local Skills Dependency Support

## Context
We have successfully implemented the Folder-based Local Skill system (Claude Code style).
To ensure robustness, we need to handle `requirements.txt` files within skill folders.

## Objective
Update `LocalScriptSkill` to detect and warn about missing dependencies defined in `requirements.txt`.

## Work Items

- [ ] 1. **Update `ai_worker/skills/local_script.py`**
    - Import `importlib.util`
    - Add `_check_requirements(self, md_path)` helper method:
        - Locate `requirements.txt` relative to `skill.md`.
        - Parse simple package names.
        - Check installation using `importlib.util.find_spec`.
        - Return warning string if missing.
    - Update `get_instructions` to call this helper and append warnings to the skill description.

- [ ] 2. **Verification**
    - Create a dummy skill with a `requirements.txt` containing a non-existent package (e.g., `not-a-real-package`).
    - Verify that `get_instructions` output contains the warning.
    - Clean up dummy skill.

## Acceptance Criteria
- [ ] `LocalScriptSkill` scans `requirements.txt` if present.
- [ ] Agent receives a warning in System Prompt if dependencies are missing.
- [ ] No crash if `requirements.txt` is missing or malformed.
