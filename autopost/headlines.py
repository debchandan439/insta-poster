"""Poster lines. Priority:  <photo>.txt  >  your Excel (one sheet per product)  >  headlines.txt  >  AI.

Excel: put it in the repo root (any .xlsx whose sheets are product names; a column called
"Billboard Line" and, optionally, "Your Notes / Brand Small Print" for the small text).
The product is known from the folder name:  incoming/Mitti Diya/photo.jpg   (or from the photo's file name).
"""
import datetime
import random
import re
from . import config as C

FILE = C.ROOT / "headlines.txt"
CATS = {"dress", "diya", "dhunuchi", "other", "any"}
SKIP_SHEETS = {"read me", "all 240", "all"}
DEFAULT_PRODUCTS = ["Laddu Gopal Poshak", "Wool Thala Posh", "Wool God Aasan", "Mitti Diya", "Mitti Dhunuchi",
                    "Mitti Glass", "Mitti Tea Cup", "Mitti Panchmukhi Pradip"]
# word in a photo/folder name -> product (checked top to bottom, so panchmukhi wins over diya)
ALIASES = [("panchmukhi", "Mitti Panchmukhi Pradip"), ("pradip", "Mitti Panchmukhi Pradip"),
           ("dhunuchi", "Mitti Dhunuchi"), ("dhuni", "Mitti Dhunuchi"),
           ("tea", "Mitti Tea Cup"), ("chai", "Mitti Tea Cup"), ("cup", "Mitti Tea Cup"),
           ("glass", "Mitti Glass"), ("aasan", "Wool God Aasan"), ("asan", "Wool God Aasan"),
           ("thala", "Wool Thala Posh"), ("thali", "Wool Thala Posh"),
           ("poshak", "Laddu Gopal Poshak"), ("laddu", "Laddu Gopal Poshak"), ("gopal", "Laddu Gopal Poshak"),
           ("dress", "Laddu Gopal Poshak"), ("diya", "Mitti Diya"), ("diye", "Mitti Diya")]
CATEGORY_OF = {"Laddu Gopal Poshak": "dress", "Mitti Diya": "diya", "Mitti Panchmukhi Pradip": "diya",
               "Mitti Dhunuchi": "dhunuchi"}
# A line that names a festival is used only in the months around it (months are 1-12).
FESTIVALS = {"diwali": {10, 11}, "deepawali": {10, 11}, "dhanteras": {10, 11}, "karwa": {10, 11},
             "chhath": {10, 11}, "kali puja": {10, 11}, "janmashtami": {8, 9}, "ganesh": {8, 9},
             "raksha": {7, 8}, "sawan": {7, 8}, "durga puja": {9, 10}, "navratri": {3, 4, 9, 10},
             "dussehra": {9, 10}, "dasara": {9, 10}, "holi": {2, 3}, "shivratri": {2, 3},
             "ram navami": {3, 4}, "hanuman jayanti": {3, 4}, "sankranti": {1}, "saraswati": {1, 2},
             "akshaya": {4, 5}, "ashtami": {9, 10}, "mahalaya": {9, 10}, "pujo": {9, 10}, "bhai dooj": {10, 11}, "govardhan": {10, 11}, "christmas": {12}, "new year": {12, 1}}


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def _xlsx():
    files = sorted(p for p in C.ROOT.glob("*.xlsx") if not p.name.startswith("~"))
    pref = [p for p in files if "billboard" in p.name.lower() or "line" in p.name.lower()]
    return (pref or files or [None])[0]


_cache = {}


def sheets():
    """{product name: [(line, small text), ...]} from the Excel."""
    if "s" in _cache:
        return _cache["s"]
    out = {}
    f = _xlsx()
    if f:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
            for ws in wb.worksheets:
                if ws.title.strip().lower() in SKIP_SHEETS:
                    continue
                rows = list(ws.iter_rows(values_only=True))
                hdr = next((i for i, r in enumerate(rows) if r and any(_norm(c) == "billboardline" for c in r if c)), None)
                if hdr is None:
                    continue
                head = [_norm(c) for c in rows[hdr]]
                li = head.index("billboardline")
                ni = next((i for i, h in enumerate(head) if h.startswith("yournotes") or "smallprint" in h), None)
                items = []
                for r in rows[hdr + 1:]:
                    line = str(r[li]).strip() if li < len(r) and r[li] else ""
                    note = str(r[ni]).strip() if ni is not None and ni < len(r) and r[ni] else ""
                    if line:
                        items.append((line, note))
                if items:
                    out[ws.title.strip()] = items
        except Exception as e:  # noqa
            print("could not read the Excel:", type(e).__name__, e)
    _cache["s"] = out
    return out


def products():
    return list(sheets()) or DEFAULT_PRODUCTS


def canon(name):
    """Any spelling of a product name -> the exact sheet/product name (or None)."""
    if not name:
        return None
    n = _norm(name)
    for p in products():
        if _norm(p) == n:
            return p
    for p in products():
        if n and (n in _norm(p) or _norm(p) in n):
            return p
    return None


def product_from_path(photo):
    """Folder name first (incoming/<product>/photo.jpg), then the photo's own name."""
    for text in (photo.parent.name if photo.parent != C.INCOMING else "", photo.stem):
        p = canon(text)
        if p:
            return p
        t = text.lower()
        for word, prod in ALIASES:
            if word in t:
                return canon(prod) or prod
    return None


def category_of(product):
    return CATEGORY_OF.get(product, "other")


def _season_ok(line, today=None):
    month = (today or datetime.date.today()).month
    low = line.lower()
    for word, months in FESTIVALS.items():
        if word in low and month not in months:
            return False
    return True


def _recent():
    try:
        from . import ghub
        return {i.get("headline", "") for i in ghub.all_items()}
    except Exception:  # noqa
        return set()


def _txt_lines():
    items = []
    if FILE.exists():
        for raw in FILE.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            parts = [p.strip() for p in raw.split("|")]
            if len(parts) >= 2 and parts[0].lower() in CATS and parts[1]:
                items.append((parts[0].lower(), parts[1], parts[2] if len(parts) > 2 else ""))
    return items


def choose(category, photo_path=None, product=None):
    """Returns {"headline", "subline"?, "product"?} or None (then the AI writes the line)."""
    if photo_path is not None:
        t = photo_path.with_suffix(".txt")
        if t.exists():
            lines = [l.strip() for l in t.read_text(encoding="utf-8").splitlines() if l.strip()]
            t.unlink()
            if lines:
                parts = [p.strip() for p in lines[0].split("|")]
                out = {"headline": parts[0][:90]}
                if len(parts) > 1 and parts[1]:
                    out["subline"] = parts[1][:80]
                return out
    seen = _recent()
    if product and product in sheets():
        pool = [(l, n) for l, n in sheets()[product] if _season_ok(l)] or sheets()[product]
        fresh = [p for p in pool if p[0] not in seen] or pool       # every line once before any repeats
        line, note = random.choice(fresh)
        return {"headline": line[:90], "subline": note[:80] if note else f"Handmade {product}", "product": product}
    pool = [(h, s) for c, h, s in _txt_lines() if c in (category, "any")]
    if not pool:
        return None
    fresh = [p for p in pool if p[0] not in seen] or pool
    h, s = random.choice(fresh)
    return {"headline": h[:90], **({"subline": s[:80]} if s else {})}
