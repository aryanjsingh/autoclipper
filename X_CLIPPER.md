# AutoClip → X (Twitter) Podcast Clipper

This repo is tuned to turn long 2-person podcasts/interviews into **standalone X clips**
with engagement-optimized captions. Source language can be anything; **output is English**.

## What it produces
- **Clips of 30 seconds to 3 minutes** (hard limits, enforced in code).
- **As many clips as the episode merits** — no fixed count. Clips are kept by an
  engagement score, not a quota.
- **No compilations/collections** — standalone clips only.
- A **tweet caption per clip** in the proven @yonann style: a third-person hook line
  (`<Speaker> says <bold claim>`) followed by 2–4 verbatim quotes from the clip.

## What it deliberately skips
- Intros, greetings, guest bios, "who are you", sponsor reads, sign-offs/outros.
- Clips that would cut a question off — every clip contains the **full question and its
  full answer**.

## Model
Claude **Opus 4.8** via the local kiro-gateway. Configured in `data/settings.json`
(`model_name: "claude-opus-4.8"`). The gateway must be running (see `../kiro-gateway`).

## Run it standalone (no web stack / DB / Celery)
```bash
cd /root/projects/autoclip
PYTHONPATH=. .venv/bin/python scripts/clip_podcast.py \
  --video path/to/episode.mp4 \
  --srt   path/to/episode.srt \
  --out   data/output/my_episode \
  --speakers "Guest Name, Host Name"      # optional, improves caption hooks
```
Useful flags:
- `--minutes N` — only process the first N minutes (fast test runs).
- `--no-video` — skip ffmpeg cutting; just produce titles + captions.
- `--category` — prompt category (default `speech`).

Outputs land in `<out>/`:
- `clips/*.mp4` — the cut clips (filename = `<id>_<title>.mp4`)
- `metadata/tweets.txt` — captions ready to copy/paste
- `metadata/tweets.json` — captions + timing + score (machine-readable)
- `metadata/clips_metadata.json` — full per-clip data (includes `tweet_text`)

## Run it through the app
The normal upload/YouTube flow uses the same pipeline
(`backend/services/simple_pipeline_adapter.py`). A YouTube/upload project will now yield
30s–3min clips + captions and no collections.

## Tuning knobs (`backend/core/shared_config.py`)
- `MIN_CLIP_SECONDS` / `MAX_CLIP_SECONDS` — the 30s / 180s clip window.
- `TARGET_CLIP_SECONDS` — the sweet-spot length the model aims for (~75s).
- `MIN_SCORE_THRESHOLD` — engagement bar (0–1). Raise it for fewer/stronger clips,
  lower it for more volume. Default `0.6`.

## Prompts
English, podcast-tuned, JSON-coherent with the parsers. Live under
`backend/prompt/languages/en/` and `backend/prompt/languages/en/speech/`:
- `outline.txt` — finds clip-worthy moments, excludes intros/sponsors.
- `timeline.txt` — precise 30s–3min boundaries, never cuts a question.
- `recommendation.txt` — engagement scoring (0–1).
- `title.txt` — internal clip titles.
- `caption.txt` — the @yonann-style tweet caption.

## Posting
Caption generation is **manual-post only** right now (clips + `tweets.txt` are produced;
nothing is posted to X automatically). The logged-in `twitter` CLI lives at
`../twitter-automation/.venv/bin/twitter` for when the posting step is built.
