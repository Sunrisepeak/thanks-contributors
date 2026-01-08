#!/usr/bin/env python3
"""
Local CLI tool for generating contributors data.

Usage:
    python main.py [--token TOKEN] <target1> [target2] [...]
    
Examples:
    python main.py 'Sunrisepeak/*'
    python main.py Sunrisepeak/xlings
    python main.py --token ghp_xxx 'octocat/*' alice/repo bob/project
    
Targets format:
    - owner/*        : All public repos of owner (org or user)
    - owner/repo     : Specific repository
    
Options:
    --token TOKEN    : GitHub personal access token (or use GITHUB_TOKEN env var)
"""

import os
import sys
import argparse
from pathlib import Path

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

# Set up minimal environment
os.environ.setdefault("OUT_FILE", "contributors.json")
os.environ.setdefault("INCLUDE_ANONYMOUS", "true")
os.environ.setdefault("SKIP_ARCHIVED", "false")
os.environ.setdefault("PER_REPO_DELAY_MS", "150")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Generate contributors data for GitHub repositories',
        usage='python main.py [--token TOKEN] <target1> [target2] ...',
        add_help=False
    )
    parser.add_argument('--token', type=str, help='GitHub personal access token')
    parser.add_argument('targets', nargs='*', help='Target repositories (owner/* or owner/repo)')
    parser.add_argument('-h', '--help', action='store_true', help='Show this help message')

    args = parser.parse_args()

    if args.help:
        print(__doc__)
        sys.exit(0)

    repo_ctx = os.environ.get("GITHUB_REPOSITORY", "")
    env_targets = os.environ.get("TARGETS", "").strip()
    
    # Get GitHub token from --token argument or environment
    token = args.token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("❌ Error: GitHub token not found")
        print("\nPlease provide a token using one of:")
        print("  1. --token flag:        python main.py --token ghp_xxx 'Sunrisepeak/*'")
        print("  2. GITHUB_TOKEN env:    export GITHUB_TOKEN='your_token_here'")
        print("  3. Inline env:          GITHUB_TOKEN='token' python main.py 'Sunrisepeak/*'")
        sys.exit(1)
    
    # Set token for script
    os.environ["GH_TOKEN"] = token
    
    # Resolve targets: CLI > env TARGETS > default for this repo > auto-detect
    if args.targets:
        targets = " ".join(args.targets)
    elif env_targets:
        targets = env_targets
    else:
        if repo_ctx == "Sunrisepeak/all-contributors":
            targets = "Sunrisepeak/* mcpp-community/* d2learn/*"
            print("🔧 Using default targets for Sunrisepeak/all-contributors")
        else:
            targets = ""  # allow downstream auto-detect based on GITHUB_REPOSITORY
            if not repo_ctx:
                print("⚠️  No targets provided and GITHUB_REPOSITORY is empty; auto-detect may fail.")
    
    # Apply smart defaults for Sunrisepeak/all-contributors
    if targets == "Sunrisepeak/all-contributors":
        targets = "Sunrisepeak/* mcpp-community/* d2learn/*"
        print("🔧 Using default targets for Sunrisepeak/all-contributors")

    os.environ["TARGETS"] = targets

    print(f"🚀 Collecting contributors for: {targets or '(auto-detect)'}")
    print(f"📁 Output directory: {os.getcwd()}")
    print()
    
    # Import and run the collector
    try:
        from collect_contributors import main as collect_main
        collect_main()
        
        # Check if files were generated
        json_file = Path("contributors.json")
        png_file = Path("contributors.png")
        html_file = Path("contributors.html")
        
        print("\n✅ Generation complete!")
        
        if json_file.exists():
            size = json_file.stat().st_size
            print(f"   📄 {json_file} ({size} bytes)")
        
        if png_file.exists():
            size = png_file.stat().st_size
            print(f"   🖼️ {png_file} ({size} bytes)")
        
        if html_file.exists():
            size = html_file.stat().st_size
            print(f"   🌐 {html_file} ({size} bytes)")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
