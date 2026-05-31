"""
Caption step: generate an X (Twitter) post caption for each clip.

Style is modeled on top podcast-clip accounts (e.g. @yonann): a third-person hook
line naming the speaker and the boldest claim, followed by a few verbatim quotes
pulled straight from the clip transcript.

This runs after title generation and before video cutting so the caption (`tweet_text`)
travels with the clip into clips_metadata.json. It also writes a human-readable
`tweets.txt` and a machine-readable `tweets.json` into the metadata directory.
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from ..utils.llm_client import LLMClient
from ..utils.text_processor import TextProcessor
from ..core.shared_config import PROMPT_FILES, METADATA_DIR

logger = logging.getLogger(__name__)

# Lines that are pure stage direction / non-speech and should never appear in quotes.
_NON_SPEECH = re.compile(r'^\s*[\[\(](music|applause|laughter|cheering|sound|noise|silence)[\]\)]\s*$', re.IGNORECASE)


class CaptionGenerator:
    """Generates per-clip tweet captions from the clip's verbatim transcript."""

    def __init__(self, metadata_dir: Optional[Path] = None, prompt_files: Dict = None):
        self.llm_client = LLMClient()
        self.text_processor = TextProcessor()
        self.metadata_dir = Path(metadata_dir) if metadata_dir else METADATA_DIR

        prompt_files_to_use = prompt_files if prompt_files is not None else PROMPT_FILES
        with open(prompt_files_to_use['caption'], 'r', encoding='utf-8') as f:
            self.caption_prompt = f.read()

    def _extract_transcript(self, srt_data: List[Dict], start_time: str, end_time: str) -> str:
        """Join the verbatim subtitle text inside [start_time, end_time], de-noised."""
        to_sec = self.text_processor.time_to_seconds
        start_s = to_sec(start_time)
        end_s = to_sec(end_time)

        pieces: List[str] = []
        for sub in srt_data:
            sub_start = to_sec(sub['start_time'])
            sub_end = to_sec(sub['end_time'])
            # Keep subtitles whose midpoint falls in the window (handles overlap).
            mid = (sub_start + sub_end) / 2
            if mid < start_s or mid > end_s:
                continue
            text = (sub.get('text') or '').strip()
            if not text or _NON_SPEECH.match(text):
                continue
            text = re.sub(r'\s+', ' ', text)
            # Skip rolling-caption repeats: identical to, or contained in, recent text.
            if pieces:
                tail = ' '.join(pieces[-3:])
                if text in tail or pieces[-1] == text:
                    continue
            pieces.append(text)

        return ' '.join(pieces).strip()

    def generate_captions(self, clips: List[Dict], srt_data: List[Dict], speakers: str = "") -> List[Dict]:
        """Add `tweet_text` (and `tweet_speaker`) to each clip in place."""
        if not clips:
            return clips

        logger.info(f"Generating tweet captions for {len(clips)} clips...")

        for clip in clips:
            transcript = self._extract_transcript(srt_data, clip['start_time'], clip['end_time'])
            if not transcript:
                logger.warning(f"  > No transcript for clip {clip.get('id')}, skipping caption")
                clip['tweet_text'] = ""
                clip['tweet_speaker'] = ""
                continue

            input_data = {
                "title": clip.get('generated_title') or clip.get('outline') or "",
                "transcript": transcript,
                "speakers": speakers or "",
            }

            try:
                raw = self.llm_client.call_with_retry(
                    self.caption_prompt, input_data, pipeline_step="caption"
                )
                parsed = self.llm_client.parse_json_response(raw)
                if isinstance(parsed, list) and parsed:
                    parsed = parsed[0]
                if isinstance(parsed, dict):
                    clip['tweet_text'] = (parsed.get('tweet_text') or "").strip()
                    clip['tweet_speaker'] = (parsed.get('speaker') or "").strip()
                else:
                    clip['tweet_text'] = str(parsed).strip()
                    clip['tweet_speaker'] = ""
                logger.info(f"  > Caption for clip {clip.get('id')}: {clip['tweet_text'][:60]!r}...")
            except Exception as e:
                logger.error(f"  > Caption generation failed for clip {clip.get('id')}: {e}")
                clip['tweet_text'] = ""
                clip['tweet_speaker'] = ""

        return clips

    def save_tweets(self, clips: List[Dict]) -> None:
        """Write tweets.json and a human-readable tweets.txt to the metadata dir."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        tweets = [
            {
                "id": clip.get('id'),
                "generated_title": clip.get('generated_title'),
                "speaker": clip.get('tweet_speaker', ""),
                "tweet_text": clip.get('tweet_text', ""),
                "start_time": clip.get('start_time'),
                "end_time": clip.get('end_time'),
                "final_score": clip.get('final_score'),
            }
            for clip in clips
            if clip.get('tweet_text')
        ]

        with open(self.metadata_dir / "tweets.json", 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=2)

        lines = []
        for t in tweets:
            lines.append(f"### Clip {t['id']} — {t.get('generated_title') or ''}  (score {t.get('final_score')})")
            lines.append(f"[{t['start_time']} -> {t['end_time']}]")
            lines.append("")
            lines.append(t['tweet_text'])
            lines.append("")
            lines.append("-" * 60)
            lines.append("")
        with open(self.metadata_dir / "tweets.txt", 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        logger.info(f"Saved {len(tweets)} captions to {self.metadata_dir / 'tweets.json'}")


def run_step_caption(
    clips_with_titles_path: Path,
    srt_path: Path,
    metadata_dir: Optional[Path] = None,
    prompt_files: Dict = None,
    speakers: str = "",
) -> List[Dict]:
    """
    Generate captions for clips and persist them.

    Reads the clips-with-titles JSON (from step4) and the SRT, writes captions back
    into the same clips file, and emits tweets.json / tweets.txt.
    """
    if metadata_dir is None:
        metadata_dir = METADATA_DIR
    metadata_dir = Path(metadata_dir)

    with open(clips_with_titles_path, 'r', encoding='utf-8') as f:
        clips = json.load(f)

    srt_data = TextProcessor.parse_srt(Path(srt_path)) if srt_path else []
    if not srt_data:
        logger.warning("No SRT data available for captions; skipping caption generation")
        return clips

    generator = CaptionGenerator(metadata_dir=metadata_dir, prompt_files=prompt_files)
    clips = generator.generate_captions(clips, srt_data, speakers=speakers)
    generator.save_tweets(clips)

    # Persist captions back into the clips-with-titles file so step6 carries them
    # into clips_metadata.json.
    with open(clips_with_titles_path, 'w', encoding='utf-8') as f:
        json.dump(clips, f, ensure_ascii=False, indent=2)

    return clips
