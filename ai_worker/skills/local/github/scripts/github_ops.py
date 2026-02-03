import argparse
import os
import sys
from github import Github, Auth

def get_github_client():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN not found in environment.")
        sys.exit(1)
    auth = Auth.Token(token)
    return Github(auth=auth)

def list_issues(repo_name, state="open", limit=5):
    g = get_github_client()
    try:
        repo = g.get_repo(repo_name)
        issues = repo.get_issues(state=state)
        print(f"### Issues in {repo_name} ({state})")
        count = 0
        for issue in issues:
            if count >= limit: break
            print(f"- **#{issue.number}** {issue.title} (by {issue.user.login})")
            count += 1
        if count == 0:
            print("No issues found.")
    except Exception as e:
        print(f"Error listing issues: {e}")

def get_repo_info(repo_name):
    g = get_github_client()
    try:
        repo = g.get_repo(repo_name)
        print(f"### Repo: {repo.full_name}")
        print(f"- Description: {repo.description}")
        print(f"- Stars: {repo.stargazers_count}")
        print(f"- Language: {repo.language}")
        print(f"- URL: {repo.html_url}")
    except Exception as e:
        print(f"Error getting repo info: {e}")

def create_issue(repo_name, title, body):
    g = get_github_client()
    try:
        repo = g.get_repo(repo_name)
        issue = repo.create_issue(title=title, body=body)
        print(f"✅ Issue Created: {issue.html_url} (#{issue.number})")
    except Exception as e:
        print(f"Error creating issue: {e}")

def create_pr(repo_name, title, body, head, base="main"):
    g = get_github_client()
    try:
        repo = g.get_repo(repo_name)
        pr = repo.create_pull(title=title, body=body, head=head, base=base)
        print(f"✅ PR Created: {pr.html_url}")
    except Exception as e:
        print(f"Error creating PR: {e}")

def main():
    parser = argparse.ArgumentParser(description="GitHub Operations")
    parser.add_argument("--action", required=True, choices=["list_issues", "get_repo", "create_pr", "create_issue"])
    parser.add_argument("--repo", required=True, help="Repository name (owner/repo)")
    
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--state", default="open")
    parser.add_argument("--title")
    parser.add_argument("--body")
    parser.add_argument("--head")
    parser.add_argument("--base", default="main")

    args = parser.parse_args()

    if args.action == "list_issues":
        list_issues(args.repo, args.state, args.limit)
    elif args.action == "get_repo":
        get_repo_info(args.repo)
    elif args.action == "create_issue":
        if not args.title or not args.body:
            print("Error: --title and --body are required for create_issue")
            return
        create_issue(args.repo, args.title, args.body)
    elif args.action == "create_pr":
        if not args.title or not args.body or not args.head:
            print("Error: --title, --body, and --head are required for create_pr")
            return
        create_pr(args.repo, args.title, args.body, args.head, args.base)

if __name__ == "__main__":
    main()
