"""Shared settings. Change texts here if you want different wording on the ads."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
INCOMING = ROOT / "incoming"
QUEUE = ROOT / "queue"

BRAND = "BhaktiBox"
AD_LINE_1 = "MADE BY HAND, MADE WITH BHAKTI"
AD_LINE_2 = "हाथ से बना, भक्ति से सजा"
AD_BUTTON = "DM HI TO ORDER"

# Models are tried in this order until one works (Google renames models often).
# To force one, add a GitHub variable/secret GEMINI_MODEL.
GEMINI_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash"]

DRY_RUN = os.environ.get("DRY_RUN") == "1"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}
MAX_REEL_SECONDS = 90
AD_STYLE = "billboard"   # "billboard" = poster shown inside a street billboard photo, "poster" = flat poster, "classic" = photo + brand band
