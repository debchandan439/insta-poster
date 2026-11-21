"""New photos in /incoming  ->  ad picture + reel + caption  ->  an Approve issue for the owner."""
import datetime
import os
import re
import shutil
import traceback
from . import adimage, captioner, config as C, ghub, reelmaker, videoprep


def _slug(name):
    base = re.sub(r"[^A-Za-z0-9]+", "-", os.path.splitext(name)[0]).strip("-")[:25] or "photo"
    return datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S-") + base


def _prepare_video(video):
    slug = _slug(video.name)
    d = C.QUEUE / slug
    d.mkdir(parents=True)
    try:
        videoprep.normalize(video, d / "reel.mp4")
        times = videoprep.frame_times(d / "reel.mp4")
        tmp = d / "_frames"
        tmp.mkdir()
        frames = []
        for i, t in enumerate(times):
            f = tmp / f"{i}.jpg"
            videoprep.grab(d / "reel.mp4", t, f, width=540)
            frames.append(f)
        category, title, caption, note, best = captioner.generate_frames(frames)
        if best is None:
            best = videoprep.sharpest(frames)
            note = (note + " " if note else "") + "AI could not pick the cover, so the sharpest frame was used."
        videoprep.grab(d / "reel.mp4", times[best], d / "cover.jpg")
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.move(str(video), str(d / ("original" + video.suffix.lower())))
        (d / "caption.txt").write_text(caption, encoding="utf-8")
        ghub.save(slug, {"slug": slug, "kind": "video", "status": "pending", "issue": 0,
                         "category": category, "title": title, "note": note, "caption": caption})
        print("prepared video", slug)
        return slug
    except Exception:
        traceback.print_exc()
        shutil.rmtree(d, ignore_errors=True)
        return None


def prepare_all():
    photos = [p for p in sorted(C.INCOMING.glob("*")) if p.suffix.lower() in C.IMAGE_EXTS]
    videos = [p for p in sorted(C.INCOMING.glob("*")) if p.suffix.lower() in C.VIDEO_EXTS]
    if not photos and not videos:
        print("incoming/ is empty, nothing to prepare")
        return
    created = []
    for v in videos:
        s = _prepare_video(v)
        if s:
            created.append(s)
    for photo in photos:
        slug = None
        try:
            slug = _slug(photo.name)
            d = C.QUEUE / slug
            d.mkdir(parents=True)
            category, title, caption, note = captioner.generate(photo)
            show_title = title if category in ("diya", "dhunuchi", "other") else ""
            ph, band, full = adimage.build(photo, show_title)
            full.save(d / "ad.jpg", quality=93)
            reelmaker.make(ph, band, d / "reel.mp4")
            shutil.move(str(photo), str(d / ("original" + photo.suffix.lower())))
            (d / "caption.txt").write_text(caption, encoding="utf-8")
            ghub.save(slug, {"slug": slug, "status": "pending", "issue": 0, "category": category,
                             "title": title, "note": note, "caption": caption})
            created.append(slug)
            print("prepared", slug, category)
        except Exception:
            traceback.print_exc()
            if slug:
                shutil.rmtree(C.QUEUE / slug, ignore_errors=True)
    if not created:
        return
    ghub.commit_and_push("Prepare new posts for approval")   # pictures must be online before the issue shows them
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    for slug in created:
        m = ghub.load(slug)
        base = f"https://raw.githubusercontent.com/{ghub.repo()}/main/queue/{slug}"
        pic = "cover" if m.get("kind") == "video" else "ad"
        pic_url = f"{base}/{'cover' if pic == 'cover' else 'ad'}.jpg"
        label = "থামবনেইল (কভার)" if pic == "cover" else "বিজ্ঞাপনের ছবি"
        body = f"""@{owner} নতুন পোস্ট তৈরি। দেখে সিদ্ধান্ত জানান.

**{label}:**

![{pic}]({pic_url})

**Reel (ভিডিও):** [দেখুন]({base}/reel.mp4)

**Caption:**

```
{m['caption']}
```
{('> ⚠️ ' + m['note']) if m['note'] else ''}

**কী লিখবেন (comment-এ):**
- `ok` → অনুমোদন. পরের সকাল ৯:৩০-এ পোস্ট হবে
- `post now` → অনুমোদন এবং এখনই পোস্ট
- `caption:` লিখে নিচে নতুন ক্যাপশন → ক্যাপশন বদলাবে (তারপর `ok` লিখুন)
- `skip` → বাতিল

<!-- slug: {slug} -->"""
        m["issue"] = ghub.new_issue(f"Approve: {m['title'] or slug}", body)
        ghub.save(slug, m)
    ghub.commit_and_push("Save issue numbers")
