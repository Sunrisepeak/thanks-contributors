#!/usr/bin/env python3
import os
import sys
import json
import time
import urllib.request
import urllib.parse
import ssl
from datetime import datetime, timezone

API = "https://api.github.com"

TARGETS_RAW = os.environ.get("TARGETS", "")
REPO_CTX = os.environ.get("GITHUB_REPOSITORY")
TOKEN = os.environ.get("GH_TOKEN")
OUT_FILE = os.environ.get("OUT_FILE", "contributors.json")

INCLUDE_ANONYMOUS = (os.environ.get("INCLUDE_ANONYMOUS", "true").lower() == "true")
SKIP_ARCHIVED = (os.environ.get("SKIP_ARCHIVED", "true").lower() == "true")
PER_REPO_DELAY_MS = int(os.environ.get("PER_REPO_DELAY_MS", "150"))

if not TOKEN:
    raise SystemExit("Missing env GH_TOKEN")



SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
from render_contributors import render_wall

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
            data = json.loads(res.read().decode("utf-8"))
            if not isinstance(data, list):
                raise RuntimeError(f"Expected list response for {next_url}")
            items.extend(data)
            link = res.headers.get("Link")
            next_url = parse_next_link(link)
    return items


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


def ensure_parent_dir(file_path: str):
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def describe_target(t: dict):
    if t["kind"] == "repo":
        return f"{t['owner']}/{t['repo']}"
    return f"{t['name']}/*"


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


def main():
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

    # Global aggregation: key -> { login, name, email, html_url, avatar_url, contributions }
    agg = {}
    # Per-repo contributors: full_repo_name -> list of contributors
    repo_details = {}

    scanned = 0
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

        try:
            contributors = list_repo_contributors(owner_login, repo_name)
        except RuntimeError as e:
            if "too large" in str(e):
                print(f"  ⚠️  skipped (contributor list too large)")
                continue
            raise

        repo_contributors = []

        for c in contributors:
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
                }

            agg[key]["contributions"] += int(c.get("contributions") or 0)

        repo_details[full] = {
            "count": len(repo_contributors),
            "contributors": repo_contributors,
        }

        if PER_REPO_DELAY_MS > 0:
            time.sleep(PER_REPO_DELAY_MS / 1000.0)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    display_contributors = []
    for _, v in agg.items():
        display_contributors.append(
            {
                "name": v.get("name"),
                "email": v.get("email"),
                "avatar_url": v.get("avatar_url"),
                "html_url": v.get("html_url"),
                "contributions": v.get("contributions", 0),
            }
        )

    # Generate visual walls
    try:
        render_wall(display_contributors, "contributors.html", "contributors.png")
    except Exception as e:
        print(f"Warning: failed to render contributors wall: {e}")

    # Build final contributors list (deduplicated, sorted by name)
    contributors_list = []
    for v in display_contributors:
        contributors_list.append({"name": v.get("name"), "email": v.get("email")})

    contributors_list.sort(key=lambda x: (x.get("name") or "").lower())

    out = {
        "all-contributors": "1.0.0",
        "count": len(contributors_list),
        "contributors": contributors_list,
        "details": repo_details,
    }

    ensure_parent_dir(OUT_FILE)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUT_FILE} (contributors={len(contributors_list)}, scanned_repos={scanned})")


if __name__ == "__main__":
    main()