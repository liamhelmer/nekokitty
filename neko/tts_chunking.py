"""Punctuation-preserving sentence chunking for local speech synthesis.

This is a narrow backport of KittenTTS upstream commit
9f3e0d8b6600b56ebe1b4d7b6d8e1e020077d1f2. The released 0.8.1 wheel splits on
and removes ``.!?``, which changes questions and exclamations into comma-ended
chunks and flattens prosody.
"""

from __future__ import annotations

import re


NON_BOUNDARY_ABBREVIATIONS = {
    "dr",
    "prof",
    "mr",
    "mrs",
    "ms",
    "fig",
    "figs",
    "pp",
    "p",
    "ch",
    "sec",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
    "al",
}


def ensure_punctuation(text: str) -> str:
    """Ensure a chunk ends with prosodic punctuation."""

    text = text.strip()
    if text and text[-1] not in ".!?,;:":
        text += ","
    return text


def is_sentence_boundary(text: str, index: int) -> bool:
    """Return whether the punctuation at ``index`` ends a sentence."""

    char = text[index]
    if char not in ".!?":
        return False
    if char == ".":
        if (
            0 < index < len(text) - 1
            and text[index - 1].isdigit()
            and text[index + 1].isdigit()
        ):
            return False
        before = text[:index]
        token_match = re.search(r"([A-Za-z]+)$", before)
        token = token_match.group(1).lower() if token_match else ""
        if token in NON_BOUNDARY_ABBREVIATIONS:
            return False
        if (
            token in {"a", "p"}
            and index + 1 < len(text)
            and text[index + 1].lower() == "m"
        ):
            return False
        if token == "m" and re.search(r"\b[ap]\.m$", before, re.IGNORECASE):
            next_text = text[index + 1 :].strip()
            return not next_text or next_text[:1].isupper()
    next_text = text[index + 1 :]
    return not next_text or next_text[:1].isspace()


def chunk_text(text: str, max_len: int = 400) -> list[str]:
    """Split text while preserving sentence punctuation and abbreviations."""

    if max_len <= 0:
        raise ValueError("max_len must be positive")
    sentences: list[str] = []
    start = 0
    for index, _ in enumerate(text):
        if is_sentence_boundary(text, index):
            sentences.append(text[start : index + 1])
            start = index + 1
    if start < len(text):
        sentences.append(text[start:])

    chunks: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= max_len:
            chunks.append(ensure_punctuation(sentence))
            continue
        words = sentence.split()
        current = ""
        for word in words:
            if len(current) + len(word) + 1 <= max_len:
                current += f" {word}" if current else word
            else:
                if current:
                    chunks.append(ensure_punctuation(current))
                current = word
        if current:
            chunks.append(ensure_punctuation(current))
    return chunks
