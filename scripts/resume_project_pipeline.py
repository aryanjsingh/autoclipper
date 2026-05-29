#!/usr/bin/env python3
"""Resume AutoClip pipeline from step 2 for an existing project (skips re-download / step 1)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("resume_project_pipeline")


async def resume_from_step2(project_id: str) -> int:
    from backend.core.path_utils import get_project_directory
    from backend.pipeline.step2_timeline import run_step2_timeline
    from backend.pipeline.step3_scoring import run_step3_scoring
    from backend.pipeline.step4_title import run_step4_title
    from backend.pipeline.step_caption import run_step_caption
    from backend.pipeline.step6_video import run_step6_video
    from backend.core.shared_config import get_prompt_files
    from backend.services.simple_pipeline_adapter import _load_project_category
    import json

    project_dir = get_project_directory(project_id)
    metadata_dir = project_dir / "metadata"
    output_dir = project_dir / "output"
    raw_dir = project_dir / "raw"
    outline_file = metadata_dir / "step1_outline.json"
    video_path = raw_dir / "input.mp4"
    srt_path = raw_dir / "input.srt"

    for path, label in [
        (outline_file, "step1 outline"),
        (video_path, "input video"),
        (srt_path, "input SRT"),
    ]:
        if not path.exists():
            logger.error("Missing %s: %s", label, path)
            return 1

    clips_output_dir = output_dir / "clips"
    clips_output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    video_category = _load_project_category(project_id)
    prompt_files = get_prompt_files(video_category)

    logger.info("Resuming project %s from step 2", project_id)

    run_step2_timeline(outline_file, metadata_dir=metadata_dir, prompt_files=prompt_files)
    run_step3_scoring(
        metadata_dir / "step2_timeline.json",
        metadata_dir=metadata_dir,
        prompt_files=prompt_files,
    )
    run_step4_title(
        metadata_dir / "step3_high_score_clips.json",
        metadata_dir=str(metadata_dir),
        prompt_files=prompt_files,
    )
    titled_clips = run_step_caption(
        metadata_dir / "step4_titles.json",
        srt_path,
        metadata_dir=metadata_dir,
        prompt_files=prompt_files,
    )
    with open(metadata_dir / "step5_collections.json", "w", encoding="utf-8") as f:
        json.dump([], f)

    run_step6_video(
        metadata_dir / "step4_titles.json",
        metadata_dir / "step5_collections.json",
        video_path,
        output_dir=output_dir,
        clips_dir=str(clips_output_dir),
        metadata_dir=str(metadata_dir),
    )

    logger.info("Resume complete. Clips: %s", clips_output_dir)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Resume pipeline from step 2")
    parser.add_argument("project_id", help="Project UUID")
    args = parser.parse_args()
    return asyncio.run(resume_from_step2(args.project_id))


if __name__ == "__main__":
    raise SystemExit(main())
