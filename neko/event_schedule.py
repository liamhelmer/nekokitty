"""Offline-first What If event cache and time-aware local search."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Iterable
from urllib import request
from zoneinfo import ZoneInfo


PACIFIC = ZoneInfo("America/Vancouver")
DEFAULT_STATE_DIR = Path("/var/lib/neko/what-if")
DEFAULT_DB = DEFAULT_STATE_DIR / "what-if.sqlite3"
BASE_URL = "https://data.dust.events/what-if"
SOURCES = ("schedule", "music", "art", "camps")
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
DAY_RE = re.compile(
    r"\b(monday|mon|tuesday|tue|tues|wednesday|wed|thursday|thu|thur|thurs|"
    r"friday|fri|saturday|sat|sat\s+day|sunday|sun)\b",
    re.IGNORECASE,
)
TIME_RE = re.compile(
    r"\b(?:(?:at|around)\s*)?(1[0-2]|0?[1-9])(?::([0-5][0-9]))?\s*(a\.?m\.?|p\.?m\.?|a|p)\b",
    re.IGNORECASE,
)
BARE_TIME_RE = re.compile(
    r"\b(?:at|around)\s*(1[0-2]|0?[1-9])(?::([0-5][0-9]))?\b",
    re.IGNORECASE,
)
WORD_TIME_RE = re.compile(
    r"\b(?:(?:at|around)\s*)?"
    r"(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
    r"(?:\s+(oh\s+)?(zero|five|ten|fifteen|twenty|twenty five|thirty|thirty five|forty|forty five|fifty|fifty five))?"
    r"\s*(a\.?m\.?|p\.?m\.?|a|p)\b",
    re.IGNORECASE,
)
SCHEDULE_WORDS = {
    "schedule", "calendar", "event", "events", "music", "dj", "djs",
    "playing", "set", "sets", "art", "camp", "camps",
}
SCHEDULE_PHRASES = (
    "what s happening", "whats happening", "what is happening",
    "what s going on", "whats going on", "what is going on",
    "what s on", "whats on",
)
QUERY_STOPWORDS = {
    "a", "about", "an", "and", "any", "are", "around", "at", "calendar", "do",
    "event", "events", "for", "going", "happening", "have", "i", "in", "is",
    "all", "could", "d", "happen", "happens", "how", "id", "it", "just", "let", "lets", "like", "looking", "maybe", "me", "neko", "nekko", "now", "of", "on", "please", "schedule", "show", "something", "uh",
    "day", "nico", "niko", "nikko", "nekko", "or", "s", "sat", "tell", "the", "there", "thing", "this", "time", "today", "us", "want", "was", "what", "whats", "with", "would",
    "who", "you",
}
EXPANSIONS = {
    "music": ("music", "musician", "dj", "dance", "live", "set", "sound"),
    "dj": ("dj", "music", "dance", "set", "sound"),
    "playing": ("playing", "performer", "musician", "dj", "music", "set"),
    "art": ("art", "artist", "installation", "mutant", "vehicle"),
    "camp": ("camp", "village", "location"),
    "food": ("food", "drink", "meal", "snack", "cafe"),
    "kids": ("kids", "children", "family", "friendly"),
    "kid": ("kids", "children", "family", "friendly"),
}


@dataclass(frozen=True, slots=True)
class EventMatch:
    item_key: str
    source: str
    title: str
    description: str
    category: str
    performer: str
    location: str
    start: datetime | None
    end: datetime | None
    score: float
    active: bool


@dataclass(frozen=True, slots=True)
class ScheduleReply:
    text: str
    needs_refinement: bool = False
    match_count: int = 0


def is_schedule_query(text: str) -> bool:
    normalized = " ".join(TOKEN_RE.findall(text.casefold()))
    words = set(normalized.split())
    discovery_phrase = (
        (normalized.startswith("where ") or normalized.startswith("when "))
        and bool(words & {"happening", "playing", "event", "events"})
    )
    timed_happening = bool(words & {"happen", "happens"}) and bool(
        DAY_RE.search(text) or _time_parts(text)
    )
    return timed_happening or discovery_phrase or bool(words & SCHEDULE_WORDS) or any(
        phrase in normalized for phrase in SCHEDULE_PHRASES
    )


def _parse_local(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = datetime.fromisoformat(value.strip())
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=PACIFIC)
    return parsed.astimezone(PACIFIC)


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.casefold())


def _query_tokens(text: str) -> list[str]:
    words = [word for word in _tokens(text) if word not in QUERY_STOPWORDS]
    expanded: list[str] = []
    for word in words:
        expanded.extend(EXPANSIONS.get(word, (word,)))
    return expanded


def _stem_token(word: str) -> str:
    return word[:-1] if len(word) > 4 and word.endswith("s") else word


def _specific_tokens(text: str) -> set[str]:
    generic = {
        "art", "installation", "music", "dj", "djs", "playing", "set", "sets",
        "camp", "camps", "happening", "where", "when", "any",
        "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "fifteen", "twenty", "thirty",
        "forty", "fifty", "oh", "am", "pm", "a", "p", "m", "neco",
    }
    days = {
        "monday", "mon", "tuesday", "tue", "tues", "wednesday", "wed",
        "thursday", "thu", "thur", "thurs", "friday", "fri", "saturday",
        "sat", "sunday", "sun",
    }
    return {
        _stem_token(word)
        for word in _tokens(text)
        if word not in QUERY_STOPWORDS
        and word not in generic
        and word not in days
        and not any(character.isdigit() for character in word)
    }


def is_schedule_refinement(text: str) -> bool:
    words = _tokens(text)
    if not words or len(words) > 8:
        return False
    return not bool(set(words) & {"story", "joke", "weather", "stop", "cancel", "mute"})


def requests_all_results(text: str) -> bool:
    normalized = " ".join(_tokens(text))
    phrases = (
        "no preference", "anything is fine", "anything", "all of them",
        "list them all", "list all", "tell me all", "show them all",
    )
    return normalized in phrases or any(phrase in normalized for phrase in phrases)


def _time_parts(query: str) -> tuple[int, int, str] | None:
    numeric = TIME_RE.search(query)
    if numeric:
        suffix = numeric.group(3).replace(".", "").casefold()
        return (
            int(numeric.group(1)),
            int(numeric.group(2) or 0),
            {"a": "am", "p": "pm"}.get(suffix, suffix),
        )
    bare = BARE_TIME_RE.search(query)
    if bare:
        # At this evening event, an unqualified "Saturday at 8" conventionally
        # means 8 PM. Explicit AM remains available and unambiguous.
        return (int(bare.group(1)), int(bare.group(2) or 0), "pm")
    words = WORD_TIME_RE.search(query)
    if not words:
        return None
    hours = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
        "twelve": 12,
    }
    minutes = {
        None: 0, "zero": 0, "five": 5, "ten": 10, "fifteen": 15,
        "twenty": 20, "twenty five": 25, "thirty": 30, "thirty five": 35,
        "forty": 40, "forty five": 45, "fifty": 50, "fifty five": 55,
    }
    return (
        hours[words.group(1).casefold()],
        minutes[(words.group(3) or "").casefold() or None],
        {"a": "am", "p": "pm"}.get(
            words.group(4).replace(".", "").casefold(),
            words.group(4).replace(".", "").casefold(),
        ),
    )


def _tfidf_cosines(query: str, documents: list[str]) -> list[float]:
    """Build a sparse TF-IDF vector space over only the filtered candidates."""

    if not documents:
        return []
    query_words = _query_tokens(query)
    if not query_words:
        return [0.0] * len(documents)
    doc_counts = [Counter(_tokens(document)) for document in documents]
    document_frequency: Counter[str] = Counter()
    for counts in doc_counts:
        document_frequency.update(counts.keys())
    total = len(documents)
    idf = {
        term: math.log((1 + total) / (1 + frequency)) + 1.0
        for term, frequency in document_frequency.items()
    }
    query_count = Counter(query_words)
    query_vector = {
        term: count * idf.get(term, math.log(1 + total) + 1.0)
        for term, count in query_count.items()
    }
    query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
    scores: list[float] = []
    for counts in doc_counts:
        vector = {term: count * idf[term] for term, count in counts.items()}
        norm = math.sqrt(sum(value * value for value in vector.values()))
        dot = sum(query_vector.get(term, 0.0) * value for term, value in vector.items())
        scores.append(dot / (query_norm * norm) if query_norm and norm else 0.0)
    return scores


def _published(item: dict[str, object]) -> bool:
    return item.get("status", 2) == 2 and item.get("moderation", 0) == 0


def _mature(item: dict[str, object]) -> bool:
    event_type = item.get("event_type")
    label = event_type.get("label", "") if isinstance(event_type, dict) else ""
    combined = f"{label} {item.get('camp', '')} {item.get('camp_type', '')}".casefold()
    return "mature 19+" in combined or "mature audiences" in combined or "19+" in combined


def _validate_payload(source: str, payload: list[object]) -> None:
    if not payload:
        raise ValueError(f"{source} feed is unexpectedly empty")
    required = {
        "schedule": {"uid", "title", "occurrence"},
        "music": {"uid", "occurrence"},
        "art": {"uid", "name"},
        "camps": {"uid", "name"},
    }[source]
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or not required <= item.keys():
            raise ValueError(f"{source} row {index} lacks its required schema")
        if source not in {"schedule", "music"}:
            continue
        occurrence = item["occurrence"]
        if not isinstance(occurrence, dict):
            raise ValueError(f"{source} row {index} occurrence is not an object")
        start = _parse_local(occurrence.get("start_time"))
        end = _parse_local(occurrence.get("end_time"))
        if start is None or end is None or end <= start:
            raise ValueError(f"{source} row {index} has an invalid time range")


def _records(
    source: str,
    payload: list[object],
    camp_context: dict[str, str] | None = None,
) -> Iterable[tuple[object, ...]]:
    camp_context = camp_context or {}
    for position, raw in enumerate(payload):
        if not isinstance(raw, dict) or not _published(raw):
            continue
        occurrence = raw.get("occurrence")
        occurrence = occurrence if isinstance(occurrence, dict) else {}
        uid = str(raw.get("uid") or raw.get("externalId") or position)
        start = _parse_local(occurrence.get("start_time"))
        end = _parse_local(occurrence.get("end_time"))
        performer = str(occurrence.get("who") or "").strip()
        title = str(raw.get("title") or raw.get("name") or performer or "Untitled").strip()
        description = str(raw.get("description") or "").strip()
        event_type = raw.get("event_type")
        event_label = event_type.get("label", "") if isinstance(event_type, dict) else ""
        category = str(
            event_label or raw.get("musicType") or raw.get("art_type")
            or raw.get("category") or raw.get("camp_type") or source
        ).strip()
        location = str(
            raw.get("location") or raw.get("camp") or raw.get("otherLocation") or ""
        ).strip()
        if source == "music" and performer:
            display_title = performer
        else:
            display_title = title
        start_text = start.isoformat() if start else ""
        end_text = end.isoformat() if end else ""
        occurrence_id = str(occurrence.get("id") or start_text or position)
        item_key = f"{source}:{uid}:{occurrence_id}"
        search_text = " ".join(
            (display_title, title, performer, description, category, location,
             str(raw.get("camp") or ""), source,
             camp_context.get(str(raw.get("campId") or raw.get("hosted_by_camp") or ""), ""),
             camp_context.get(str(raw.get("camp") or raw.get("location") or "").casefold(), ""),
            )
        )
        yield (
            item_key, source, uid, display_title, description, category, performer,
            location, start_text or None, end_text or None, int(_mature(raw)),
            search_text, json.dumps(raw, ensure_ascii=False, sort_keys=True),
        )


def build_database(payloads: dict[str, list[object]], target: Path, fetched_at: datetime) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix="what-if-", suffix=".sqlite3", delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        connection = sqlite3.connect(temporary)
        with connection:
            connection.executescript(
                """
                PRAGMA journal_mode=DELETE;
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE items (
                    item_key TEXT PRIMARY KEY, source TEXT NOT NULL, uid TEXT NOT NULL,
                    title TEXT NOT NULL, description TEXT NOT NULL, category TEXT NOT NULL,
                    performer TEXT NOT NULL, location TEXT NOT NULL,
                    starts_at TEXT, ends_at TEXT, mature INTEGER NOT NULL,
                    search_text TEXT NOT NULL, raw_json TEXT NOT NULL
                );
                CREATE INDEX items_time ON items(starts_at, ends_at);
                CREATE INDEX items_source ON items(source);
                """
            )
            camp_context: dict[str, str] = {}
            for raw in payloads["camps"]:
                if not isinstance(raw, dict):
                    continue
                context = f"{raw.get('name', '')} {raw.get('camp_type', '')} {raw.get('description', '')}"
                camp_context[str(raw.get("uid") or "")] = context
                camp_context[str(raw.get("name") or "").casefold()] = context
            for source in SOURCES:
                payload = payloads[source]
                connection.executemany(
                    "INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    _records(source, payload, camp_context),
                )
                encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
                connection.execute(
                    "INSERT INTO metadata VALUES (?, ?)",
                    (f"{source}_sha256", hashlib.sha256(encoded).hexdigest()),
                )
                connection.execute(
                    "INSERT INTO metadata VALUES (?, ?)",
                    (f"{source}_count", str(len(payload))),
                )
            connection.execute(
                "INSERT INTO metadata VALUES ('fetched_at', ?)",
                (fetched_at.astimezone(PACIFIC).isoformat(),),
            )
            connection.execute("INSERT INTO metadata VALUES ('timezone', 'America/Vancouver')")
            connection.execute("INSERT INTO metadata VALUES ('schema_version', '1')")
        connection.close()
        os.chmod(temporary, 0o644)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def refresh_cache(
    state_dir: Path = DEFAULT_STATE_DIR,
    *,
    base_url: str = BASE_URL,
    timeout_s: float = 20.0,
) -> Path:
    """Fetch all feeds and atomically replace snapshots/database only on success."""

    state_dir.mkdir(parents=True, exist_ok=True)
    payloads: dict[str, list[object]] = {}
    raw_bytes: dict[str, bytes] = {}
    for source in SOURCES:
        req = request.Request(
            f"{base_url}/{source}.json",
            headers={"User-Agent": "Neko-Kitty-Carrier/1 schedule-cache"},
        )
        with request.urlopen(req, timeout=timeout_s) as response:
            data = response.read(5_000_001)
        if len(data) > 5_000_000:
            raise ValueError(f"{source} feed exceeds 5 MB limit")
        payload = json.loads(data)
        if not isinstance(payload, list):
            raise ValueError(f"{source} feed is not a JSON array")
        _validate_payload(source, payload)
        payloads[source] = payload
        raw_bytes[source] = data
    fetched_at = datetime.now(PACIFIC)
    with tempfile.TemporaryDirectory(dir=state_dir, prefix="refresh-") as temp_name:
        temp_dir = Path(temp_name)
        for source, data in raw_bytes.items():
            (temp_dir / f"{source}.json").write_bytes(data)
        database = temp_dir / "what-if.sqlite3"
        build_database(payloads, database, fetched_at)
        for source in SOURCES:
            os.replace(temp_dir / f"{source}.json", state_dir / f"{source}.json")
        os.replace(database, state_dir / "what-if.sqlite3")
    return state_dir / "what-if.sqlite3"


class EventSchedule:
    """Read the immutable-on-replacement cache and rank a narrowed candidate set."""

    def __init__(self, database: Path = DEFAULT_DB) -> None:
        self.database = database

    def available(self) -> bool:
        return self.database.is_file()

    def fetched_at(self) -> datetime | None:
        if not self.available():
            return None
        with sqlite3.connect(self.database) as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key='fetched_at'"
            ).fetchone()
        return _parse_local(row[0]) if row else None

    def _festival_date(self, weekday: str) -> datetime | None:
        aliases = {
            "mon": "monday", "tue": "tuesday", "tues": "tuesday",
            "wed": "wednesday", "thu": "thursday", "thur": "thursday",
            "thurs": "thursday", "fri": "friday", "sat": "saturday",
            "sat day": "saturday", "sun": "sunday",
        }
        weekday = aliases.get(" ".join(weekday.casefold().split()), weekday)
        with sqlite3.connect(self.database) as connection:
            rows = connection.execute(
                "SELECT DISTINCT starts_at FROM items WHERE starts_at IS NOT NULL ORDER BY starts_at"
            )
            for (value,) in rows:
                parsed = _parse_local(value)
                if parsed and parsed.strftime("%A").casefold() == weekday.casefold():
                    return parsed
        return None

    def _reference_times(self, query: str, now: datetime) -> tuple[datetime, ...]:
        day_match = DAY_RE.search(query)
        time_parts = _time_parts(query)
        if not day_match and not time_parts:
            return (now,)
        base = self._festival_date(day_match.group(1)) if day_match else now
        if base is None:
            return (now,)
        if not time_parts:
            return (base.replace(hour=12, minute=0, second=0, microsecond=0),)
        hour, minute, meridiem = time_parts
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        return (base.replace(hour=hour, minute=minute, second=0, microsecond=0),)

    @staticmethod
    def _mode(query: str) -> str:
        normalized = " ".join(_tokens(query))
        words = set(normalized.split())
        has_day = DAY_RE.search(query) is not None
        has_time = _time_parts(query) is not None
        if has_day and not has_time:
            return "day"
        if has_time:
            return "point"
        if (
            normalized.startswith("when ")
            or normalized.startswith("where ")
            or normalized.startswith("is there ")
            or normalized.startswith("are there ")
            or " any art" in f" {normalized}"
            or " any camp" in f" {normalized}"
            or (
                bool(words & {"art", "installation", "camp", "camps"})
                and "now" not in words
            )
        ):
            return "discovery"
        return "now"

    def search(
        self,
        query: str,
        *,
        now: datetime | None = None,
        limit: int = 5,
        include_mature: bool = False,
    ) -> tuple[EventMatch, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        if not self.available():
            return ()
        current = (now or datetime.now(PACIFIC)).astimezone(PACIFIC)
        references = self._reference_times(query, current)
        mode = self._mode(query)
        wants_static = mode == "discovery" and bool(
            re.search(r"\b(art|installation|camp|camps)\b", query, re.IGNORECASE)
        )
        rows: dict[str, sqlite3.Row] = {}
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            if wants_static:
                for row in connection.execute(
                    "SELECT * FROM items WHERE starts_at IS NULL AND (? OR mature=0)",
                    (int(include_mature),),
                ):
                    rows[row["item_key"]] = row
            if mode == "day":
                day_start = references[0].replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                for row in connection.execute(
                    """
                    SELECT * FROM items
                    WHERE starts_at IS NOT NULL AND starts_at < ? AND ends_at > ?
                      AND (? OR mature=0)
                    """,
                    (day_end.isoformat(), day_start.isoformat(), int(include_mature)),
                ):
                    rows[row["item_key"]] = row
            elif mode == "discovery":
                for row in connection.execute(
                    """
                    SELECT * FROM items
                    WHERE starts_at IS NOT NULL AND ends_at > ? AND (? OR mature=0)
                    """,
                    (current.isoformat(), int(include_mature)),
                ):
                    rows[row["item_key"]] = row
            else:
                for reference in references:
                    latest_start = (reference + timedelta(minutes=30)).isoformat()
                    earliest_end = (reference + timedelta(minutes=15)).isoformat()
                    for row in connection.execute(
                        """
                        SELECT * FROM items
                        WHERE starts_at IS NOT NULL AND starts_at <= ? AND ends_at > ?
                          AND (? OR mature=0)
                        """,
                        (latest_start, earliest_end, int(include_mature)),
                    ):
                        rows[row["item_key"]] = row
        candidates = list(rows.values())
        words = set(_tokens(query))
        if "art" in words or "installation" in words:
            candidates = [
                row for row in candidates
                if row["source"] == "art"
                or (
                    "installation" not in words
                    and row["source"] == "schedule"
                    and bool(
                        set(_tokens(f"{row['category']} {row['title']}"))
                        & {"art", "arts", "craft", "crafts"}
                    )
                )
            ]
        elif words & {"music", "dj", "djs", "playing", "set", "sets"}:
            candidates = [
                row for row in candidates
                if row["source"] == "music"
                or (
                    row["source"] == "schedule"
                    and any(
                        marker in row["category"].casefold()
                        for marker in ("music", "dance", "performance")
                    )
                )
            ]
        elif words & {"camp", "camps"} and not words & {"event", "events", "happening"}:
            candidates = [row for row in candidates if row["source"] == "camps"]
        specific = _specific_tokens(query)
        if specific:
            candidates = [
                row for row in candidates
                if specific & {_stem_token(word) for word in _tokens(row["search_text"])}
            ]
        vectors = _tfidf_cosines(query, [row["search_text"] for row in candidates])
        results: list[EventMatch] = []
        music_request = bool(re.search(r"\b(music|dj|djs|playing|set|sets)\b", query, re.I))
        for row, similarity in zip(candidates, vectors, strict=True):
            start = _parse_local(row["starts_at"])
            end = _parse_local(row["ends_at"])
            ranking_reference = current if mode == "discovery" else min(
                references, key=lambda value: abs((start or value) - value)
            )
            active = bool(start and end and start <= ranking_reference < end)
            duration_h = max((end - start).total_seconds() / 3600, 0.05) if start and end else 8.0
            narrowness = 1.0 / (1.0 + duration_h)
            temporal = 1.0 if active else (0.8 if start else 0.15)
            source_boost = 0.8 if music_request and row["source"] == "music" else 0.0
            score = similarity * 4.0 + temporal + narrowness + source_boost
            results.append(
                EventMatch(
                    row["item_key"], row["source"], row["title"], row["description"],
                    row["category"], row["performer"], row["location"], start, end,
                    score, active,
                )
            )
        results.sort(
            key=lambda item: (
                -item.score,
                item.start or datetime.max.replace(tzinfo=PACIFIC),
                item.title.casefold(),
            )
        )
        return tuple(results[:limit])

    @staticmethod
    def _clock(value: datetime) -> str:
        rendered = value.astimezone(PACIFIC).strftime("%I:%M %p").lstrip("0")
        return rendered.replace(":00 ", " ")

    def respond(
        self,
        query: str,
        *,
        now: datetime | None = None,
        limit: int = 3,
        force_list: bool = False,
    ) -> ScheduleReply:
        if not self.available():
            return ScheduleReply(
                "My local What If schedule isn't ready yet. I can try again after it syncs."
            )
        current = (now or datetime.now(PACIFIC)).astimezone(PACIFIC)
        all_matches = self.search(query, now=current, limit=100)
        match_count = len(all_matches)
        specific = _specific_tokens(query)
        words = set(_tokens(query))
        if match_count > 3 and not specific and not force_list:
            if words & {"music", "dj", "djs", "playing", "set", "sets"}:
                prompt = (
                    f"I found {match_count} music choices then. What kind of music, "
                    "performer, or sound camp are you in the mood for?"
                )
            elif words & {"art", "installation"}:
                prompt = (
                    f"I found {match_count} art choices. What kind of art or name "
                    "should I look for?"
                )
            else:
                prompt = (
                    f"I found {match_count} things happening then. Do you want music, "
                    "art, food, a workshop, or something else?"
                )
            return ScheduleReply(prompt, needs_refinement=True, match_count=match_count)
        matches = all_matches if force_list else all_matches[:limit]
        if not matches:
            return ScheduleReply(
                "I don't see a matching kid-friendly event then in my local What If schedule.",
                match_count=0,
            )
        timed = [match for match in matches if match.start and match.end]
        static = [match for match in matches if not match.start]
        parts: list[str] = []
        for match in timed:
            assert match.start is not None and match.end is not None
            actually_active = match.start <= current < match.end
            if actually_active and self._mode(query) == "now":
                timing = f"is on now until {self._clock(match.end)}"
            else:
                timing = (
                    f"is on {match.start.strftime('%A')} from {self._clock(match.start)} "
                    f"until {self._clock(match.end)}"
                )
            location = f" at {match.location}" if match.location else ""
            parts.append(f"{match.title} {timing}{location}")
        for match in static:
            location = f" at {match.location}" if match.location else ""
            parts.append(f"{match.title}{location}")
        prefix = "In Pacific time, " if timed else ""
        return ScheduleReply(
            prefix + ". ".join(parts) + ".",
            match_count=match_count,
        )

    def answer(self, query: str, *, now: datetime | None = None, limit: int = 3) -> str:
        return self.respond(query, now=now, limit=limit).text
