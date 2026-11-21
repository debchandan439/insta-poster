"""Also posts to the Facebook Page (optional: only runs when FB_PAGE_ID and FB_PAGE_TOKEN secrets exist)."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"


class FBError(Exception):
    pass


def enabled():
    return bool(os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_TOKEN"))


def _post(url, data=None, headers=None, method="POST"):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise FBError(e.read().decode()[:500])


def post_photo(image_url, caption):
    page, tok = os.environ["FB_PAGE_ID"], os.environ["FB_PAGE_TOKEN"]
    return _post(f"{GRAPH}/{page}/photos", {"url": image_url, "caption": caption, "access_token": tok})


def post_reel(video_url, caption):
    """Facebook Reel; if that route is refused, falls back to a normal Page video."""
    page, tok = os.environ["FB_PAGE_ID"], os.environ["FB_PAGE_TOKEN"]
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
