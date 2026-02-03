---
name: github
description: Interact with GitHub repositories (Issues, PRs, Info). For local development (Clone/Edit), use the `!workon <repo>` command first to set context.
---

# GitHub Operations

Use this skill to perform operations on GitHub repositories using the configured credentials.

## Usage

Run the `scripts/github_ops.py` script using `run_local_script` with the appropriate arguments.

### List Issues
To list open issues in a repository:

```python
run_local_script(
    script_name="github/scripts/github_ops.py",
    args=["--action", "list_issues", "--repo", "owner/repo", "--limit", "5"]
)
```

### Get Repository Info
To get details about a repository (stars, description):

```python
run_local_script(
    script_name="github/scripts/github_ops.py",
    args=["--action", "get_repo", "--repo", "owner/repo"]
)
```

### Create Issue
To create a new Issue:

```python
run_local_script(
    script_name="github/scripts/github_ops.py",
    args=[
        "--action", "create_issue",
        "--repo", "owner/repo",
        "--title", "Issue Title",
        "--body", "Description of the issue"
    ]
)
```

### Create Pull Request
To create a new Pull Request:

```python
run_local_script(
    script_name="github/scripts/github_ops.py",
    args=[
        "--action", "create_pr",
        "--repo", "owner/repo",
        "--title", "PR Title",
        "--body", "Description of changes",
        "--head", "feature-branch",
        "--base", "main"
    ]
)
```

## Setup Requirements
This skill requires the `GITHUB_TOKEN` environment variable to be set in `.env`.
