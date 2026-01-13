"""Git helpers for change detection and auto-commits."""

from __future__ import annotations

import os
import subprocess
from typing import Iterable

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
