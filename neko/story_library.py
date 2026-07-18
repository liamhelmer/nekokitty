"""Small local, manifest-gated story selector for Neko."""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path


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
    def context_note(story: Story, *, interrupted: bool = False) -> str:
        state = "I started telling" if interrupted else "I told"
        essentials = "; ".join(story.essentials)
        return f"{state} {story.title}. Summary: {story.summary} Essentials: {essentials}"
