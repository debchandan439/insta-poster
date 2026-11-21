"""Puts the poster inside a street billboard photo (assets/billboard.jpg).
Feed picture = billboard scene 4:5. Reel = same scene, brand strip slides up."""
from PIL import Image, ImageDraw, ImageFilter
from . import config as C, poster

W, FEED_H = 1080, 1350
ZOOM = 1.35   # how close the camera is to the billboard


def _panel_box(im):
    """Finds the white panel by flood-filling from the middle of the picture."""
    g = im.convert("RGB")
    mask = Image.new("L", g.size, 0)
    px, mp = g.load(), mask.load()
    for y in range(g.height):
        for x in range(g.width):
            mp[x, y] = 255 if min(px[x, y]) > 205 else 0
    ImageDraw.floodfill(mask, (g.width // 2, g.height // 2), 128)
    box = mask.point(lambda v: 255 if v == 128 else 0).getbbox()
    return box


def build(path, headline, subline=""):
    """Returns (scene_part, strip_part, feed_image)."""
    mock = Image.open(C.ASSETS / "billboard.jpg").convert("RGB")
    x0, y0, x1, y1 = _panel_box(mock)
    x0, y0, x1, y1 = x0 + 2, y0 + 2, x1 - 2, y1 - 2          # stay inside the frame
    s = W * ZOOM / mock.width
    scene = mock.resize((int(mock.width * s), int(mock.height * s)), Image.LANCZOS)
    bx0, by0, bx1, by1 = (int(v * s) for v in (x0, y0, x1, y1))
    pw, ph = bx1 - bx0, by1 - by0
    big_h = round(poster.W * ph / pw)
    art, strip, full = poster.build(path, headline, subline, height=big_h)
    art = full.resize((pw, ph), Image.LANCZOS)
    # soft light on the glass + faint inner shadow so it looks printed into the frame
    gloss = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gloss)
    gd.polygon([(0, 0), (int(pw * 0.7), 0), (0, int(ph * 0.45))], fill=(255, 255, 255, 26))
    art = Image.alpha_composite(art.convert("RGBA"), gloss).convert("RGB")
    scene.paste(art, (bx0, by0))
    edge = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    ImageDraw.Draw(edge).rectangle([bx0, by0, bx1, by1], outline=(0, 0, 0, 90), width=3)
    scene = Image.alpha_composite(scene.convert("RGBA"), edge.filter(ImageFilter.GaussianBlur(1.5))).convert("RGB")
    cy, cx = (by0 + by1) // 2, (bx0 + bx1) // 2
    top = max(0, min(scene.height - FEED_H, cy - FEED_H // 2 - 40))
    left = max(0, min(scene.width - W, cx - W // 2))
    feed = scene.crop((left, top, left + W, top + FEED_H))
    max_h = 1920 - 170          # the Reel is 1080x1920 and also carries the brand strip
    rt = max(0, min(scene.height - max_h, cy - max_h // 2))
    reel_scene = scene.crop((left, rt, left + W, rt + max_h))
    return reel_scene, poster._strip(poster.accent_from(Image.open(path).convert("RGB")) if False else _accent(path)), feed


def _accent(path):
    src = Image.open(path)
    prod, accent = poster._product(src)
    return accent
