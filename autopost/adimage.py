"""Builds the ad picture: product photo on top, brand band at the bottom."""
import colorsys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from . import config as C

W, H, BAND = 1080, 1350, 300
PH = H - BAND


def font(name, size):
    return ImageFont.truetype(str(C.ASSETS / "fonts" / name), size)


def cover(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def accent_from(im):
    """Pick a strong colour from the photo for the button and top line."""
    small = im.convert("RGB").resize((64, 64))
    buckets = {}
    for r, g, b in small.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s > 0.45 and 0.3 < v < 0.97:
            buckets.setdefault(int(h * 12) % 12, []).append((r, g, b))
    if not buckets:
        return (160, 60, 30)
    best = max(buckets.values(), key=len)
    r, g, b = (sum(p[i] for p in best) // len(best) for i in range(3))
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    r, g, b = colorsys.hsv_to_rgb(h, min(1, s + 0.1), min(v, 0.72))
    return (int(r * 255), int(g * 255), int(b * 255))


def _photo_scene(prod, title, accent):
    """Cut-out product (transparent PNG) on a warm golden background."""
    top, bottom = (255, 243, 224), (247, 214, 170)
    bg = Image.new("RGB", (W, PH))
    px = bg.load()
    for y in range(PH):
        t = y / PH
        c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(W):
            px[x, y] = c
    glow = Image.new("RGBA", (W, PH), (0, 0, 0, 0))
    cx, cy = W // 2, PH // 2 + 40
    ImageDraw.Draw(glow).ellipse([cx - 420, cy - 420, cx + 420, cy + 420], fill=(255, 240, 210, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    bg.paste(glow, (0, 0), glow)
    r = min(900 / prod.width, (PH - 260) / prod.height, 640 / prod.width * 1.45)
    p = prod.resize((int(prod.width * r), int(prod.height * r)), Image.LANCZOS)
    x, y = (W - p.width) // 2, (PH - p.height) // 2 + 30
    sh = Image.new("L", (W, PH), 0)
    ImageDraw.Draw(sh).ellipse([x + 30, y + p.height - 30, x + p.width - 30, y + p.height + 30], fill=110)
    bg.paste((60, 30, 10), (0, 0), sh.filter(ImageFilter.GaussianBlur(18)))
    bg.paste(p, (x, y), p)
    if title:
        d = ImageDraw.Draw(bg)
        size = 52
        while size > 28 and d.textlength(title, font=font("Poppins-Bold.ttf", size)) > W - 80:
            size -= 2
        f = font("Poppins-Bold.ttf", size)
        d.text(((W - d.textlength(title, font=f)) / 2, 60), title, font=f, fill=accent)
    return bg


def _photo_plain(img):
    """Normal photo: fill the frame, or fit it (with margins) if it is a wide shot."""
    if img.width / img.height > 1.25:
        iw, ih = img.size
        img = img.crop((0, int(ih * 0.10), iw, int(ih * 0.98)))
        edge = img.getpixel((img.width // 2, img.height - 8))
        bg = Image.new("RGB", (W, PH), edge)
        r = min((W - 70) / img.width, PH / img.height)
        im2 = img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS)
        bg.paste(im2, ((W - im2.width) // 2, (PH - im2.height) // 2))
        return bg
    return cover(img, W, PH)


def _band(accent):
    bgc = (253, 252, 248)
    band = Image.new("RGB", (W, BAND), bgc)
    d = ImageDraw.Draw(band)
    d.rectangle([0, 0, W, 8], fill=accent)
    band.paste(Image.open(C.ASSETS / "logo_small.png").convert("RGB"), (40, 55))
    d.text((270, 50), C.AD_LINE_1, font=font("Poppins-Bold.ttf", 44), fill=(120, 50, 20))
    d.text((270, 112), C.AD_LINE_2, font=font("Poppins-Medium.ttf", 34), fill=(150, 100, 40))
    bx, by, bw, bh = 270, 175, 470, 76
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=38, fill=accent)
    f = font("Poppins-Bold.ttf", 34)
    d.text((bx + (bw - d.textlength(C.AD_BUTTON, font=f)) / 2, by + 16), C.AD_BUTTON, font=f, fill=(255, 255, 255))
    return band


def build(path, title=""):
    """Returns (photo_part, band_part, full_ad_image)."""
    src = Image.open(path)
    has_alpha = src.mode in ("RGBA", "LA") and src.getchannel("A").getextrema()[0] < 250
    if has_alpha:
        src = src.convert("RGBA")
        src = src.crop(src.getchannel("A").getbbox())
        flat = Image.new("RGB", src.size, (255, 255, 255))
        flat.paste(src, (0, 0), src)
        accent = accent_from(flat)
        photo = _photo_scene(src, title, accent)
    else:
        rgb = src.convert("RGB")
        accent = accent_from(rgb)
        photo = _photo_plain(rgb)
    band = _band(accent)
    full = Image.new("RGB", (W, H))
    full.paste(photo, (0, 0))
    full.paste(band, (0, PH))
    return photo, band, full
