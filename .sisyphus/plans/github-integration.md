# Plan: GitHub Integration

## Objective
Enable the AI Worker to interact with GitHub (Clone, PR, Issues) to support "ChatOps".

## Prerequisites
- `GITHUB_TOKEN` in `.env`.

## Work Items

- [ ] 1. **Dependencies**
    - Update `ai_worker/pyproject.toml` to include `PyGithub`.
    - Install dependency.

- [ ] 2. **GitHub Local Skill (`ai_worker/skills/local/github/`)**
    - `skill.md`: Instructions.
    - `github_ops.py`: A swiss-army knife script using PyGithub.
        - `list-repos`
        - `create-pr`
        - `get-issue`
        - `comment`

- [ ] 3. **Verification**
    - Run `python github_ops.py --action list-repos` to verify auth.

## Future (Phase 2)
- `!workon` command in `main.py` (Cloning logic).
