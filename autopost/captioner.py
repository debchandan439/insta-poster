"""Asks Google Gemini to look at the photo and write the caption + hashtags."""
import base64
import datetime
import io
import json
import os
import random
import re
import urllib.error
import urllib.request
from PIL import Image
from . import config as C

PROMPT = """You write Instagram posts for {brand}, a small Indian shop that sells handmade puja items:
Laddu Gopal / Radha Rani dresses (poshak), mitti (clay) diyas and mitti dhunuchi.
Look at the product photo and answer ONLY with JSON:
{{"category": "...", "title_en": "...", "headline": "...", "subline": "...", "caption": "..."}}

headline: ONE witty poster line in Hinglish (Hindi written in English letters), 3-7 words, like Indian brand
  billboards (Blinkit, Swiggy, Zomato): everyday language, wordplay, rhyme or a cheeky twist that fits the product
  and the season. Original, not a copy of any brand's line. No price, discount, offer or delivery promise.
  Style examples only (never reuse them): "Roshni wahi, jo haath se bani." / "Safai ho gayi? Ab roshni ki baari." /
  "Kanha ji ke kapde, kanha ji ke nakhre." / "Aarti ka asli mazaa, dhunuchi ke saath."
  Every poster must feel different: vary the sentence shape, mood and opening word.
subline: 4-8 words in simple English or Hinglish saying what the product is, e.g. "Handmade mitti diye for your puja".

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
not blurred, not mid-transition). Answer ONLY with JSON: {{"category": "...", "title_en": "...", "headline": "...", "subline": "...", "caption": "...", "best_frame": 0}}
"""


def _ask(model, key, b64s, video=False, extra=""):
    prompt = PROMPT.format(brand=C.BRAND, today=datetime.date.today().isoformat()) + extra
    if video:
        prompt += VIDEO_NOTE.format(n=len(b64s), last=len(b64s) - 1)
    parts = [{"text": prompt}] + [{"inline_data": {"mime_type": "image/jpeg", "data": b}} for b in b64s]
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


HEADLINES = {
    "dress": [("Kanha ji ka look, ekdum perfect.", "Handmade poshak for Laddu Gopal"),
              ("Kanha ji ke kapde, kanha ji ke nakhre.", "Handmade Laddu Gopal dress"),
              ("Aaj Kanha ji kya pehnenge?", "Handmade poshak, every piece unique"),
              ("Chhote Thakur, bade shaunk.", "Handmade dress for Laddu Gopal")],
    "diya": [("Roshni wahi, jo haath se bani.", "Handmade mitti diye for your puja"),
             ("Diya jalao, dil bhi roshan karo.", "Handmade clay diyas"),
             ("Safai ho gayi? Ab roshni ki baari.", "Handmade mitti diye for your home"),
             ("Har diye mein kumhaar ki mehnat.", "Handmade clay diyas by BhaktiBox")],
    "dhunuchi": [("Dhak bajao, dhunuchi jalao.", "Handmade mitti dhunuchi for your aarti"),
                 ("Aarti ka asli mazaa, dhunuchi ke saath.", "Handmade clay dhunuchi"),
                 ("Dhuan uthe, bhakti jage.", "Handmade mitti dhunuchi")],
    "other": [("Pooja ki taiyari, haath se bani.", "Handmade with love by BhaktiBox"),
              ("Mandir ki shaan, haath ki kaarigari.", "Handmade puja items"),
              ("Bhakti mein sajaavat, sajaavat mein bhakti.", "Handmade by BhaktiBox")],
}
ANGLES = [
    "a twist on a well-known Hindi saying or idiom",
    "a rhyme or a two-part line with a punch at the end",
    "a funny relatable everyday moment (cleaning, guests coming, mom's orders)",
    "a cheeky question to the viewer",
    "a proud line about the craft and the potter's hands",
    "a playful 'pehle ... phir ...' style line",
    "a warm festive or seasonal line (only if it truly fits this time of year)",
]


def _recent_headlines(n=12):
    try:
        from . import ghub
        hs = [i.get("headline", "") for i in ghub.all_items() if i.get("headline")]
        return hs[-n:]
    except Exception:  # noqa
        return []
LAST = {}   # headline/subline of the most recent generate() call


def clean(caption):
    caption = caption.replace("**", "").replace("__", "").strip()
    return re.sub(r"\n{3,}", "\n\n", caption)[:2100]


def generate(image_path, product=None):
    """Returns (category, title, caption, note). note explains any fallback."""
    cat, title, cap, note, _ = generate_frames([image_path], video=False, product=product)
    return cat, title, cap, note


def generate_frames(paths, video=True, product=None):
    """Returns (category, title, caption, note, best_frame or None)."""
    LAST.clear()
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        t = FALLBACK["other"]
        LAST.update(zip(("headline", "subline"), random.choice(HEADLINES["other"])))
        return "other", t[0], t[1], "GEMINI_API_KEY secret missing, so a plain template caption was used.", None
    models = ([os.environ["GEMINI_MODEL"]] if os.environ.get("GEMINI_MODEL") else []) + C.GEMINI_MODELS
    b64s, errors = [_jpeg_b64(p) for p in paths], []
    recent = _recent_headlines()
    from . import headlines as H
    if product:
        extra_p = f"\nThe product in this photo is exactly: {product}. Write about this product.\n"
    else:
        extra_p = ("\nAlso add the JSON field \"product\": the best match from this list: "
                   + ", ".join(H.products()) + ", or \"other\".\n")
    extra = extra_p + f"\nFor the headline use this style this time: {random.choice(ANGLES)}.\n"
    if recent:
        extra += "Earlier headlines, so do NOT repeat or closely resemble them: " + " | ".join(recent) + "\n"
    for m in models:
        try:
            out = _ask(m, key, b64s, video, extra)
            cat = out.get("category", "other")
            cat = cat if cat in FALLBACK else "other"
            cap = clean(out["caption"])
            if f"#{C.BRAND}".lower() not in cap.lower():
                cap += f"\n\n#{C.BRAND}"
            hd = random.choice(HEADLINES[cat])
            LAST["product"] = product or H.canon(out.get("product")) or ""
            if product:
                cat = H.category_of(product)
            elif LAST["product"]:
                cat = H.category_of(LAST["product"])
            LAST["headline"] = (str(out.get("headline") or "").strip()[:60]) or hd[0]
            LAST["subline"] = (str(out.get("subline") or "").strip()[:60]) or hd[1]
            best = out.get("best_frame")
            best = best if isinstance(best, int) and 0 <= best < len(paths) else None
            return cat, str(out.get("title_en", ""))[:40], cap, "", best
        except urllib.error.HTTPError as e:
            errors.append(f"{m}: HTTP {e.code}")
        except Exception as e:  # noqa
            errors.append(f"{m}: {type(e).__name__}")
    t = FALLBACK["other"]
    LAST.update(zip(("headline", "subline"), random.choice(HEADLINES["other"])))
    return "other", t[0], t[1], "AI caption failed (" + "; ".join(errors) + "), so a plain template caption was used. Please edit it.", None
