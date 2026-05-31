#!/usr/bin/env python3
"""
Download a YouTube video and run the AutoClip pipeline synchronously (no Celery).

Usage:
  .venv/bin/python scripts/run_youtube_pipeline.py "https://youtu.be/VIDEO_ID"
  .venv/bin/python scripts/run_youtube_pipeline.py URL --cookies data/youtube_cookies.txt
  .venv/bin/python scripts/run_youtube_pipeline.py URL --proxy socks5://127.0.0.1:1080
  .venv/bin/python scripts/run_youtube_pipeline.py --video /path/to/file.mp4 --srt /path/to/file.srt --name "My Podcast"
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("run_youtube_pipeline")


def _resolve_node_binary() -> str | None:
    """yt-dlp needs a JS runtime on servers where `node` is not on PATH."""
    for candidate in (
        os.getenv("YTDLP_NODE_PATH"),
        os.getenv("NODE_BINARY"),
        shutil.which("node"),
    ):
        if candidate and Path(candidate).is_file():
            return candidate
    cursor_bins = Path("/root/.cursor-server/bin/linux-x64")
    if cursor_bins.is_dir():
        matches = sorted(cursor_bins.glob("*/node"), key=lambda p: p.stat().st_mtime, reverse=True)
        if matches:
            return str(matches[0])
    return None


def _video_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if not match:
        raise ValueError(f"Could not parse YouTube video id from: {url}")
    return match.group(1)


def _build_ydl_opts(
    output_dir: Path,
    cookies: Path | None,
    proxy: str | None,
) -> dict:
    opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-orig", "en-US"],
        "subtitlesformat": "srt",
        "ignoreerrors": True,
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "remote_components": ["ejs:github"],
    }
    node_bin = _resolve_node_binary()
    if node_bin:
        opts["js_runtimes"] = {"node": {"path": node_bin}}
        logger.info("Using Node.js for yt-dlp: %s", node_bin)
    else:
        logger.warning("No Node.js found; YouTube download may fail (set YTDLP_NODE_PATH)")
    if cookies and cookies.exists():
        opts["cookiefile"] = str(cookies)
        logger.info("Using cookies file: %s", cookies)
    if proxy:
        opts["proxy"] = proxy
        logger.info("Using proxy: %s", proxy)
    return opts


def download_youtube(url: str, temp_dir: Path, cookies: Path | None, proxy: str | None) -> tuple[Path, Path | None, str]:
    import yt_dlp

    temp_dir.mkdir(parents=True, exist_ok=True)
    ydl_opts = _build_ydl_opts(temp_dir, cookies, proxy)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title") or _video_id(url)

    video_id = _video_id(url)
    video_candidates = list(temp_dir.glob(f"{video_id}.*"))
    video_path = next((p for p in video_candidates if p.suffix.lower() in {".mp4", ".mkv", ".webm"}), None)
    if not video_path:
        video_path = next(temp_dir.glob("*.mp4"), None)
    if not video_path:
        raise FileNotFoundError(f"Download finished but no video file found in {temp_dir}")

    subtitle_path = None
    for pattern in (f"{video_id}*.srt", "*.srt"):
        matches = sorted(temp_dir.glob(pattern))
        if matches:
            subtitle_path = matches[0]
            break

    return video_path, subtitle_path, title


def _ensure_srt(video_path: Path, srt_path: Path | None, raw_dir: Path) -> Path:
    dest = raw_dir / "input.srt"
    if srt_path and srt_path.exists():
        shutil.copy2(srt_path, dest)
        return dest

    logger.warning("No subtitles from YouTube; generating with Whisper (this may take a while)")
    from backend.utils.speech_recognizer import generate_subtitle_for_video

    generated = generate_subtitle_for_video(video_path, output_path=dest, method="auto", model="base", language="en")
    if not generated or not Path(generated).exists():
        raise RuntimeError("No subtitles available and Whisper generation failed")
    return Path(generated)


def create_project(name: str, source_url: str, project_type: str) -> str:
    from backend.core.database import engine
    from backend.models.base import Base
    from backend.models.bilibili import BilibiliAccount, UploadRecord  # noqa: F401
    from backend.models.project import Project, ProjectStatus, ProjectType
    from backend.core.database import SessionLocal

    Base.metadata.create_all(bind=engine)
    project_id = str(uuid.uuid4())

    db = SessionLocal()
    try:
        project = Project(
            id=project_id,
            name=name[:255],
            description=f"YouTube import: {source_url}",
            status=ProjectStatus.PROCESSING,
            project_type=ProjectType(project_type),
            project_metadata={"source_url": source_url, "source": "youtube"},
            processing_config={"source_url": source_url},
        )
        db.add(project)
        db.commit()
        logger.info("Created project %s (%s)", project_id, name)
        return project_id
    finally:
        db.close()


def stage_files(project_id: str, video_path: Path, srt_path: Path | None) -> tuple[str, str]:
    from backend.core.path_utils import get_project_directory

    raw_dir = get_project_directory(project_id) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    dest_video = raw_dir / "input.mp4"
    shutil.copy2(video_path, dest_video)
    dest_srt = _ensure_srt(dest_video, srt_path, raw_dir)

    from backend.core.database import SessionLocal
    from backend.models.project import Project

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.video_path = str(dest_video)
            cfg = dict(project.processing_config or {})
            cfg["subtitle_path"] = str(dest_srt)
            project.processing_config = cfg
            db.commit()
    finally:
        db.close()

    return str(dest_video), str(dest_srt)


async def run_pipeline(project_id: str, video_path: str, srt_path: str) -> dict:
    from backend.services.simple_pipeline_adapter import create_simple_pipeline_adapter

    task_id = str(uuid.uuid4())
    adapter = create_simple_pipeline_adapter(project_id, task_id)
    return await adapter.process_project_sync(video_path, srt_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AutoClip on a YouTube URL or local files")
    parser.add_argument("url", nargs="?", help="YouTube URL")
    parser.add_argument("--video", type=Path, help="Skip download; use local video file")
    parser.add_argument("--srt", type=Path, help="Optional local SRT (with --video)")
    parser.add_argument("--name", help="Project name override")
    parser.add_argument("--project-type", default="speech", help="Project type (default: speech for podcasts)")
    parser.add_argument(
        "--cookies",
        type=Path,
        default=Path(os.getenv("YOUTUBE_COOKIES_FILE", "data/youtube_cookies.txt")),
        help="Netscape cookies.txt for YouTube (export from browser)",
    )
    parser.add_argument("--proxy", default=os.getenv("YOUTUBE_PROXY", ""), help="HTTP/SOCKS proxy for yt-dlp")
    parser.add_argument(
        "--use-cloak",
        action="store_true",
        help="Export cookies via CloakBrowser (twitter-automation/browser) before download",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    proxy = args.proxy.strip() or None
    cookies = args.cookies if args.cookies else None

    if args.video:
        if not args.video.exists():
            logger.error("Video file not found: %s", args.video)
            return 1
        title = args.name or args.video.stem
        source_url = args.url or ""
        video_path = args.video
        srt_path = args.srt if args.srt and args.srt.exists() else None
    else:
        if not args.url:
            logger.error("Provide a YouTube URL or --video")
            return 1
        source_url = args.url
        temp_dir = PROJECT_ROOT / "data" / "temp" / f"yt-{_video_id(source_url)}"

        if args.use_cloak:
            import subprocess

            cloak_cookies = PROJECT_ROOT / "data" / "youtube_cookies.txt"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "scripts" / "cloak_youtube_cookies.py"),
                    source_url,
                    "-o",
                    str(cloak_cookies),
                ],
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                cookies = cloak_cookies
                logger.info("CloakBrowser cookies exported to %s", cloak_cookies)
            else:
                logger.warning("CloakBrowser cookie export failed: %s", proc.stderr or proc.stdout)

        try:
            video_path, srt_path, title = download_youtube(source_url, temp_dir, cookies, proxy)
        except Exception as exc:
            logger.error("YouTube download failed: %s", exc)
            logger.error(
                "On cloud servers YouTube often blocks datacenter IPs. "
                "Fix: export browser cookies to data/youtube_cookies.txt "
                "(yt-dlp --cookies-from-browser chrome --cookies data/youtube_cookies.txt --skip-download URL) "
                "or download locally and rerun with --video/--srt."
            )
            return 1
        title = args.name or title

    project_id = create_project(title, source_url, args.project_type)
    video_path_str, srt_path_str = stage_files(project_id, video_path, srt_path)
    logger.info("Staged video=%s srt=%s", video_path_str, srt_path_str)

    result = asyncio.run(run_pipeline(project_id, video_path_str, srt_path_str))
    status = result.get("status")
    logger.info("Pipeline finished: status=%s project_id=%s", status, project_id)

    if status == "succeeded":
        print(f"\n✅ Done. Project ID: {project_id}")
        print(f"   Clips: data/projects/{project_id}/output/clips/")
        return 0

    print(f"\n❌ Pipeline failed for project {project_id}: {result.get('error', result)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
