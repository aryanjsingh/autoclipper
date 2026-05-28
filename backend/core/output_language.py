"""Output language helpers for prompts, UI copy, and speech recognition."""

from __future__ import annotations

import os

OUTPUT_LANGUAGE = os.getenv(
    "AUTOCLIP_OUTPUT_LANGUAGE",
    os.getenv("OUTPUT_LANGUAGE", "en"),
).strip().lower()


def is_english() -> bool:
    return OUTPUT_LANGUAGE.startswith("en")


def speech_recognition_language() -> str:
    if is_english():
        return os.getenv("SPEECH_RECOGNITION_LANGUAGE", "en")
    return os.getenv("SPEECH_RECOGNITION_LANGUAGE", "auto")
