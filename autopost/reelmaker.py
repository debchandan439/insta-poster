"""Turns the ad into a 7-second vertical video (slow zoom, text slides up)."""
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageFilter

W, H, FPS, SEC = 1080, 1920, 30, 7


def _ease(t):
    return 1 - (1 - t) ** 3


def make(photo, band, out):
    n = FPS * SEC
    ph, bh = photo.height, band.height
    top = (H - ph - bh) // 2
    bg = photo.copy()
    r = H / bg.height
    bg = bg.resize((int(bg.width * r) + 1, H))
    bg = bg.crop(((bg.width - W) // 2, 0, (bg.width - W) // 2 + W, H)).filter(ImageFilter.GaussianBlur(40))
    work = Path(tempfile.mkdtemp())
    try:
        for i in range(n):
            t = i / (n - 1)
            z = 1.0 + 0.10 * _ease(t)
            w, h = int(W * z), int(ph * z)
            p = photo.resize((w, h), Image.BILINEAR)
            p = p.crop(((w - W) // 2, (h - ph) // 2, (w - W) // 2 + W, (h - ph) // 2 + ph))
            fr = bg.copy()
            fr.paste(p, (0, top))
            s = min(max((i / FPS - 1.0) / 0.8, 0), 1)
            fr.paste(band, (0, top + ph + int((1 - _ease(s)) * 400)))
            fr.save(work / f"f{i:04d}.jpg", quality=92)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-framerate", str(FPS), "-i", str(work / "f%04d.jpg"),
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",  # silent audio track (Instagram is happier with one)
            "-vf", f"fade=t=in:st=0:d=0.4,fade=t=out:st={SEC - 0.4}:d=0.4",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(out),
        ], check=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
