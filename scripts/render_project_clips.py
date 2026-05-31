#!/usr/bin/env python3
"""Re-select clips (with top-N fallback), then titles, captions, and ffmpeg cuts."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("render_project_clips")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id", help="Project UUID")
    parser.add_argument("--skip-llm", action="store_true", help="Use outline as title; skip caption LLM")
    args = parser.parse_args()

    from backend.core.path_utils import get_project_directory
    from backend.core.shared_config import get_prompt_files
    from backend.pipeline.step3_scoring import ClipScorer, select_clips_for_pipeline
    from backend.pipeline.step4_title import run_step4_title
    from backend.pipeline.step_caption import run_step_caption
    from backend.pipeline.step6_video import run_step6_video
    from backend.services.simple_pipeline_adapter import _load_project_category

    project_dir = get_project_directory(args.project_id)
    metadata_dir = project_dir / "metadata"
    output_dir = project_dir / "output"
    raw_dir = project_dir / "raw"
    all_scored_path = metadata_dir / "step3_all_scored.json"
    high_score_path = metadata_dir / "step3_high_score_clips.json"
    titles_path = metadata_dir / "step4_titles.json"
    video_path = raw_dir / "input.mp4"
    srt_path = raw_dir / "input.srt"
    clips_dir = output_dir / "clips"

    if not all_scored_path.exists():
        logger.error("Missing %s", all_scored_path)
        return 1
    if not video_path.exists():
        logger.error("Missing %s", video_path)
        return 1

    scored = json.loads(all_scored_path.read_text(encoding="utf-8"))
    selected = select_clips_for_pipeline(scored)
    ClipScorer().save_scores(selected, high_score_path)
    logger.info("Selected %d clip(s) for rendering", len(selected))

    prompt_files = get_prompt_files(_load_project_category(args.project_id))

    if args.skip_llm:
        for clip in selected:
            outline = clip.get("outline")
            if isinstance(outline, dict):
                title = outline.get("title", f"Clip_{clip.get('id')}")
            else:
                title = str(outline) if outline else f"Clip_{clip.get('id')}"
            clip["generated_title"] = title[:120]
        titles_path.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        run_step4_title(high_score_path, metadata_dir=str(metadata_dir), prompt_files=prompt_files)
        selected = json.loads(titles_path.read_text(encoding="utf-8"))
        if srt_path.exists():
            run_step_caption(titles_path, srt_path, metadata_dir=metadata_dir, prompt_files=prompt_files)

    collections_path = metadata_dir / "step5_collections.json"
    collections_path.write_text("[]", encoding="utf-8")
    clips_dir.mkdir(parents=True, exist_ok=True)

    result = run_step6_video(
        titles_path,
        collections_path,
        video_path,
        output_dir=output_dir,
        clips_dir=str(clips_dir),
        metadata_dir=str(metadata_dir),
    )
    logger.info("Done: %s", result)
    for p in result.get("clip_paths", []):
        print(p)
    return 0 if result.get("clips_generated") else 1


if __name__ == "__main__":
    raise SystemExit(main())
