# Plan: Implement !workon Command

## Objective
Enable the Agent to clone and switch context to specific GitHub repositories for development tasks.

## Work Items

- [ ] 1. **Settings Update**
    - Define `WORKSPACE_ROOT` in `.env` (default: `workspace`).
    - Ensure directory exists.

- [ ] 2. **Implement `!workon` in `main.py`**
    - Logic:
        - Parse repo name.
        - Construct Clone URL (with Token for private).
        - Run `git clone` or `git pull`.
        - Set `self.active_project` state.
        - Persist to `.env` (`ACTIVE_PROJECT`).

- [ ] 3. **Context Injection**
    - Update `handle_message` to pass `active_project_path` to `DefaultWorker`.
    - Update `DefaultWorker` to append "Active Project: [Path]" to System Prompt.

- [ ] 4. **Safety**
    - Prevent cloning outside workspace.
    - Sanitize repo names.

## Dependencies
- `git` binary.
