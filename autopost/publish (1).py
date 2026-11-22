"""Posts approved items (picture first, then the Reel)."""
import os
import re
import time
from . import config as C, facebook, ghub, instagram


def _scrub(text):
    """Never let a token appear in an issue comment (the repository is public)."""
    text = re.sub(r"EAA[A-Za-z0-9_-]{20,}", "[token hidden]", str(text))
    for name in ("IG_ACCESS_TOKEN", "FB_PAGE_TOKEN", "GEMINI_API_KEY"):
        v = os.environ.get(name, "")
        if len(v) > 12:
            text = text.replace(v, "[secret hidden]")
    return text


def publish_slug(slug):
    """Posts what is still missing. Each part (Instagram/Facebook, picture/Reel) is remembered once it is
    live, so a retry never posts the same thing twice."""
    m = ghub.load(slug)
    if m.get("status") in ("posted", "skipped"):
        print("already", m["status"], slug)
        return True
    base = f"https://raw.githubusercontent.com/{ghub.repo()}/main/queue/{slug}"
    caption = (C.QUEUE / slug / "caption.txt").read_text(encoding="utf-8")
    ig_done, fb_done = set(m.get("ig_done", [])), set(m.get("fb_done", []))
    problems, fb_notes, new_ok = [], [], []
    if m.get("kind") == "video":   # own video: Reel only, with the chosen cover picture
        jobs = (("Reel", f"{base}/reel.mp4",
                 lambda u, c: instagram.publish_reel(u, c, cover_url=f"{base}/cover.jpg")),)
    else:
        jobs = (("ছবি", f"{base}/ad.jpg", instagram.publish_image),
                ("Reel", f"{base}/reel.mp4", instagram.publish_reel))
    fb_fn = {"ছবি": facebook.post_photo, "Reel": facebook.post_reel}
    use_fb = facebook.enabled() and not C.DRY_RUN
    for kind, url, fn in jobs:
        if kind not in ig_done:
            try:
                if C.DRY_RUN:
                    print("[dry-run] would post", kind, url)
                else:
                    if kind == "Reel":
                        print("video content-type:", instagram.content_type(url))
                    for attempt in range(3):   # a failed try posts nothing, so trying again is safe
                        try:
                            fn(url, caption)
                            break
                        except Exception as e:  # noqa
                            if attempt == 2 or "could not process" not in str(e):
                                raise
                            print("Instagram could not process the file, trying again in 45 s:", _scrub(e))
                            time.sleep(45)
                ig_done.add(kind)
                new_ok.append(kind)
            except Exception as e:  # noqa
                problems.append(f"Instagram {kind}: {_scrub(e)}")
        if use_fb and kind not in fb_done:   # Facebook works on its own
            try:
                fb_fn[kind](url, caption)
                fb_done.add(kind)
                fb_notes.append(f"Facebook {kind} ✅")
            except Exception as e:  # noqa
                fb_notes.append(f"Facebook {kind} ❌ {_scrub(e)[:300]}")
    m["ig_done"], m["fb_done"] = sorted(ig_done), sorted(fb_done)
    all_kinds = {k for k, _, _ in jobs}
    complete = all_kinds <= ig_done
    m["status"] = "posted" if complete else ("partial" if ig_done else "failed")
    ghub.save(slug, m)
    head = "✅ Instagram-এ পোস্ট হয়েছে: " + ", ".join(new_ok) if new_ok else "Instagram-এ নতুন কিছু পোস্ট হয়নি।"
    msg = head
    if fb_notes:
        msg += "\n\n" + "\n".join(fb_notes)
    if problems:
        msg += "\n\n⚠️ এটা হয়নি:\n```\n" + "\n".join(problems) + "\n```"
        msg += "\nআবার চেষ্টা করতে এখানে `retry` লিখুন। যা আগে পোস্ট হয়ে গেছে সেটা আর পোস্ট হবে না।"
    ghub.comment(m.get("issue"), msg)
    ghub.commit_and_push(f"{m['status']}: {slug}")
    if complete:
        ghub.close_issue(m.get("issue"))
    return complete


def publish_next():
    approved = [i for i in ghub.all_items() if i["status"] == "approved"]
    if not approved:
        print("no approved posts waiting")
        return
    publish_slug(approved[0]["slug"])   # one set per day
