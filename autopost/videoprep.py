"""Your own video -> Reel-ready video (1080x1920) + the best cover picture."""
import subprocess
from PIL import Image, ImageFilter, ImageStat
from . import config as C

FRAMES = 10


def _out(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def duration(path):
    return min(float(_out("ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path))), C.MAX_REEL_SECONDS)


def has_audio(path):
    return bool(_out("ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                     "stream=index", "-of", "csv=p=0", str(path)))


def normalize(src, dst):
    """9:16, H.264 + AAC, at most 90 s. Wide videos get a blurred background."""
    vf = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5[bg];"
          "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
          "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src)]
    if has_audio(src):
        cmd += ["-filter_complex", vf, "-map", "[v]", "-map", "0:a:0"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", vf,
                "-map", "[v]", "-map", "1:a", "-shortest"]
    cmd += ["-t", str(C.MAX_REEL_SECONDS), "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True)


def frame_times(video):
    d = duration(video)
    return [d * (i + 0.5) / FRAMES for i in range(FRAMES)]


def grab(video, t, out, width=None):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1"]
    if width:
        cmd += ["-vf", f"scale={width}:-2"]
    subprocess.run(cmd + ["-q:v", "2", str(out)], check=True)


def sharpest(paths):
    """Fallback when AI gives no answer: the frame with the most detail."""
    def score(p):
        g = Image.open(p).convert("L").filter(ImageFilter.FIND_EDGES)
        return ImageStat.Stat(g).stddev[0]
    return max(range(len(paths)), key=lambda i: score(paths[i]))
