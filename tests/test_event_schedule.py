from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from neko.event_schedule import (
    EventSchedule,
    PACIFIC,
    build_database,
    is_schedule_query,
    requests_all_results,
    refresh_cache,
)


def occurrence(title: str, start: str, end: str, **changes: object) -> dict[str, object]:
    item: dict[str, object] = {
        "uid": title.casefold().replace(" ", "-"),
        "title": title,
        "description": changes.pop("description", ""),
        "event_type": {"label": changes.pop("label", "Family Friendly")},
        "location": changes.pop("location", "Test Camp"),
        "status": 2,
        "moderation": 0,
        "occurrence": {"start_time": start, "end_time": end},
    }
    item.update(changes)
    return item


class EventScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "what-if.sqlite3"
        schedule = [
            occurrence("Ends too soon", "2026-07-25T19:00:00", "2026-07-25T20:15:00"),
            occurrence("Short craft", "2026-07-25T19:55:00", "2026-07-25T20:25:00"),
            occurrence("Starts at edge", "2026-07-25T20:30:00", "2026-07-25T21:00:00"),
            occurrence("Starts too late", "2026-07-25T20:31:00", "2026-07-25T21:00:00"),
            occurrence("All day gathering", "2026-07-25T00:00:00", "2026-07-26T00:00:00"),
            occurrence("Extra one", "2026-07-25T20:00:00", "2026-07-25T21:00:00"),
            occurrence("Extra two", "2026-07-25T20:10:00", "2026-07-25T21:10:00"),
            occurrence("Extra three", "2026-07-25T20:20:00", "2026-07-25T21:20:00"),
            occurrence(
                "Penguin Parade",
                "2026-07-26T10:00:00",
                "2026-07-26T11:00:00",
                description="Waddle with the penguins",
                location="Penguin Camp",
            ),
            occurrence(
                "Adults only",
                "2026-07-25T20:00:00",
                "2026-07-25T21:00:00",
                label="Mature 19+",
            ),
        ]
        music = [
            {
                "uid": "music-1",
                "title": "Saturday sounds",
                "location": "Moon Stage",
                "status": 2,
                "moderation": 0,
                "occurrence": {
                    "id": "one",
                    "who": "DJ Whiskers",
                    "start_time": "2026-07-25T20:05:00",
                    "end_time": "2026-07-25T21:05:00",
                },
            }
        ]
        art = [
            {
                "uid": "art-1",
                "name": "Moon Cat",
                "description": "A silver feline sculpture",
                "art_type": "Art",
                "status": 2,
                "moderation": 0,
            }
        ]
        camps = [
            {
                "uid": "camp-1",
                "name": "Cozy Camp",
                "description": "Blankets and cocoa",
                "camp_type": "Theme Camp",
                "status": 2,
                "moderation": 0,
            }
        ]
        build_database(
            {"schedule": schedule, "music": music, "art": art, "camps": camps},
            self.database,
            datetime(2026, 7, 17, 12, tzinfo=PACIFIC),
        )
        self.schedule = EventSchedule(self.database)
        self.now = datetime(2026, 7, 25, 20, tzinfo=PACIFIC)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_schedule_intent_phrases(self) -> None:
        self.assertTrue(is_schedule_query("What's happening now?"))
        self.assertTrue(is_schedule_query("Who is playing music?"))
        self.assertTrue(is_schedule_query("Where is yoga happening?"))
        self.assertFalse(is_schedule_query("Tell me another cat story"))
        self.assertFalse(is_schedule_query("Tell me about your cat-shaped cart"))
        self.assertFalse(is_schedule_query("Tell a story about a sunset"))

    def test_current_window_excludes_ending_and_starting_boundaries(self) -> None:
        titles = {item.title for item in self.schedule.search("what is happening now", now=self.now)}
        self.assertNotIn("Ends too soon", titles)
        self.assertNotIn("Starts too late", titles)
        self.assertIn("Short craft", titles)
        self.assertIn("Starts at edge", titles)

    def test_narrow_events_beat_all_day_entries(self) -> None:
        matches = self.schedule.search("what is happening now", now=self.now, limit=20)
        self.assertLess(
            [item.title for item in matches].index("Short craft"),
            [item.title for item in matches].index("All day gathering"),
        )

    def test_music_vector_ranking_uses_performer_and_source(self) -> None:
        match = self.schedule.search("what music or DJ is playing now", now=self.now, limit=1)[0]
        self.assertEqual(match.title, "DJ Whiskers")
        self.assertEqual(match.source, "music")

    def test_mature_events_are_cached_but_hidden_by_default(self) -> None:
        default = self.schedule.search("adults only event", now=self.now, limit=20)
        adult = self.schedule.search(
            "adults only event", now=self.now, limit=20, include_mature=True
        )
        self.assertNotIn("Adults only", {item.title for item in default})
        self.assertIn("Adults only", {item.title for item in adult})

    def test_static_art_is_searched_only_when_requested(self) -> None:
        self.assertEqual(
            self.schedule.search("find the silver cat art", now=self.now, limit=1)[0].title,
            "Moon Cat",
        )
        self.assertNotIn(
            "Moon Cat",
            {item.title for item in self.schedule.search("what is happening now", now=self.now)},
        )
        self.assertEqual(
            self.schedule.search("is there any penguin art installation", now=self.now),
            (),
        )

    def test_bare_saturday_at_eight_is_evening_and_spoken_as_pacific_12_hour(self) -> None:
        answer = self.schedule.answer("find Short craft Saturday at 8", now=self.now)
        self.assertIn("Pacific time", answer)
        self.assertIn("Saturday", answer)
        self.assertIn("8:25 PM", answer)
        self.assertNotIn("20:", answer)

    def test_many_generic_time_hits_request_refinement(self) -> None:
        reply = self.schedule.respond(
            "what was going on Saturday at 8pm", now=self.now
        )
        spoken_time = self.schedule.respond(
            "what was going on Saturday eight p.m.", now=self.now
        )
        exact_live_asr = self.schedule.respond(
            "whats going on Sat day at eight PM", now=self.now
        )
        normalized_policy_text = self.schedule.respond(
            "what s going on Sat day at eight PM", now=self.now
        )
        truncated_meridiem = self.schedule.respond(
            "what s going on Saturday at eight P", now=self.now
        )
        self.assertTrue(reply.needs_refinement)
        self.assertGreater(reply.match_count, 5)
        self.assertIn("music, art, food", reply.text)
        self.assertTrue(spoken_time.needs_refinement)
        self.assertTrue(exact_live_asr.needs_refinement)
        self.assertGreater(exact_live_asr.match_count, 5)
        self.assertTrue(normalized_policy_text.needs_refinement)
        self.assertGreater(normalized_policy_text.match_count, 5)
        self.assertTrue(truncated_meridiem.needs_refinement)
        self.assertGreater(truncated_meridiem.match_count, 5)
        music_refinement = self.schedule.respond(
            "what s going on Saturday at eight PM how about music", now=self.now
        )
        self.assertFalse(music_refinement.needs_refinement)
        self.assertEqual(music_refinement.match_count, 1)
        self.assertIn("DJ Whiskers", music_refinement.text)
        all_events = self.schedule.respond(
            "what s going on Saturday at eight PM",
            now=self.now,
            force_list=True,
        )
        self.assertFalse(all_events.needs_refinement)
        self.assertGreater(all_events.match_count, 5)
        self.assertIn("Short craft", all_events.text)
        self.assertIn("All day gathering", all_events.text)
        self.assertTrue(requests_all_results("No preference"))
        self.assertTrue(requests_all_results("Please list them all"))

    def test_when_and_where_queries_search_beyond_the_current_window(self) -> None:
        before_festival = datetime(2026, 7, 17, 12, tzinfo=PACIFIC)
        dj = self.schedule.search(
            "when is DJ Whiskers playing", now=before_festival, limit=1
        )[0]
        penguins = self.schedule.search(
            "where is the penguin thing happening", now=before_festival, limit=1
        )[0]
        self.assertEqual(dj.title, "DJ Whiskers")
        self.assertEqual(penguins.title, "Penguin Parade")
        answer = self.schedule.answer("when is DJ Whiskers playing", now=before_festival)
        self.assertIn("Saturday", answer)
        self.assertIn("8:05 PM", answer)
        self.assertIn("Moon Stage", answer)

    def test_refresh_failure_retains_existing_cache(self) -> None:
        state = Path(self.temp.name) / "state"
        state.mkdir()
        existing = state / "what-if.sqlite3"
        existing.write_bytes(b"old-cache")
        with mock.patch(
            "neko.event_schedule.request.urlopen", side_effect=OSError("offline")
        ):
            with self.assertRaises(OSError):
                refresh_cache(state)
        self.assertEqual(existing.read_bytes(), b"old-cache")

    def test_empty_refresh_feed_is_rejected(self) -> None:
        class EmptyResponse:
            def __enter__(self) -> "EmptyResponse":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self, _limit: int) -> bytes:
                return b"[]"

        state = Path(self.temp.name) / "empty-state"
        with mock.patch(
            "neko.event_schedule.request.urlopen", return_value=EmptyResponse()
        ):
            with self.assertRaisesRegex(ValueError, "unexpectedly empty"):
                refresh_cache(state)
        self.assertFalse((state / "what-if.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
