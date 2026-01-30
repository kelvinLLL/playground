# Plan: Import Skills

## Objective
Enhance the Agent's capabilities by importing high-quality local skills.

## Work Items

- [ ] 1. **Import `deep-reading-analyst` (Lite Version)**
    - Create directory: `ai_worker/skills/local/deep-reading/`
    - Create `skill.md`: A condensed version of the original, focusing on SCQA and Critical Thinking workflows. Avoid context bloat.
    - Note: This is a "Prompt Skill" (no script).

- [ ] 2. **Create `code-stats` Skill (Demo)**
    - Create directory: `ai_worker/skills/local/code-stats/`
    - Create `skill.md`: Describe usage (Count lines, find TODOs).
    - Create `code_stats.py`: Python script to recursively count lines by extension and find TODOs/FIXMEs.
    - Create `requirements.txt`: (Empty or `pathspec` if needed, but stdlib is fine).

- [ ] 3. **Verification**
    - Check `get_instructions` (Manifest).
    - Run `inspect_skill('deep-reading')`.
    - Run `run_local_script('code-stats/code_stats.py')`.

## Content References
- Deep Reading SKILL.md: (Already fetched in context, will paste during execution)
