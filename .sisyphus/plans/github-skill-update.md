# Plan: Enhance GitHub Skill

## Objective
Add `create_issue` capability to the GitHub skill to facilitate easier testing and task management.

## Work Items

- [ ] 1. **Update `github_ops.py`**
    - Add `create_issue(repo_name, title, body)` function.
    - Update `main()` argument parser to include `create_issue` in choices.
    - Wire up the logic.

- [ ] 2. **Update `SKILL.md`**
    - Add usage example for `create_issue`.

## Verification
- Manual test command.
