"""Shared configuration for output locations and filenames."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Tuple

DEFAULT_OUTPUT_DIR = ".thanks-contributors"
CONTRIB_JSON_NAME = "contributors.json"
CONTRIB_HTML_NAME = "contributors.html"
CONTRIB_PNG_NAME = "contributors.png"
CONTRIB_MD_NAME = "contributors.md"
DEFAULT_README_NAME = "README.md"


def get_output_dir() -> Path:
    """Get output directory, using GITHUB_WORKSPACE as base when running as action."""
    output_dir = os.environ.get("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
    github_workspace = os.environ.get("GITHUB_WORKSPACE")
    
    # If running as GitHub Action, use workspace as base
    if github_workspace:
        return Path(github_workspace) / output_dir
    else:
        return Path(output_dir)


def get_output_paths(base_dir: Path | None = None) -> Dict[str, Path]:
    root = Path(base_dir) if base_dir else get_output_dir()
    readme_name = os.environ.get("README_PATH", DEFAULT_README_NAME)
    github_workspace = os.environ.get("GITHUB_WORKSPACE")
    
    # README path: handle absolute vs relative paths
    readme_path = Path(readme_name)
    
    # If path is not absolute, resolve it relative to workspace or current dir
    if not readme_path.is_absolute():
        if github_workspace:
            # Running in GitHub Actions: resolve relative to workspace
            readme_path = Path(github_workspace) / readme_name
        else:
            # Running locally: resolve relative to current directory
            readme_path = Path.cwd() / readme_name
    
    return {
        "json": root / CONTRIB_JSON_NAME,
        "html": root / CONTRIB_HTML_NAME,
        "png": root / CONTRIB_PNG_NAME,
        "md": root / CONTRIB_MD_NAME,
        "readme": readme_path,
    }


def get_tracked_files(base_dir: Path | None = None) -> Tuple[str, str, str, str, str]:
    paths = get_output_paths(base_dir)
    return (str(paths["json"]), str(paths["png"]), str(paths["html"]), str(paths["md"]), str(paths["readme"]))
