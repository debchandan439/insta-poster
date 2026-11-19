"""Shared settings. Change texts here if you want different wording on the ads."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
INCOMING = ROOT / "incoming"
QUEUE = ROOT / "queue"

BRAND = "BhaktiBox"
AD_LINE_1 = "ALL ARE HANDMADE"
AD_LINE_2 = "सब कुछ हाथ से बना"
AD_BUTTON = "DM ME FOR PRICE"

# Models are tried in this order until one works (Google renames models often).
# To force one, add a GitHub variable/secret GEMINI_MODEL.
GEMINI_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash"]

DRY_RUN = os.environ.get("DRY_RUN") == "1"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
