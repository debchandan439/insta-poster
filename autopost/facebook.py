"""Also posts to the Facebook Page (optional: only runs when FB_PAGE_ID and FB_PAGE_TOKEN secrets exist)."""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"


class FBError(Exception):
    pass


def _tok():
    """Token exactly as Facebook wants it: no quotes, spaces, commas or line breaks around it."""
    return re.sub(r"\s+", "", os.environ.get("FB_PAGE_TOKEN", "")).strip("\"',")


def _pid():
    return re.sub(r"\D", "", os.environ.get("FB_PAGE_ID", ""))


def enabled():
    raw = os.environ.get("FB_PAGE_ID", "").strip()
    if raw and not raw.isdigit():
        print("FB_PAGE_ID must be only digits (the Page number), not a token - Facebook posting skipped")
        return False
    if _tok() and not _tok().startswith("EAA"):
        print("FB_PAGE_TOKEN does not look like a token (should start with EAA) - Facebook posting skipped")
        return False
    return bool(raw and _tok())


def _post(url, data=None, headers=None, method="POST"):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise FBError(e.read().decode()[:500])


def post_photo(image_url, caption):
    page, tok = _pid(), _tok()
    return _post(f"{GRAPH}/{page}/photos", {"url": image_url, "caption": caption, "access_token": tok})


def post_reel(video_url, caption):
    """Facebook Reel; if that route is refused, falls back to a normal Page video."""
    page, tok = _pid(), _tok()
    try:
        start = _post(f"{GRAPH}/{page}/video_reels", {"upload_phase": "start", "access_token": tok})
        _post(start["upload_url"], headers={"Authorization": f"OAuth {tok}", "file_url": video_url})
        for _ in range(6):   # the file is fetched by Facebook; try finishing a few times
            try:
                return _post(f"{GRAPH}/{page}/video_reels", {
                    "upload_phase": "finish", "video_id": start["video_id"],
                    "video_state": "PUBLISHED", "description": caption, "access_token": tok})
            except FBError:
                time.sleep(10)
        raise FBError("reel did not finish")
    except Exception:  # noqa
        return _post(f"{GRAPH}/{page}/videos", {"file_url": video_url, "description": caption, "access_token": tok})
