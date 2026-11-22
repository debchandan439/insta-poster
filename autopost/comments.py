"""The owner answers an Approve issue with a short comment."""
import json
import os
import re
from . import config as C, ghub, publish


def handle():
    event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
    if event["comment"].get("author_association") != "OWNER":
        print("ignored: comment is not from the repository owner")
        return
    m = re.search(r"<!-- slug: ([A-Za-z0-9_-]+) -->", event["issue"].get("body") or "")
    if not m:
        print("ignored: not an Approve issue")
        return
    slug, number = m.group(1), event["issue"]["number"]
    meta = ghub.load(slug)
    text = (event["comment"]["body"] or "").strip()
    first = text.splitlines()[0].strip().lower().rstrip(".!") if text else ""

    if meta["status"] in ("posted", "skipped"):
        ghub.comment(number, f"এই পোস্ট আগেই {meta['status']}।")
    elif first.startswith("caption:"):
        new = (text.split(":", 1)[1]).strip()
        if not new:
            ghub.comment(number, "`caption:` এর পরে নতুন ক্যাপশন লিখুন।")
            return
        meta["caption"] = new[:2100]
        (C.QUEUE / slug / "caption.txt").write_text(meta["caption"], encoding="utf-8")
        ghub.save(slug, meta)
        ghub.commit_and_push(f"Edit caption {slug}")
        ghub.comment(number, "✏️ ক্যাপশন বদলানো হয়েছে। এখন `ok` বা `post now` লিখুন।")
    elif first in ("ok", "okay", "approve", "approved", "yes"):
        meta["status"] = "approved"
        ghub.save(slug, meta)
        ghub.commit_and_push(f"Approved {slug}")
        ghub.comment(number, "👍 অনুমোদিত। পরের সকাল ৯:৩০-এ পোস্ট হবে। (এখনই চাইলে `post now` লিখুন)")
    elif first in ("post now", "now", "retry"):
        meta["status"] = "approved"
        ghub.save(slug, meta)
        publish.publish_slug(slug)
    elif first == "skip":
        meta["status"] = "skipped"
        ghub.save(slug, meta)
        ghub.commit_and_push(f"Skipped {slug}")
        ghub.comment(number, "🚫 বাতিল করা হলো।")
        ghub.close_issue(number)
    else:
        ghub.comment(number, "বুঝিনি। লিখুন: `ok`, `post now`, `skip`, অথবা `caption:` দিয়ে নতুন ক্যাপশন।")
