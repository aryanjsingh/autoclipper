#!/usr/bin/env python3
"""
Standalone podcast -> X clips runner (no web stack, no DB, no Celery).

Runs the full clipping pipeline on a single video + SRT and writes:
  <out>/clips/*.mp4              the cut clips (30s-3min each)
  <out>/metadata/clips_metadata.json
  <out>/metadata/tweets.json     machine-readable captions
  <out>/metadata/tweets.txt      human-readable captions (ready to copy/paste)

Usage:
  PYTHONPATH=. .venv/bin/python scripts/clip_podcast.py \
      --video data/temp/yt-Rni7Fz7208c/Rni7Fz7208c.mp4 \
      --srt   data/temp/yt-Rni7Fz7208c/Rni7Fz7208c.en.srt \
      --out   data/output/test_run \
      --speakers "Elon Musk, Nikhil Kamath"

Flags:
  --minutes N    Only process the first N minutes of the SRT (fast test runs).
  --no-video     Skip ffmpeg cutting; just produce titles + captions metadata.
  --category C   Prompt category (default: speech).
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Make the repo importable when run as a script.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Force English output regardless of shell env.
os.environ.setdefault("AUTOCLIP_OUTPUT_LANGUAGE", "en")

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("clip_podcast")

from backend.core.shared_config import get_prompt_files, MIN_CLIP_SECONDS, MAX_CLIP_SECONDS
from backend.utils.text_processor import TextProcessor
from backend.pipeline.step1_outline import run_step1_outline
from backend.pipeline.step2_timeline import run_step2_timeline
from backend.pipeline.step3_scoring import run_step3_scoring
from backend.pipeline.step4_title import run_step4_title
from backend.pipeline.step_caption import run_step_caption
from backend.pipeline.step6_video import run_step6_video


def truncate_srt(srt_path: Path, minutes: float, dest: Path) -> Path:
    """Write a copy of the SRT containing only entries that start before `minutes`."""
    import pysrt
    subs = pysrt.open(str(srt_path), encoding="utf-8")
    cutoff_ms = minutes * 60 * 1000
    kept = [s for s in subs if (s.start.ordinal <= cutoff_ms)]
    out = pysrt.SubRipFile(items=kept)
    out.save(str(dest), encoding="utf-8")
    log.info("Truncated SRT to first %.0f min: %d/%d cues -> %s", minutes, len(kept), len(subs), dest)
    return dest


def main():
    ap = argparse.ArgumentParser(description="Clip a podcast into X-ready clips + captions.")
    ap.add_argument("--video", required=True, help="Path to the source video (mp4).")
    ap.add_argument("--srt", required=True, help="Path to the SRT transcript.")
    ap.add_argument("--out", required=True, help="Output directory.")
    ap.add_argument("--speakers", default="", help="Comma-separated speaker names (helps captions).")
    ap.add_argument("--category", default="speech", help="Prompt category (default: speech).")
    ap.add_argument("--minutes", type=float, default=0, help="Only process first N minutes (0 = all).")
    ap.add_argument("--no-video", action="store_true", help="Skip ffmpeg cutting.")
    args = ap.parse_args()

    video = Path(args.video)
    srt = Path(args.srt)
    out = Path(args.out)
    metadata_dir = out / "metadata"
    clips_dir = out / "clips"
    collections_dir = out / "collections"
    for d in (metadata_dir, clips_dir, collections_dir):
        d.mkdir(parents=True, exist_ok=True)

    if not srt.exists():
        sys.exit(f"SRT not found: {srt}")
    if not args.no_video and not video.exists():
        sys.exit(f"Video not found: {video} (use --no-video to skip cutting)")

    if args.minutes and args.minutes > 0:
        srt = truncate_srt(srt, args.minutes, metadata_dir / "input_truncated.srt")

    prompt_files = get_prompt_files(args.category)
    log.info("Prompts: %s", {k: str(v) for k, v in prompt_files.items()})

    # Step 1: find clip-worthy moments
    outlines = run_step1_outline(srt, metadata_dir=metadata_dir, prompt_files=prompt_files)
    log.info("Step 1: %d candidate moments", len(outlines))
    if not outlines:
        sys.exit("No moments found. Check the SRT / prompts.")

    # Step 2: precise 30s-3min timestamps
    timeline = run_step2_timeline(metadata_dir / "step1_outline.json", metadata_dir=metadata_dir, prompt_files=prompt_files)
    log.info("Step 2: %d timed clips (within %d-%ds)", len(timeline), MIN_CLIP_SECONDS, MAX_CLIP_SECONDS)

    # Step 3: engagement scoring + threshold filter (no cap on count)
    scored = run_step3_scoring(metadata_dir / "step2_timeline.json", metadata_dir=metadata_dir, prompt_files=prompt_files)
    log.info("Step 3: %d clips passed the score threshold", len(scored))
    if not scored:
        sys.exit("No clips passed the engagement threshold.")

    # Step 4: titles
    titled = run_step4_title(metadata_dir / "step3_high_score_clips.json", metadata_dir=str(metadata_dir), prompt_files=prompt_files)
    log.info("Step 4: %d titles", len(titled))

    # Caption step: yonann-style tweet text
    titled = run_step_caption(metadata_dir / "step4_titles.json", srt, metadata_dir=metadata_dir, prompt_files=prompt_files, speakers=args.speakers)
    log.info("Captions written to %s", metadata_dir / "tweets.txt")

    # Empty collections (compilations disabled)
    with open(metadata_dir / "step5_collections.json", "w", encoding="utf-8") as f:
        json.dump([], f)

    # Step 6: cut the clips (unless skipped)
    if args.no_video:
        with open(metadata_dir / "clips_metadata.json", "w", encoding="utf-8") as f:
            json.dump(titled, f, ensure_ascii=False, indent=2)
        log.info("Skipped video cutting (--no-video).")
    else:
        result = run_step6_video(
            metadata_dir / "step4_titles.json",
            metadata_dir / "step5_collections.json",
            video,
            output_dir=out,
            clips_dir=str(clips_dir),
            collections_dir=str(collections_dir),
            metadata_dir=str(metadata_dir),
        )
        log.info("Step 6: generated %d clip videos", result.get("clips_generated", 0))

    # Summary
    tp = TextProcessor()
    print("\n" + "=" * 70)
    print(f"DONE — {len(titled)} clips")
    print("=" * 70)
    for c in titled:
        dur = tp.time_to_seconds(c["end_time"]) - tp.time_to_seconds(c["start_time"])
        print(f"\n[{c.get('id')}] {c.get('generated_title')}")
        print(f"    {c['start_time']} -> {c['end_time']}  ({dur:.0f}s)  score={c.get('final_score')}")
        if c.get("tweet_text"):
            preview = c["tweet_text"].replace("\n", " / ")
            print(f"    tweet: {preview[:120]}")
    print(f"\nCaptions: {metadata_dir / 'tweets.txt'}")
    if not args.no_video:
        print(f"Clips:    {clips_dir}")


if __name__ == "__main__":
    main()
