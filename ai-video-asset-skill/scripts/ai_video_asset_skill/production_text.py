"""Utilities for keeping workflow labels out of visual briefs."""

from __future__ import annotations

import re
from typing import Any, Iterable, List


_PRODUCTION_LABEL_PATTERNS = [
    r"(?i)AI\s*视频\s*素材",
    r"(?i)AIGC\s*视频\s*素材",
    r"商业\s*视频\s*素材",
    r"商用\s*视频\s*素材",
    r"视频\s*素材",
    r"商业\s*素材",
    r"宣传片\s*素材",
    r"生图\s*提示词",
    r"image2\s*提示词",
    r"提示词",
    r"生图",
]

_DIRECTION_SUFFIX_PATTERNS = [
    r"商业化\s*素材\s*方向",
    r"商业\s*素材\s*方向",
    r"素材\s*方向",
    r"商业化\s*方向",
]


def clean_visual_phrase(value: Any, fallback: str = "") -> str:
    """Remove workflow labels from text that describes the visible image."""

    text = str(value or "")
    for pattern in _PRODUCTION_LABEL_PATTERNS:
        text = re.sub(pattern, " ", text)
    for pattern in _DIRECTION_SUFFIX_PATTERNS:
        text = re.sub(pattern, " ", text)
    text = re.sub(r"\s+", " ", text.replace("\u3000", " ")).strip()
    text = re.sub(r"\s*([，,、/|：:；;])\s*", r"\1", text)
    text = text.strip(" _-，,、/|：:；;。.")
    return text or fallback


def clean_visual_terms(values: Iterable[Any], max_items: int | None = None) -> List[str]:
    """Clean market/search terms before they become subjects, actions, or scene fields."""

    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_visual_phrase(value)
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
        if max_items and len(output) >= max_items:
            break
    return output
