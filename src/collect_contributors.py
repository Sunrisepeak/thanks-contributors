#!/usr/bin/env python3
import os
import re
import sys
import json
import time
import urllib.request
import urllib.parse
import ssl
from pathlib import Path
from datetime import datetime, timedelta, timezone

from config import get_output_dir, get_output_paths

API = "https://api.github.com"

TARGETS_RAW = os.environ.get("TARGETS", "")
REPO_CTX = os.environ.get("GITHUB_REPOSITORY")
TOKEN = os.environ.get("GH_TOKEN")

INCLUDE_ANONYMOUS = (os.environ.get("INCLUDE_ANONYMOUS", "true").lower() == "true")
SKIP_ARCHIVED = (os.environ.get("SKIP_ARCHIVED", "true").lower() == "true")
PER_REPO_DELAY_MS = int(os.environ.get("PER_REPO_DELAY_MS", "150"))
# Extra logins to exclude, appended to the built-in bot/agent filter
EXTRA_EXCLUDE_LOGINS = set(
    s.strip().lower()
    for s in os.environ.get("EXCLUDE_LOGINS", "").replace(",", " ").split()
    if s.strip()
)
MAX_COMMIT_PAGES = 50

# Matches GitHub App bots ([bot] suffix, type=Bot handles most), common agent
# logins (speak-agent, cursoragent, ...) and legacy bot naming (-bot/_bot suffix)
BOT_LOGIN_RE = re.compile(r"(?i)agent|\[bot\]$|^bot$|[-_]bot$")
DEFAULT_EXCLUDE_LOGINS = {
    "copilot", "dependabot[bot]", "renovate[bot]", "imgbot[bot]",
    "greenkeeper[bot]", "allcontributors[bot]", "semantic-release-bot",
    "codecov-commenter", "snyk-bot",
}

if not TOKEN:
    raise SystemExit("Missing env GH_TOKEN")



SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
from render_contributors import render_wall, sort_contributors

def request(url: str):
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "org-contributors-action")

    try:
        # Create SSL context that doesn't verify certificates
        # (needed in some environments with corporate proxies or certificate issues)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        return urllib.request.urlopen(req, context=ssl_context)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        remaining = e.headers.get("x-ratelimit-remaining")
        reset = e.headers.get("x-ratelimit-reset")
        if e.code == 403:
            raise RuntimeError(
                f"403 Forbidden. rate_remaining={remaining} rate_reset={reset} body={body}"
            ) from None
        raise RuntimeError(f"{e.code} {e.reason}: {body}") from None


def parse_next_link(link_header: str):
    # Link: <url>; rel="next", <url>; rel="last"
    if not link_header:
        return None
    parts = [p.strip() for p in link_header.split(",")]
    for p in parts:
        if 'rel="next"' in p:
            start = p.find("<")
            end = p.find(">")
            if start != -1 and end != -1 and end > start:
                return p[start + 1 : end]
    return None


def paginate(url: str):
    items = []
    next_url = url
    while next_url:
        with request(next_url) as res:
            raw = res.read()
            # 204 No Content (e.g. empty repository) — treat as empty list
            if res.status == 204 or not raw.strip():
                return items
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, list):
                raise RuntimeError(f"Expected list response for {next_url}")
            items.extend(data)
            link = res.headers.get("Link")
            next_url = parse_next_link(link)
    return items


def is_bot_login(login: str) -> bool:
    if not login:
        return False
    login = login.lower()
    if BOT_LOGIN_RE.search(login):
        return True
    return login in DEFAULT_EXCLUDE_LOGINS or login in EXTRA_EXCLUDE_LOGINS


def is_bot_account(c: dict) -> bool:
    if c.get("type") == "Bot":
        return True
    return is_bot_login(c.get("login"))


def list_org_public_repos(org: str):
    qs = urllib.parse.urlencode({"type": "public", "per_page": 100, "sort": "updated"})
    return paginate(f"{API}/orgs/{org}/repos?{qs}")


def list_user_public_repos(user: str):
    qs = urllib.parse.urlencode({"type": "public", "per_page": 100, "sort": "updated"})
    return paginate(f"{API}/users/{user}/repos?{qs}")


def list_repo_contributors(owner: str, repo: str):
    qs = urllib.parse.urlencode(
        {"per_page": 100, "anon": "true" if INCLUDE_ANONYMOUS else "false"}
    )
    return paginate(f"{API}/repos/{owner}/{repo}/contributors?{qs}")


def get_repo(owner: str, repo: str):
    with request(f"{API}/repos/{owner}/{repo}") as res:
        data = json.loads(res.read().decode("utf-8"))
    return data


def collect_recent_commit_counts(owner: str, repo: str, since_iso: str):
    """Count commits in the recent window, keyed like the contributors
    aggregation (user:{login} / anon:{name or email}).

    Returns (counts, failed). Tolerates empty repositories (409/204)."""
    counts = {}
    qs = urllib.parse.urlencode({"per_page": 100, "since": since_iso})
    next_url = f"{API}/repos/{owner}/{repo}/commits?{qs}"
    pages = 0
    while next_url:
        if pages >= MAX_COMMIT_PAGES:
            print(f"  ⚠️  recent commits truncated at {MAX_COMMIT_PAGES} pages")
            break
        try:
            with request(next_url) as res:
                raw = res.read()
                status = res.status
                link = res.headers.get("Link")
        except RuntimeError as e:
            if "409" in str(e) or "is empty" in str(e).lower():
                break  # empty repository — no commits at all
            print(f"  ⚠️  recent commits fetch failed: {e}")
            return counts, True
        if status == 204 or not raw.strip():
            break
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            break
        if not isinstance(data, list):
            break
        for cm in data:
            author = cm.get("author") if isinstance(cm.get("author"), dict) else {}
            login = author.get("login")
            if login and is_bot_login(login):
                continue
            if login:
                key = f"user:{login}"
            else:
                ca = (cm.get("commit") or {}).get("author") or {}
                key = f"anon:{ca.get('name') or ca.get('email') or 'unknown'}"
            counts[key] = counts.get(key, 0) + 1
        pages += 1
        next_url = parse_next_link(link)
    return counts, False


def ensure_parent_dir(file_path: str):
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def describe_target(t: dict):
    if t["kind"] == "repo":
        return f"{t['owner']}/{t['repo']}"
    return f"{t['name']}/*"


def load_existing_json(json_path):
    """Load the existing contributors JSON file if it exists."""
    if not json_path.exists():
        return None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def contributors_changed(json_path, new_contributors_list, new_display_names, sort_cfg):
    """True if the contributor set, display config, or rendered order changed.

    Pure count changes (recent_commits +/-) don't trigger a re-render since
    the wall displays no numbers — only set/config/order changes do."""
    existing = load_existing_json(json_path)
    if existing is None:
        return True

    old = existing.get("contributors", [])
    old_set = {(c.get("name"), c.get("email")) for c in old}
    new_set = {(c.get("name"), c.get("email")) for c in new_contributors_list}
    if old_set != new_set:
        print("Contributors changed (new/updated contributors detected)")
        return True

    if existing.get("display") != sort_cfg:
        print("Contributors changed (display configuration changed)")
        return True

    old_names = [c.get("name") for c in old]
    if old_names[: len(new_display_names)] != list(new_display_names):
        print("Contributors changed (display order changed)")
        return True

    print("Contributors unchanged (skipping render)")
    return False


def parse_targets(raw_targets: str, repo_ctx: str):
    tokens = []
    for part in raw_targets.replace(",", " ").split():
        if part.strip():
            tokens.append(part.strip())

    targets = []
    for tok in tokens:
        if "/" in tok:
            owner, _, repo = tok.partition("/")
            if not owner or not repo:
                raise SystemExit(f"Invalid target '{tok}', expected owner/repo or owner/*")
            targets.append({"kind": "repo" if repo != "*" else "org_user", "owner": owner, "repo": repo, "name": owner})
        else:
            raise SystemExit(f"Invalid target '{tok}', expected owner/repo or owner/*")

    if not targets:
        repo_target = detect_target_from_repo(repo_ctx)
        if repo_target:
            targets.append(repo_target)

    if not targets:
        raise SystemExit("No targets resolved. Provide targets or run in a GitHub Actions repo context.")

    return targets


def detect_target_from_repo(repo_ctx: str):
    if not repo_ctx or "/" not in repo_ctx:
        return None
    owner, _, repo = repo_ctx.partition("/")
    try:
        repo_info = get_repo(owner, repo)
    except Exception:
        return None
    return {"kind": "org_user", "name": owner}


def resolve_sort_config():
    raw_pinned = os.environ.get("SORT_PINNED", "")
    pinned = [p for p in re.split(r"[,\s]+", raw_pinned.strip()) if p]

    sort_by = (os.environ.get("SORT_BY", "recent_commits") or "recent_commits").strip().lower()
    if sort_by not in ("recent_commits", "contributions", "name"):
        print(f"⚠️  unknown SORT_BY '{sort_by}', falling back to 'recent_commits'")
        sort_by = "recent_commits"

    try:
        window_days = int(os.environ.get("RECENT_WINDOW_DAYS", "365"))
    except ValueError:
        window_days = 365
    if window_days <= 0:
        window_days = 365

    try:
        max_display = int(os.environ.get("MAX_DISPLAY", "50"))
    except ValueError:
        max_display = 50
    if max_display < 0:
        max_display = 0

    return {
        "sort_pinned": pinned,
        "sort_by": sort_by,
        "recent_window_days": window_days,
        "max_display": max_display,
    }


def main():
    # Get output paths (must be done here after environment is fully set up)
    # config.py handles GITHUB_WORKSPACE prefix automatically
    output_dir_path = get_output_dir()
    paths = get_output_paths(output_dir_path)
    out_json_path = paths["json"]
    html_out_path = paths["html"]
    png_out_path = paths["png"]
    md_out_path = paths["md"]
    readme_path = paths["readme"]

    print(f"DEBUG: readme_path = {readme_path}")
    print(f"DEBUG: readme_path type = {type(readme_path)}")

    targets = parse_targets(TARGETS_RAW, REPO_CTX)
    seen_labels = set()
    target_labels = []
    for t in targets:
        label = describe_target(t)
        if label in seen_labels:
            continue
        seen_labels.add(label)
        target_labels.append(label)
    print(f"Targets: {', '.join(target_labels)}")

    sort_cfg = resolve_sort_config()
    print(
        f"Display config: sort_by={sort_cfg['sort_by']} "
        f"pinned={sort_cfg['sort_pinned'] or '-'} "
        f"window={sort_cfg['recent_window_days']}d max_display={sort_cfg['max_display'] or 'unlimited'}"
    )

    repo_pool = []
    seen_repos = set()
    for t in targets:
        if t["kind"] == "org_user":
            try:
                repos = list_org_public_repos(t["name"])
            except Exception as e:
                try:
                    repos = list_user_public_repos(t["name"])
                except Exception as e2:
                    print(f"Warning: Could not fetch repos for {t['name']}, skipping.")
                    print(f"  (org error: {e})")
                    print(f"  (user error: {e2})")
                    repos = []
        else:
            repos = [get_repo(t["owner"], t["repo"])]

        for r in repos:
            full = r.get("full_name")
            if full and full in seen_repos:
                continue
            seen_repos.add(full)
            repo_pool.append(r)

    # Global aggregation: key -> { login, name, email, html_url, avatar_url, contributions, recent_commits }
    agg = {}
    # Per-repo contributors: full_repo_name -> list of contributors
    repo_details = {}

    since_iso = (
        datetime.now(timezone.utc) - timedelta(days=sort_cfg["recent_window_days"])
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    scanned = 0
    failed_repos = []
    recent_failures = 0
    for r in repo_pool:
        if SKIP_ARCHIVED and r.get("archived"):
            continue
        if r.get("disabled"):
            continue
        if r.get("fork"):
            continue

        scanned += 1
        owner_login = (r.get("owner") or {}).get("login")
        repo_name = r["name"]
        owner_login = owner_login or r.get("full_name", "").split("/")[0]
        full = r.get("full_name", f"{owner_login}/{repo_name}")
        print(f"[{scanned}] scanning {full}")

        # A single broken repo must not fail the whole run
        try:
            contributors = list_repo_contributors(owner_login, repo_name)
        except RuntimeError as e:
            if "too large" in str(e):
                print(f"  ⚠️  skipped (contributor list too large)")
                continue
            print(f"  ⚠️  skipped ({e})")
            failed_repos.append(full)
            continue
        except Exception as e:
            print(f"  ⚠️  skipped ({e})")
            failed_repos.append(full)
            continue

        try:
            recent, recent_failed = collect_recent_commit_counts(owner_login, repo_name, since_iso)
        except Exception as e:
            print(f"  ⚠️  recent commits error ({e})")
            recent, recent_failed = {}, True
        if recent_failed:
            recent_failures += 1

        repo_contributors = []

        for c in contributors:
            # Skip bot / agent accounts
            if is_bot_account(c):
                continue
            login = c.get("login")
            if not login and not INCLUDE_ANONYMOUS:
                continue

            key = f"user:{login}" if login else f"anon:{c.get('name') or c.get('email') or 'unknown'}"

            # Build contributor info
            contrib_info = {
                "name": c.get("name") or c.get("login") or "unknown",
                "email": c.get("email"),
            }
            repo_contributors.append(contrib_info)

            # Aggregate globally
            if key not in agg:
                agg[key] = {
                    "login": login,
                    "name": c.get("name") or c.get("login") or "unknown",
                    "email": c.get("email"),
                    "html_url": c.get("html_url"),
                    "avatar_url": c.get("avatar_url"),
                    "contributions": 0,
                    "recent_commits": 0,
                }

            agg[key]["contributions"] += int(c.get("contributions") or 0)
            agg[key]["recent_commits"] += recent.get(key, 0)

        repo_details[full] = {
            "count": len(repo_contributors),
            "contributors": repo_contributors,
        }

        if PER_REPO_DELAY_MS > 0:
            time.sleep(PER_REPO_DELAY_MS / 1000.0)

    if failed_repos:
        print(f"\n⚠️  {len(failed_repos)} repo(s) failed and were skipped:")
        for f in failed_repos:
            print(f"   - {f}")

    # Fall back to all-time contributions when recent data is entirely missing
    if (
        sort_cfg["sort_by"] == "recent_commits"
        and recent_failures > 0
        and not any(v.get("recent_commits") for v in agg.values())
        and scanned > 0
    ):
        print("⚠️  recent commits data unavailable; sorting by contributions instead")
        sort_cfg["sort_by"] = "contributions"

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    display_contributors = []
    for _, v in agg.items():
        display_contributors.append(
            {
                "name": v.get("name"),
                "email": v.get("email"),
                "login": v.get("login"),
                "avatar_url": v.get("avatar_url"),
                "html_url": v.get("html_url"),
                "contributions": v.get("contributions", 0),
                "recent_commits": v.get("recent_commits", 0),
            }
        )

    # Display order: pinned first (config order), then by sort key.
    # JSON keeps the full ordered list; max_display only limits rendering.
    ordered_full = sort_contributors(
        display_contributors,
        pinned=sort_cfg["sort_pinned"],
        sort_by=sort_cfg["sort_by"],
        max_display=0,
    )
    max_display = sort_cfg["max_display"]
    display_limited = ordered_full[:max_display] if max_display > 0 else ordered_full

    contributors_list = [
        {
            "name": c.get("name"),
            "email": c.get("email"),
            "login": c.get("login"),
            "contributions": c.get("contributions", 0),
            "recent_commits": c.get("recent_commits", 0),
        }
        for c in ordered_full
    ]

    # Check if contributors have changed before writing/rendering
    display_names = [c.get("name") for c in display_limited]
    has_changes = contributors_changed(out_json_path, contributors_list, display_names, sort_cfg)

    out = {
        "thanks-contributors": "1.1.0",
        "count": len(contributors_list),
        "display": sort_cfg,
        "contributors": contributors_list,
        "details": repo_details,
    }

    # Only write and render if there are changes
    if has_changes:
        # Ensure output directories exist
        ensure_parent_dir(str(out_json_path))
        ensure_parent_dir(str(html_out_path))
        ensure_parent_dir(str(png_out_path))
        ensure_parent_dir(str(md_out_path))

        try:
            render_wall(
                display_contributors,
                str(html_out_path),
                str(png_out_path),
                str(md_out_path),
                str(readme_path),
                pinned=sort_cfg["sort_pinned"],
                sort_by=sort_cfg["sort_by"],
                max_display=max_display,
            )
        except Exception as e:
            print(f"Warning: failed to render contributors wall: {e}")

        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    else:
        # Ensure parent directory exists even if we skip writing
        ensure_parent_dir(str(out_json_path))

    print(
        f"Wrote {out_json_path} (contributors={len(contributors_list)}, scanned_repos={scanned})"
    )

    # Return whether there were changes
    return has_changes


if __name__ == "__main__":
    main()
