"""Posts approved items (picture first, then the Reel)."""
from . import config as C, ghub, instagram


def publish_slug(slug):
    m = ghub.load(slug)
    base = f"https://raw.githubusercontent.com/{ghub.repo()}/main/queue/{slug}"
    caption = (C.QUEUE / slug / "caption.txt").read_text(encoding="utf-8")
    ok, problems = [], []
    for kind, url, fn in (("ছবি", f"{base}/ad.jpg", instagram.publish_image),
                          ("Reel", f"{base}/reel.mp4", instagram.publish_reel)):
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
    if not ok:
        m["status"] = "failed"
        ghub.save(slug, m)
        ghub.comment(m.get("issue"), "❌ পোস্ট হয়নি।\n\n```\n" + "\n".join(problems) + "\n```\nএই লেখাটার ছবি আমাকে পাঠান।")
        ghub.commit_and_push(f"Failed: {slug}")
        return False
    m["status"] = "posted"
    ghub.save(slug, m)
    msg = "✅ পোস্ট হয়েছে: " + ", ".join(ok)
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
