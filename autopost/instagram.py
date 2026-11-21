"""Posts a photo or a Reel to Instagram through the official Graph API."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"


class IGError(Exception):
    pass


def _call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params)
    if method == "GET":
        req = urllib.request.Request(f"{GRAPH}/{path}?{data}")
    else:
        req = urllib.request.Request(f"{GRAPH}/{path}", data=data.encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise IGError(e.read().decode()[:600])


def _wait(container, tries, delay):
    for _ in range(tries):
        st = _call("GET", container, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise IGError(f"Instagram could not process the file ({st})")
        time.sleep(delay)
    raise IGError("Instagram took too long to process the file")


def _publish(container):
    return _call("POST", f"{os.environ['IG_USER_ID']}/media_publish", creation_id=container)["id"]


def publish_image(image_url, caption):
    c = _call("POST", f"{os.environ['IG_USER_ID']}/media", image_url=image_url, caption=caption)["id"]
    _wait(c, 20, 5)
    return _publish(c)


def publish_reel(video_url, caption, cover_url=None):
    extra = {"cover_url": cover_url} if cover_url else {}
    c = _call("POST", f"{os.environ['IG_USER_ID']}/media", media_type="REELS",
              video_url=video_url, caption=caption, share_to_feed="true", **extra)["id"]
    _wait(c, 72, 5)
    return _publish(c)


def content_type(url):
    """Diagnostic: what type does the web server say this file is?"""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.headers.get("Content-Type", "?")
    except Exception as e:  # noqa
        return f"unreachable ({type(e).__name__})"
