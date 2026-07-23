"""Small local, manifest-gated story selector for Neko."""

from __future__ import annotations

import json
import hashlib
import random
import re
from dataclasses import dataclass
from pathlib import Path


STORY_SOUND_TARGET_WORDS = 75
STORY_SOUND_MAXIMUM = 10
WORD_RE = re.compile(r"\b[\w’'-]+\b")
FORBIDDEN_STORY_STOP_RE = re.compile(
    r"\bnekk?o\b\W+(?:stop|stopped)\b",
    re.IGNORECASE,
)
FORBIDDEN_STORY_DOUBLE_WAKE_RE = re.compile(
    r"\bnekk?o\b\W+\bnekk?o\b",
    re.IGNORECASE,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "content/stories/library.json"
DEFAULT_RECORDING_MANIFEST = (
    REPO_ROOT / "content/stories/recordings/mini-kiki-v1/manifest.json"
)
RECORDING_CUES = {None, "meow_general", "meow_thank_you"}
QUERY_STOPWORDS = {
    "a", "an", "and", "another", "about", "me", "please", "story", "tell", "the",
}


def contains_forbidden_stop_phrase(text: str) -> bool:
    """Reject narration that could acoustically trigger the global stop path."""

    return (
        FORBIDDEN_STORY_STOP_RE.search(text) is not None
        or FORBIDDEN_STORY_DOUBLE_WAKE_RE.search(text) is not None
    )


@dataclass(frozen=True, slots=True)
class Story:
    story_id: str
    title: str
    text: str
    tags: tuple[str, ...]
    summary: str
    essentials: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecordedStorySection:
    path: Path
    sha256: str
    duration_seconds: float
    contains_neko: bool
    cue_after: str | None


@dataclass(frozen=True, slots=True)
class RecordedStory:
    story_id: str
    sections: tuple[RecordedStorySection, ...]
    ending_purr: bool


class StoryLibrary:
    """Read only approved local originals; never fetch or expose candidates."""

    def __init__(
        self,
        manifest_path: Path = DEFAULT_MANIFEST,
        recording_manifest_path: Path | None = DEFAULT_RECORDING_MANIFEST,
    ) -> None:
        self.root = REPO_ROOT.resolve()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("entries"), list):
            raise ValueError("unsupported story manifest")
        self.entries = tuple(data["entries"])
        self.recording_manifest_path = recording_manifest_path
        self._recording_manifest_mtime_ns: int | None = None
        self.recordings: dict[str, dict] = {}
        self._reload_recordings_if_changed()

    def _reload_recordings_if_changed(self) -> None:
        path = self.recording_manifest_path
        if path is None or not path.is_file():
            return
        mtime_ns = path.stat().st_mtime_ns
        if mtime_ns == self._recording_manifest_mtime_ns:
            return
        recording_data = json.loads(path.read_text(encoding="utf-8"))
        if recording_data.get("schema_version") != 1 or not isinstance(
            recording_data.get("stories"), list
        ):
            raise ValueError("unsupported story recording manifest")
        recordings = {item["story_id"]: item for item in recording_data["stories"]}
        if len(recordings) != len(recording_data["stories"]):
            raise ValueError("duplicate story recording ID")
        self.recordings = recordings
        self._recording_manifest_mtime_ns = mtime_ns

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
            if contains_forbidden_stop_phrase(text):
                raise ValueError(
                    f"approved story contains a reserved stop phrase: {entry['id']}"
                )
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

    def recording_for(self, story: Story) -> RecordedStory | None:
        """Return a hash-verified pre-rendered plan, or the live-TTS fallback."""

        self._reload_recordings_if_changed()
        entry = self.recordings.get(story.story_id)
        if entry is None:
            return None
        source_path = (self.root / entry["source_path"]).resolve()
        try:
            source_path.relative_to(self.root)
        except ValueError as error:
            raise ValueError("story recording source escapes repository") from error
        if not source_path.is_file() or _sha256(source_path) != entry.get("source_sha256"):
            raise ValueError(f"story recording source is stale: {story.story_id}")
        spoken_hash = hashlib.sha256(
            self.spoken_text(story).encode("utf-8")
        ).hexdigest()
        if spoken_hash != entry.get("spoken_text_sha256"):
            raise ValueError(f"story recording text is stale: {story.story_id}")

        section_items = entry.get("sections")
        if not isinstance(section_items, list) or not section_items:
            raise ValueError(f"story recording has no sections: {story.story_id}")
        sections: list[RecordedStorySection] = []
        for expected_index, item in enumerate(section_items):
            if item.get("index") != expected_index:
                raise ValueError(f"story recording section order is invalid: {story.story_id}")
            path = (self.root / item["path"]).resolve()
            try:
                path.relative_to(self.root)
            except ValueError as error:
                raise ValueError("story recording audio escapes repository") from error
            expected_hash = item.get("sha256")
            if (
                path.suffix.casefold() != ".flac"
                or not isinstance(expected_hash, str)
                or not path.is_file()
                or _sha256(path) != expected_hash
            ):
                raise ValueError(
                    f"story recording audio failed integrity: {story.story_id}/{expected_index}"
                )
            duration = item.get("duration_seconds")
            cue = item.get("cue_after")
            if not isinstance(duration, (int, float)) or not 0 < duration <= 60:
                raise ValueError(f"invalid story section duration: {story.story_id}")
            if cue not in RECORDING_CUES:
                raise ValueError(f"invalid story recording cue: {cue}")
            sections.append(
                RecordedStorySection(
                    path=path,
                    sha256=expected_hash,
                    duration_seconds=float(duration),
                    contains_neko=item.get("contains_neko") is True,
                    cue_after=cue,
                )
            )
        ending_purr = entry.get("ending_purr")
        if not isinstance(ending_purr, bool):
            raise ValueError(f"story ending-purr decision is missing: {story.story_id}")
        return RecordedStory(story.story_id, tuple(sections), ending_purr)

    @staticmethod
    def context_note(story: Story, *, interrupted: bool = False) -> str:
        state = "I started telling" if interrupted else "I told"
        essentials = "; ".join(story.essentials)
        return f"{state} {story.title}. Summary: {story.summary} Essentials: {essentials}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
