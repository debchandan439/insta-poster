"""Asks Google Gemini to look at the photo and write the caption + hashtags."""
import base64
import datetime
import io
import json
import os
import re
import urllib.error
import urllib.request
from PIL import Image
from . import config as C

PROMPT = """You write Instagram posts for {brand}, a small Indian shop that sells handmade puja items:
Laddu Gopal / Radha Rani dresses (poshak), mitti (clay) diyas and mitti dhunuchi.
Look at the product photo and answer ONLY with JSON: {{"category": "...", "title_en": "...", "caption": "..."}}

category: one of dress, diya, dhunuchi, other.
title_en: 2-4 English words naming the product, e.g. "Handmade Mitti Diya Set".
caption rules:
- Mix Hindi (Devanagari) and English, warm devotional tone, 6-9 short lines, a few fitting emojis.
- Describe only what you can actually SEE (colours, lace/zari work, design, how it is shown).
- Say it is handmade. End the text lines with a call to action to DM for price.
- Do NOT invent price, size, material, offers, discounts, delivery or stock claims.
  Mention a size only if it is clearly written in the photo.
- No markdown, no asterisks.
- After a blank line add 12-15 hashtags: always #{brand}; then product, devotional and festival tags that
  fit the photo. Today is {today}; add a festival tag only if a major festival (Diwali, Kali Puja,
  Durga Puja, Janmashtami, Ram Navami etc.) is within about 3 weeks. These are relevant tags, not a
  claim about what is trending today.
"""

FALLBACK = {
    "dress": ("Handmade Laddu Gopal Dress", "✨ नन्हे कान्हा के लिए सुंदर हाथ से बनी पोशाक 💛\nHandmade with love, with beautiful lace work. 🙏\nDM for price. 🛍️\n\n#BhaktiBox #LadduGopal #LadduGopalDress #KanhaJi #ThakurJiDress #HandmadePoshak #KrishnaBhakti #BalGopal #HinduDevotional"),
    "diya": ("Handmade Mitti Diya", "🪔 हाथ से बने मिट्टी के दीये, आपकी पूजा के लिए।\nHandmade clay diyas to light up your puja. ✨\nDM for price. 🛍️\n\n#BhaktiBox #MittiDiya #HandmadeDiya #ClayDiya #DiwaliDecor #PujaEssentials #HinduDevotional"),
    "dhunuchi": ("Handmade Mitti Dhunuchi", "🙏 हाथ से बनी मिट्टी की धुनुची, पूजा और आरती के लिए।\nHandmade clay dhunuchi for your puja. ✨\nDM for price. 🛍️\n\n#BhaktiBox #Dhunuchi #MittiDhunuchi #DurgaPuja #PujaEssentials #HandmadeDhunuchi #HinduDevotional"),
    "other": ("Handmade Puja Item", "🙏 हाथ से बना पूजा का सामान।\nHandmade with love. ✨ DM for price. 🛍️\n\n#BhaktiBox #HandmadePuja #PujaEssentials #HinduDevotional"),
}


def _jpeg_b64(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((1024, 1024))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


VIDEO_NOTE = """
The images are {n} frames taken in order from one short video (numbered 0 to {last}).
Write the caption for the whole video. Also add a JSON field "best_frame": the number of the single
frame that makes the best cover picture (product clearly visible, sharp, well lit, nice composition,
not blurred, not mid-transition). Answer ONLY with JSON: {{"category": "...", "title_en": "...", "caption": "...", "best_frame": 0}}
"""


def _ask(model, key, b64s, video=False):
    prompt = PROMPT.format(brand=C.BRAND, today=datetime.date.today().isoformat())
    if video:
        prompt += VIDEO_NOTE.format(n=len(b64s), last=len(b64s) - 1)
    parts = [{"text": prompt}] + [{"inline_data": {"mime_type": "image/jpeg", "data": b}} for b in b64s]
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def clean(caption):
    caption = caption.replace("**", "").replace("__", "").strip()
    return re.sub(r"\n{3,}", "\n\n", caption)[:2100]


def generate(image_path):
    """Returns (category, title, caption, note). note explains any fallback."""
    cat, title, cap, note, _ = generate_frames([image_path], video=False)
    return cat, title, cap, note


def generate_frames(paths, video=True):
    """Returns (category, title, caption, note, best_frame or None)."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        t = FALLBACK["other"]
        return "other", t[0], t[1], "GEMINI_API_KEY secret missing, so a plain template caption was used.", None
    models = ([os.environ["GEMINI_MODEL"]] if os.environ.get("GEMINI_MODEL") else []) + C.GEMINI_MODELS
    b64s, errors = [_jpeg_b64(p) for p in paths], []
    for m in models:
        try:
            out = _ask(m, key, b64s, video)
            cat = out.get("category", "other")
            cat = cat if cat in FALLBACK else "other"
            cap = clean(out["caption"])
            if f"#{C.BRAND}".lower() not in cap.lower():
                cap += f"\n\n#{C.BRAND}"
            best = out.get("best_frame")
            best = best if isinstance(best, int) and 0 <= best < len(paths) else None
            return cat, str(out.get("title_en", ""))[:40], cap, "", best
        except urllib.error.HTTPError as e:
            errors.append(f"{m}: HTTP {e.code}")
        except Exception as e:  # noqa
            errors.append(f"{m}: {type(e).__name__}")
    t = FALLBACK["other"]
    return "other", t[0], t[1], "AI caption failed (" + "; ".join(errors) + "), so a plain template caption was used. Please edit it.", None
