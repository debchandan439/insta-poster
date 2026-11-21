"""Billboard-style poster: bold colour, witty one-line headline, product big, brand strip at the bottom."""
import colorsys
from PIL import Image, ImageDraw, ImageFilter
from . import config as C
from .adimage import accent_from, font, cover

W, H, STRIP = 1080, 1350, 170
PH = H - STRIP


def _wrap(d, text, f, maxw):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def _fit_headline(d, text, maxw, maxh, start=118):
    for size in range(start, 40, -4):
        f = font("Poppins-Bold.ttf", size)
        lines = _wrap(d, text, f, maxw)
        if len(lines) * size * 1.18 <= maxh and all(d.textlength(l, font=f) <= maxw for l in lines):
            return f, lines, size
    f = font("Poppins-Bold.ttf", 40)
    return f, _wrap(d, text, f, maxw), 40


def _bg_colour(accent):
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in accent))
    r, g, b = colorsys.hsv_to_rgb(h, max(s, 0.75), 0.80)
    return (int(r * 255), int(g * 255), int(b * 255))


def _shadow(canvas, im, xy, alpha):
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    mask = alpha if alpha.mode == "L" else alpha.convert("L")
    blk = Image.new("RGBA", im.size, (0, 0, 0, 120))
    sh.paste(blk, (xy[0] + 14, xy[1] + 22), mask)
    sh = sh.filter(ImageFilter.GaussianBlur(20))
    canvas.paste(sh, (0, 0), sh)


def _product(src):
    """Returns (RGBA image, accent). Cut-outs keep their shape, plain photos become a rounded card."""
    has_alpha = src.mode in ("RGBA", "LA") and src.getchannel("A").getextrema()[0] < 250
    if has_alpha:
        src = src.convert("RGBA")
        src = src.crop(src.getchannel("A").getbbox())
        flat = Image.new("RGB", src.size, (255, 255, 255))
        flat.paste(src, (0, 0), src)
        return src, accent_from(flat)
    rgb = src.convert("RGB")
    return rgb.convert("RGBA"), accent_from(rgb)


def _rounded(im, radius=36):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=radius, fill=255)
    out = im.copy()
    out.putalpha(m)
    return out


def build(path, headline, subline="", height=H):
    """Returns (poster_part, strip_part, full_image)."""
    PH = height - STRIP
    prod, accent = _product(Image.open(path))
    is_card = prod.getchannel("A").getextrema()[0] == 255
    bg = _bg_colour(accent)
    light_bg = sum(bg) / 3 > 170
    ink = (60, 25, 10) if light_bg else (255, 255, 255)
    soft = (95, 55, 30) if light_bg else (255, 232, 200)

    poster = Image.new("RGB", (W, PH), bg)
    d = ImageDraw.Draw(poster)
    # soft light spot + thin inner frame, like a printed billboard
    spot = Image.new("RGBA", (W, PH), (0, 0, 0, 0))
    ImageDraw.Draw(spot).ellipse([W * 0.25, PH * 0.35, W * 1.15, PH * 1.2], fill=(255, 255, 255, 55))
    spot = spot.filter(ImageFilter.GaussianBlur(90))
    poster.paste(spot, (0, 0), spot)
    d = ImageDraw.Draw(poster)
    d.rectangle([22, 22, W - 23, PH - 23], outline=soft, width=3)

    wide = prod.width / prod.height > 1.05
    if wide:   # headline on top, product below
        f, lines, size = _fit_headline(d, headline, W - 130, 330, 112)
        y = 80
        for ln in lines:
            d.text((65, y), ln, font=f, fill=ink)
            y += int(size * 1.18)
        sf = font("Poppins-Medium.ttf", 36)
        if subline:
            d.text((65, y + 14), subline, font=sf, fill=soft)
        top = y + 100
        area = (W - 120, PH - top - 50)
        r = min(area[0] / prod.width, area[1] / prod.height)
        p = prod.resize((int(prod.width * r), int(prod.height * r)), Image.LANCZOS)
        x, yy = (W - p.width) // 2, top + (area[1] - p.height) // 2
    else:      # headline left, product right
        f, lines, size = _fit_headline(d, headline, 500, 760, 104)
        y = 110
        for ln in lines:
            d.text((65, y), ln, font=f, fill=ink)
            y += int(size * 1.18)
        sf = font("Poppins-Medium.ttf", 34)
        if subline:
            for ln in _wrap(d, subline, sf, 480):
                d.text((65, y + 24), ln, font=sf, fill=soft)
                y += 46
        area = (500, PH - 130)
        r = min(area[0] / prod.width, area[1] / prod.height)
        p = prod.resize((int(prod.width * r), int(prod.height * r)), Image.LANCZOS)
        x, yy = W - p.width - 55, PH - p.height - 70
    if is_card:
        p = _rounded(p)
    _shadow(poster, p, (x, yy), p.getchannel("A"))
    poster.paste(p, (x, yy), p)

    strip = _strip(accent)
    full = Image.new("RGB", (W, height))
    full.paste(poster, (0, 0))
    full.paste(strip, (0, PH))
    return poster, strip, full


def _strip(accent):
    s = Image.new("RGB", (W, STRIP), (253, 252, 248))
    d = ImageDraw.Draw(s)
    logo = Image.open(C.ASSETS / "logo_small.png").convert("RGB")
    r = (STRIP - 30) / logo.height
    logo = logo.resize((int(logo.width * r), int(logo.height * r)), Image.LANCZOS)
    s.paste(logo, (35, 15))
    tx = 35 + logo.width + 30
    d.text((tx, 32), C.AD_LINE_1, font=font("Poppins-Bold.ttf", 30), fill=(120, 50, 20))
    d.text((tx, 78), C.AD_LINE_2, font=font("Poppins-Medium.ttf", 26), fill=(150, 100, 40))
    f = font("Poppins-Bold.ttf", 28)
    bw = int(d.textlength(C.AD_BUTTON, font=f)) + 56
    bx = W - bw - 35
    d.rounded_rectangle([bx, 48, bx + bw, 122], radius=37, fill=accent)
    d.text((bx + 28, 64), C.AD_BUTTON, font=f, fill=(255, 255, 255))
    return s
