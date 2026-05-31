"""
X-style corner watermark: official-look X badge + @USERNAME (bold italic, white).
Applied to final pipeline clips in step 6.

The watermark PNG is rendered at high resolution with supersampling, then
downscaled once by ffmpeg. Rendering big and scaling down (instead of drawing
tiny) is what keeps the badge and text crisp instead of blurry/compressed.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_FONT_PATH = _ASSETS_DIR / "fonts" / "LiberationSans-BoldItalic.ttf"
_LOGO_PATH = _ASSETS_DIR / "x_logo.png"
_CACHE_DIR = _ASSETS_DIR / "watermark_cache"

# --- Placement (fractions of the output frame) -----------------------------
# Logo badge height ~4% of frame height; lower-right, matching the reference.
WATERMARK_HEIGHT_RATIO = 0.040
MARGIN_RIGHT_RATIO = 0.035
MARGIN_BOTTOM_RATIO = 0.10

# --- Stored render resolution ----------------------------------------------
# Badge box side in the stored PNG (px). The text scales relative to this.
_STORE_BOX = 220
# Supersample factor: draw this much larger, then LANCZOS-downscale for AA
# (PIL does not anti-alias polygons/lines, so we lean on the downscale).
_SS = 4

DEFAULT_USERNAME = "ARYNNSGH"


def _resolve_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        _FONT_PATH,
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSansBoldOblique.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _load_x_badge(size: int) -> Image.Image:
    """The official X badge (images/x_logo.png), scaled to `size` px square."""
    logo = Image.open(_LOGO_PATH).convert("RGBA")
    return logo.resize((size, size), Image.LANCZOS)


def render_watermark_png(
    username: str = DEFAULT_USERNAME,
    reference_height: int = 1080,  # kept for call-site compatibility; render is fixed-res
) -> Path:
    """
    Render a transparent, high-resolution PNG watermark (badge + @handle).
    Cached on disk by username. ffmpeg scales it down per clip.
    """
    handle = username if username.startswith("@") else f"@{username}"
    handle = handle.upper()

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _CACHE_DIR / f"x_watermark_{handle.lstrip('@')}.png"
    if cache_path.exists():
        return cache_path

    box = _STORE_BOX * _SS
    gap = int(box * 0.26)

    # Size the font so the text's cap height is ~70% of the badge height,
    # matching the reference proportions, then re-measure for layout.
    target_text_h = int(box * 0.70)
    font = _resolve_font(box)
    probe = font.getbbox(handle)
    measured_h = max(1, probe[3] - probe[1])
    font = _resolve_font(max(8, int(box * target_text_h / measured_h)))

    bbox = font.getbbox(handle)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    shadow_off = max(1, box // 36)

    width = box + gap + text_w + shadow_off + box // 20
    height = box  # badge defines the height so the ffmpeg scale is exact
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    img.alpha_composite(_load_x_badge(box), (0, 0))

    text_x = box + gap
    text_y = (height - text_h) // 2 - bbox[1]

    # Soft drop shadow for legibility on bright backgrounds.
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.text(
        (text_x + shadow_off, text_y + shadow_off),
        handle,
        font=font,
        fill=(0, 0, 0, 170),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(1, box // 90)))
    img = Image.alpha_composite(img, shadow)

    draw = ImageDraw.Draw(img)
    draw.text((text_x, text_y), handle, font=font, fill=(255, 255, 255, 255))

    # Supersample down for smooth, anti-aliased edges.
    img = img.resize((width // _SS, height // _SS), Image.LANCZOS)

    img.save(cache_path, "PNG")
    logger.debug("Rendered watermark PNG: %s (%dx%d)", cache_path, *img.size)
    return cache_path


def _probe_video_size(video_path: Path) -> Tuple[int, int]:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and "x" in result.stdout.strip():
        w, h = result.stdout.strip().split("x")
        return int(w), int(h)
    return 1920, 1080


def apply_watermark(
    video_path: Path,
    username: str = DEFAULT_USERNAME,
    *,
    enabled: bool = True,
) -> bool:
    """
    Burn the X-style watermark into a clip (re-encodes video; copies audio).
    Overwrites the file in place on success.
    """
    if not enabled:
        return True
    if not video_path.exists():
        logger.error("Watermark skipped, file missing: %s", video_path)
        return False

    try:
        _, height = _probe_video_size(video_path)
        wm_path = render_watermark_png(username=username)

        with tempfile.NamedTemporaryFile(
            suffix=".mp4", dir=video_path.parent, delete=False
        ) as tmp:
            tmp_out = Path(tmp.name)

        # Scale the badge to a target pixel height (even number) once, with a
        # high-quality scaler, then overlay lower-right.
        wm_h = max(2, int(round(height * WATERMARK_HEIGHT_RATIO)) // 2 * 2)
        x_expr = f"W-w-W*{MARGIN_RIGHT_RATIO}"
        y_expr = f"H-h-H*{MARGIN_BOTTOM_RATIO}"
        filter_complex = (
            f"[1:v]scale=-1:{wm_h}:flags=lanczos[wm];"
            f"[0:v][wm]overlay={x_expr}:{y_expr}:format=auto"
        )

        # Encode for X/Twitter compatibility: H.264 High + yuv420p is the only
        # widely accepted combination. The source is often yuv444p, which X
        # rejects with a misleading "aspect ratio too small" error, so we force
        # the pixel format here (this is the single re-encode every clip passes
        # through). Audio is normalized to AAC for the same reason.
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(wm_path),
            "-filter_complex",
            filter_complex,
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(tmp_out),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if result.returncode != 0:
            logger.error("Watermark ffmpeg failed for %s: %s", video_path, result.stderr[-800:])
            tmp_out.unlink(missing_ok=True)
            return False

        tmp_out.replace(video_path)
        logger.info("Applied watermark to %s", video_path.name)
        return True
    except Exception as exc:
        logger.error("Watermark failed for %s: %s", video_path, exc)
        return False


def _probe_pix_fmt(video_path: Path) -> str:
    """Return the video stream's pixel format (e.g. 'yuv420p'), or '' on failure."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=pix_fmt",
        "-of",
        "default=nw=1:nk=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def ensure_twitter_compatible(video_path: Path) -> bool:
    """
    Guarantee a clip is accepted by X/Twitter's media pipeline.

    X only reliably accepts H.264 + yuv420p. The clipper extracts with stream
    copy (preserving the source's pixel format, often yuv444p), and X rejects
    yuv444p with a misleading "aspect ratio too small" error. apply_watermark()
    already re-encodes to yuv420p, so this is a safety net for the watermark-
    disabled / watermark-failed paths: it re-encodes ONLY when the pixel format
    is not already yuv420p, so marked clips are never touched twice.

    Overwrites the file in place on success. Returns True if the file is
    compatible afterwards (already-compatible files are a no-op success).
    """
    if not video_path.exists():
        logger.error("Compatibility check skipped, file missing: %s", video_path)
        return False

    pix_fmt = _probe_pix_fmt(video_path)
    if pix_fmt == "yuv420p":
        return True

    logger.info("Normalizing %s for X (pix_fmt=%r -> yuv420p)", video_path.name, pix_fmt or "unknown")
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".mp4", dir=video_path.parent, delete=False
        ) as tmp:
            tmp_out = Path(tmp.name)

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(tmp_out),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if result.returncode != 0:
            logger.error("Compatibility re-encode failed for %s: %s", video_path, result.stderr[-800:])
            tmp_out.unlink(missing_ok=True)
            return False

        tmp_out.replace(video_path)
        logger.info("Normalized %s for X", video_path.name)
        return True
    except Exception as exc:
        logger.error("Compatibility re-encode failed for %s: %s", video_path, exc)
        return False
