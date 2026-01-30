# Plan: Local Skills Lazy Loading

## Objective
Prevent Context Window Bloat by only loading Skill Manifests (Name/Desc) into System Prompt. Full instructions are loaded on-demand via a new `inspect_skill` tool.

## Work Items

- [ ] 1. **Create `InspectSkillTool` in `local_script.py`**
    - Input: `skill_name` (e.g. "duckduckgo")
    - Logic:
        - Resolve path: `skills/local/{skill_name}/*.md`
        - Read all MD files in that folder.
        - Return combined content.
    - Security: Prevent directory traversal.

- [ ] 2. **Refactor `LocalScriptSkill.get_instructions`**
    - OLD: Cat `content = f.read()` for all files.
    - NEW:
        - Iterate `skill.md` files.
        - Parse Frontmatter (if exists) or Regex capture Description.
        - Build a summary list: `- **{name}**: {description}`.
        - Add instruction: "Use `inspect_skill` to learn how to use these."

- [ ] 3. **Register Tool**
    - Add `InspectSkillTool(self.local_dir)` to `get_tools()`.

## Verification
1. `get_instructions` should be short (Manifest only).
2. `inspect_skill('duckduckgo')` should return full MD with usage.
3. `run_local_script` remains unchanged.
