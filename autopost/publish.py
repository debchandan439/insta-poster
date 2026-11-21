"""Posts approved items (picture first, then the Reel)."""
from . import config as C, facebook, ghub, instagram


def publish_slug(slug):
    m = ghub.load(slug)
    base = f"https://raw.githubusercontent.com/{ghub.repo()}/main/queue/{slug}"
    caption = (C.QUEUE / slug / "caption.txt").read_text(encoding="utf-8")
    ok, problems = [], []
    if m.get("kind") == "video":   # own video: Reel only, with the chosen cover picture
        jobs = (("Reel", f"{base}/reel.mp4",
                 lambda u, c: instagram.publish_reel(u, c, cover_url=f"{base}/cover.jpg")),)
    else:
        jobs = (("ছবি", f"{base}/ad.jpg", instagram.publish_image),
                ("Reel", f"{base}/reel.mp4", instagram.publish_reel))
    fb_notes = []
    fb_fn = {"ছবি": facebook.post_photo, "Reel": facebook.post_reel}
    for kind, url, fn in jobs:
        try:
            if C.DRY_RUN:
                print("[dry-run] would post", kind, url)
            else:
                if kind == "Reel":
                    print("video content-type:", instagram.content_type(url))
                fn(url, caption)
            ok.append(kind)
        except Exception as e:  # noqa
            problems.append(f"{kind}: {e}")
            continue
        if facebook.enabled() and not C.DRY_RUN:   # Facebook trouble never blocks Instagram
            try:
                fb_fn[kind](url, caption)
                fb_notes.append(f"Facebook {kind} ✅")
            except Exception as e:  # noqa
                fb_notes.append(f"Facebook {kind} ❌ {str(e)[:300]}")
    if not ok:
        m["status"] = "failed"
        ghub.save(slug, m)
        ghub.comment(m.get("issue"), "❌ পোস্ট হয়নি।\n\n```\n" + "\n".join(problems) + "\n```\nএই লেখাটার ছবি আমাকে পাঠান।")
        ghub.commit_and_push(f"Failed: {slug}")
        return False
    m["status"] = "posted"
    ghub.save(slug, m)
    msg = "✅ Instagram-এ পোস্ট হয়েছে: " + ", ".join(ok)
    if fb_notes:
        msg += "\n\n" + "\n".join(fb_notes)
    if problems:
        msg += "\n\n⚠️ কিন্তু এটা হয়নি:\n```\n" + "\n".join(problems) + "\n```"
    ghub.comment(m.get("issue"), msg)
    ghub.commit_and_push(f"Posted: {slug}")
    if not problems:
        ghub.close_issue(m.get("issue"))
    return True


def publish_next():
    approved = [i for i in ghub.all_items() if i["status"] == "approved"]
    if not approved:
        print("no approved posts waiting")
        return
    publish_slug(approved[0]["slug"])   # one set per day
