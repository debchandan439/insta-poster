"""Small helpers for git, GitHub issues and the queue folder."""
import json
import os
import re
import subprocess
from . import config as C

SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def run(*args, check=True):
    if C.DRY_RUN:
        print("[dry-run]", " ".join(args)[:200])
        return ""
    return subprocess.run(args, check=check, capture_output=True, text=True, cwd=C.ROOT).stdout


def repo():
    return os.environ.get("GITHUB_REPOSITORY", "owner/repo")


def branch():
    return os.environ.get("GITHUB_REF_NAME") if os.environ.get("GITHUB_EVENT_NAME") == "push" else "main"


def commit_and_push(message):
    run("git", "config", "user.name", "bhaktibox-bot")
    run("git", "config", "user.email", "bot@users.noreply.github.com")
    run("git", "add", "-A")
    if C.DRY_RUN:
        return
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=C.ROOT).returncode == 0:
        return
    run("git", "commit", "-m", message)
    run("git", "pull", "--rebase", "origin", "main", check=False)
    run("git", "push", "origin", "HEAD:main")


def new_issue(title, body):
    out = run("gh", "issue", "create", "--title", title, "--body", body)
    m = re.search(r"/issues/(\d+)", out or "")
    return int(m.group(1)) if m else 0


def comment(number, body):
    if number:
        run("gh", "issue", "comment", str(number), "--body", body)


def close_issue(number):
    if number:
        run("gh", "issue", "close", str(number))


def meta_path(slug):
    if not SLUG_RE.match(slug):
        raise ValueError("bad slug")
    return C.QUEUE / slug / "meta.json"


def load(slug):
    return json.loads(meta_path(slug).read_text(encoding="utf-8"))


def save(slug, meta):
    meta_path(slug).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def all_items():
    out = []
    for d in sorted(C.QUEUE.iterdir()) if C.QUEUE.exists() else []:
        if (d / "meta.json").exists():
            out.append(load(d.name))
    return out
