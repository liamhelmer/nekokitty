"""Small local, manifest-gated story selector for Neko."""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path


STORY_SOUND_TARGET_WORDS = 75
STORY_SOUND_MAXIMUM = 10
WORD_RE = re.compile(r"\b[\w’'-]+\b")


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "content/stories/library.json"
QUERY_STOPWORDS = {
    "a", "an", "and", "another", "about", "me", "please", "story", "tell", "the",
}


@dataclass(frozen=True, slots=True)
class Story:
    story_id: str
    title: str
    text: str
    tags: tuple[str, ...]
    summary: str
    essentials: tuple[str, ...]


class StoryLibrary:
    """Read only approved local originals; never fetch or expose candidates."""

    def __init__(self, manifest_path: Path = DEFAULT_MANIFEST) -> None:
        self.root = REPO_ROOT.resolve()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("entries"), list):
            raise ValueError("unsupported story manifest")
        self.entries = tuple(data["entries"])

    def _scored(self, query: str) -> list[tuple[int, Story]]:
        terms = set(re.findall(r"[\w]+", query.casefold())) - QUERY_STOPWORDS
        matches: list[tuple[int, Story]] = []
        for entry in self.entries:
            if entry.get("status") != "approved_for_owner_test":
                continue
            path = (self.root / entry["path"]).resolve()
            try:
                path.relative_to(self.root)
            except ValueError as error:
                raise ValueError("story path escapes repository") from error
            text = path.read_text(encoding="utf-8")
            haystack = set(
                re.findall(
                    r"[\w]+",
                    f"{entry['title']} {' '.join(entry.get('tags', []))} {text}".casefold(),
                )
            )
            score = len(terms & haystack)
            summary = entry.get("summary")
            essentials = entry.get("essentials")
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError(f"approved story lacks summary: {entry['id']}")
            if not isinstance(essentials, list) or not all(
                isinstance(item, str) and item.strip() for item in essentials
            ):
                raise ValueError(f"approved story lacks essentials: {entry['id']}")
            matches.append(
                (
                    score,
                    Story(
                        entry["id"],
                        entry["title"],
                        text,
                        tuple(entry["tags"]),
                        summary.strip(),
                        tuple(essentials),
                    ),
                )
            )
        matches.sort(key=lambda item: (-item[0], item[1].title))
        return matches

    def search(self, query: str, *, limit: int = 3) -> tuple[Story, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        matches = self._scored(query)
        return tuple(item[1] for item in matches[:limit])

    def choose(
        self,
        query: str,
        *,
        exclude_id: str | None = None,
        rng: random.Random | None = None,
    ) -> Story:
        scored = self._scored(query)
        if not scored:
            raise LookupError("no approved local stories")
        best_score = scored[0][0]
        candidates = [story for score, story in scored if score == best_score]
        alternatives = [story for story in candidates if story.story_id != exclude_id]
        if not alternatives:
            alternatives = [
                story for _score, story in scored if story.story_id != exclude_id
            ]
        pool = alternatives or candidates
        if not pool:
            raise LookupError("no approved local stories")
        # Keep retrieval relevant, but vary among equally scored/tagged local
        # material. The manifest remains the authority boundary.
        chooser = rng or random.SystemRandom()
        return chooser.choice(pool)

    @staticmethod
    def spoken_text(story: Story) -> str:
        lines = story.text.splitlines()
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
        text = "\n".join(lines).strip()
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        return re.sub(r"\*([^*]+)\*", r"\1", text)

    @staticmethod
    def sound_budget(text: str) -> int:
        """Return total story sounds, including the post-story tail purr."""

        words = len(WORD_RE.findall(text))
        if words == 0:
            return 0
        rounded_target = (words + STORY_SOUND_TARGET_WORDS // 2) // STORY_SOUND_TARGET_WORDS
        return max(1, min(STORY_SOUND_MAXIMUM, rounded_target))

    @staticmethod
    def with_audio_cues(text: str, *, rng: random.Random | None = None) -> str:
        """Add evenly spaced, lightly varied meows; reserve the last sound for a purr."""

        total_budget = StoryLibrary.sound_budget(text)
        inline_budget = max(0, total_budget - 1)
        if inline_budget == 0:
            return text

        boundaries: list[tuple[int, int]] = []
        for index, char in enumerate(text):
            if char not in ".!?":
                continue
            end = index + 1
            while end < len(text) and text[end] in "\"'’”":
                end += 1
            if end < len(text) and not text[end].isspace():
                continue
            words_before = len(WORD_RE.findall(text[:end]))
            boundaries.append((end, words_before))

        total_words = len(WORD_RE.findall(text))
        candidates = [
            item for item in boundaries if 25 <= item[1] <= total_words - 25
        ]
        if not candidates:
            return text

        selected: list[int] = []
        available = candidates.copy()
        for number in range(1, inline_budget + 1):
            if not available:
                break
            target = total_words * number / (inline_budget + 1)
            best = min(available, key=lambda item: abs(item[1] - target))
            selected.append(best[0])
            available.remove(best)

        chooser = rng or random.SystemRandom()
        markers = ["[meow]"] * len(selected)
        friendly_count = max(1, len(markers) // 3)
        for index in chooser.sample(range(len(markers)), k=friendly_count):
            markers[index] = "[meow:thanks]"
        rendered = text
        placements = zip(sorted(selected), markers, strict=True)
        for end, marker in reversed(list(placements)):
            rendered = f"{rendered[:end]} {marker}{rendered[end:]}"
        return rendered

    @staticmethod
    def context_note(story: Story, *, interrupted: bool = False) -> str:
        state = "I started telling" if interrupted else "I told"
        essentials = "; ".join(story.essentials)
        return f"{state} {story.title}. Summary: {story.summary} Essentials: {essentials}"
