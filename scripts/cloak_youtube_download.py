#!/usr/bin/env python3
"""Capture YouTube googlevideo URLs via CloakBrowser network interception."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _download(url: str, dest: Path) -> None:
    import urllib.request

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.youtube.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=900) as resp, open(dest, "wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def capture_and_download(url: str, output_dir: Path) -> tuple[Path, str]:
    from cloakbrowser import launch

    output_dir.mkdir(parents=True, exist_ok=True)
    media_urls: list[str] = []

    browser = launch(headless=True)
    try:
        context = browser.new_context(locale="en-US", timezone_id="America/New_York")
        page = context.new_page()

        def on_response(response):
            try:
                u = response.url
                if "googlevideo.com/videoplayback" in u and response.status == 200:
                    media_urls.append(u)
            except Exception:
                pass

        page.on("response", on_response)
        print(f"CloakBrowser: opening {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        time.sleep(3)

        title = page.title().replace(" - YouTube", "").strip() or "youtube_video"

        # Try to start playback so googlevideo requests fire
        for selector in (
            "button.ytp-large-play-button",
            "button.ytp-play-button",
            "video.html5-main-video",
        ):
            try:
                page.locator(selector).first.click(timeout=3000)
                break
            except Exception:
                continue

        # Also try keyboard shortcut
        try:
            page.keyboard.press("k")
        except Exception:
            pass

        deadline = time.time() + 45
        while time.time() < deadline and len(media_urls) < 2:
            time.sleep(1)

        if not media_urls:
            raise RuntimeError("No googlevideo URLs captured — playback may be blocked")

        # Prefer itag=22 (720p mp4) or highest itag in URL
        def score(u: str) -> tuple[int, int]:
            itag_match = re.search(r"[?&]itag=(\d+)", u)
            itag = int(itag_match.group(1)) if itag_match else 0
            height_match = re.search(r"[?&]clen=(\d+)", u)
            size = int(height_match.group(1)) if height_match else 0
            return (itag, size)

        media_urls.sort(key=score, reverse=True)
        chosen = media_urls[0]
        print(f"Captured {len(media_urls)} media URLs; downloading best candidate...")

        dest = output_dir / "video.mp4"
        _download(chosen, dest)
        return dest, title
    finally:
        browser.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("-o", "--output-dir", type=Path, default=PROJECT_ROOT / "data" / "temp" / "cloak-dl")
    args = parser.parse_args()
    video, title = capture_and_download(args.url, args.output_dir)
    print(json.dumps({"title": title, "video": str(video)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
