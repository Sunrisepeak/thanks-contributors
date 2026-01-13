"""Git helpers for change detection, auto-commits, and PR management."""

from __future__ import annotations

import os
import subprocess
import json
import urllib.request
import urllib.error
from typing import Iterable, Optional
from datetime import datetime

from config import get_tracked_files


def _run_git(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=False
    )


def _is_github_actions() -> bool:
    """Check if running in GitHub Actions environment."""
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def write_github_output(key: str, value: str) -> bool:
    """Append a key=value line to $GITHUB_OUTPUT if available."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return False
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")
    return True


def _get_github_api(url: str, method: str = "GET", data: Optional[dict] = None) -> dict:
    """Make GitHub API requests."""
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("Missing GH_TOKEN environment variable")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "thanks-contributors-action"
    }
    
    request_data = None
    if data:
        request_data = json.dumps(data).encode("utf-8")
    
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error ({e.code}): {error_body}")


def _get_base_branch() -> str:
    """Resolve target base branch for PR creation.

    Order of precedence:
    1) Explicit env overrides: BASE_BRANCH / PR_BASE
    2) GitHub workflow env: GITHUB_BASE_REF (if non-empty)
    3) Repo default branch via GitHub API
    4) Fallback to 'main'
    """
    env_base = (
        os.environ.get("BASE_BRANCH")
        or os.environ.get("PR_BASE")
        or os.environ.get("GITHUB_BASE_REF")
    )
    if env_base and env_base.strip():
        return env_base.strip()

    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo:
        try:
            info = _get_github_api(f"https://api.github.com/repos/{repo}")
            default_branch = (info.get("default_branch") or "").strip()
            if default_branch:
                return default_branch
        except Exception as e:
            print(f"⚠️  Failed to fetch repo default branch: {e}")

    return "main"


def _find_existing_pr(branch_name: str) -> Optional[dict]:
    """Find existing PR for the given branch that was auto-created and not merged."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise RuntimeError("GITHUB_REPOSITORY not set")
    
    api_url = f"https://api.github.com/repos/{repo}/pulls"
    params = {
        "state": "open",
        "head": f"{repo.split('/')[0]}:{branch_name}",
    }
    
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{api_url}?{query_string}"
    
    try:
        data = _get_github_api(url)
        if isinstance(data, list) and len(data) > 0:
            # Look for PR created by github-actions[bot]
            for pr in data:
                if pr.get("user", {}).get("login") == "github-actions[bot]":
                    # Check if PR has our marker in description
                    if "auto-generated" in pr.get("body", ""):
                        return pr
            # If no marked PR found, return the first one
            if data:
                return data[0]
        return None
    except Exception as e:
        print(f"⚠️  Failed to find existing PR: {e}")
        return None


def _create_pr(branch_name: str, title: str, body: str) -> dict:
    """Create a new PR."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise RuntimeError("GITHUB_REPOSITORY not set")
    
    # Resolve base branch robustly
    default_branch = _get_base_branch()
    
    api_url = f"https://api.github.com/repos/{repo}/pulls"
    
    payload = {
        "title": title,
        "body": body,
        "head": branch_name,
        "base": default_branch,
    }
    
    pr_data = _get_github_api(api_url, method="POST", data=payload)
    return pr_data


def _update_pr(pr_number: int, title: str, body: str) -> dict:
    """Update an existing PR."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise RuntimeError("GITHUB_REPOSITORY not set")
    
    api_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    
    payload = {
        "title": title,
        "body": body,
    }
    
    pr_data = _get_github_api(api_url, method="PATCH", data=payload)
    return pr_data


def _push_branch(branch_name: str, force: bool = False) -> bool:
    """Push branch to remote."""
    args = ["push", "origin", branch_name]
    if force:
        args.insert(2, "-f")
    
    result = _run_git(args)
    if result.returncode != 0:
        raise RuntimeError(f"git push failed: {result.stderr.strip()}")
    return True


def _create_or_update_pr_branch(
    files: Iterable[str],
    branch_name: str,
    message: str,
    user_name: str = "github-actions[bot]",
    user_email: str = "41898282+github-actions[bot]@users.noreply.github.com",
    cwd: str | None = None,
) -> bool:
    """Create or update a PR branch with changes."""
    if cwd:
        os.chdir(cwd)
    
    files = list(files)
    
    # Configure git user
    _run_git(["config", "user.name", user_name])
    _run_git(["config", "user.email", user_email])
    
    # Create or checkout branch
    check_branch = _run_git(["rev-parse", "--verify", branch_name])
    if check_branch.returncode != 0:
        # Branch doesn't exist, create it
        result = _run_git(["checkout", "-b", branch_name])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create branch: {result.stderr.strip()}")
    else:
        # Branch exists, switch to it
        result = _run_git(["checkout", branch_name])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to checkout branch: {result.stderr.strip()}")
    
    # Add files
    add_result = _run_git(["add", *files])
    if add_result.returncode != 0:
        raise RuntimeError(f"git add failed: {add_result.stderr.strip()}")
    
    # Check if there are changes
    status_result = _run_git(["status", "--porcelain"])
    if not status_result.stdout.strip():
        print("ℹ️  No changes to commit")
        return False
    
    # Commit
    commit_result = _run_git(["commit", "-m", message, "--allow-empty"])
    if commit_result.returncode != 0:
        raise RuntimeError(f"git commit failed: {commit_result.stderr.strip()}")
    
    # Push to remote
    _push_branch(branch_name, force=True)
    
    return True


def auto_commit(
    files: Iterable[str] | None = None,
    message: str = "chore: update contributors",
    user_name: str = "github-actions[bot]",
    user_email: str = "41898282+github-actions[bot]@users.noreply.github.com",
    cwd: str | None = None,
    push: bool = True,
) -> bool:
    """Automatically commit and push changes to tracked files."""
    if files is None:
        files = get_tracked_files()
    
    if not _is_github_actions():
        print("INFO: Not running in GitHub Actions; skipping auto-commit.")
        return False
    
    # Change to repo directory if specified
    if cwd:
        os.chdir(cwd)
    
    files = list(files)
    
    # Configure git user
    _run_git(["config", "user.name", user_name])
    _run_git(["config", "user.email", user_email])

    # Add files
    add_result = _run_git(["add", *files])
    if add_result.returncode != 0:
        raise RuntimeError(f"git add failed: {add_result.stderr.strip()}")

    # Commit
    commit_result = _run_git(["commit", "-m", message])
    if commit_result.returncode != 0:
        raise RuntimeError(f"git commit failed: {commit_result.stderr.strip()}")

    # Push
    if push:
        push_result = _run_git(["push"])
        if push_result.returncode != 0:
            raise RuntimeError(f"git push failed: {push_result.stderr.strip()}")

    print("✓ Auto-commit completed")
    return True


def create_or_update_pr(
    files: Iterable[str] | None = None,
    branch_name: str = "thanks-contributors/update",
    title: str = "chore: update contributors",
    message: str = "chore: update contributors",
    user_name: str = "github-actions[bot]",
    user_email: str = "41898282+github-actions[bot]@users.noreply.github.com",
    cwd: str | None = None,
) -> dict | None:
    """
    Create a new PR or update an existing one with changes.
    
    Returns:
        dict: PR data if created/updated, None if no changes
    """
    if files is None:
        files = get_tracked_files()
    
    if not _is_github_actions():
        print("INFO: Not running in GitHub Actions; skipping PR creation.")
        return None
    
    # Create or update branch with changes
    has_changes = _create_or_update_pr_branch(
        files=files,
        branch_name=branch_name,
        message=message,
        user_name=user_name,
        user_email=user_email,
        cwd=cwd,
    )
    
    if not has_changes:
        return None
    
    # Build PR body
    pr_body = f"""{message}

---
*This PR was auto-generated on {datetime.utcnow().isoformat()}Z*
*auto-generated*
"""
    
    # Check if PR already exists
    existing_pr = _find_existing_pr(branch_name)
    
    if existing_pr:
        # Update existing PR
        print(f"🔄 Updating existing PR #{existing_pr['number']}")
        pr_number = existing_pr["number"]
        pr_data = _update_pr(
            pr_number=pr_number,
            title=title,
            body=pr_body,
        )
        print(f"✓ PR #{pr_number} updated: {pr_data.get('html_url', '')}")
        return pr_data
    else:
        # Create new PR
        print("🆕 Creating new PR")
        pr_data = _create_pr(
            branch_name=branch_name,
            title=title,
            body=pr_body,
        )
        pr_number = pr_data.get("number")
        print(f"✓ PR #{pr_number} created: {pr_data.get('html_url', '')}")
        return pr_data
