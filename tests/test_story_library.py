from __future__ import annotations

import json
import os
from pathlib import Path
import random
import re
import tempfile
import unittest

from neko.story_library import DEFAULT_RECORDING_MANIFEST, StoryLibrary


class StoryLibraryTests(unittest.TestCase):
    def test_returns_only_approved_local_story_text(self) -> None:
        stories = StoryLibrary().search("gummy worms otherworld")
        self.assertEqual(stories[0].story_id, "original.magic-girl-gummy-worm-moon")
        self.assertIn("Magic Girl", stories[0].text)
        self.assertNotIn("Clever cat", [story.title for story in stories])

    def test_choice_avoids_immediate_repeat_and_strips_markdown(self) -> None:
        library = StoryLibrary()
        first = library.choose("story")
        second = library.choose("story", exclude_id=first.story_id)
        self.assertNotEqual(first.story_id, second.story_id)
        spoken = library.spoken_text(first)
        self.assertFalse(spoken.startswith("#"))
        self.assertNotIn("**", spoken)
        self.assertNotIn("*", spoken)

    def test_specific_character_query_does_not_randomize_to_unrelated_story(self) -> None:
        story = StoryLibrary().choose("tell me a story about Luna")
        self.assertEqual(story.story_id, "original.luna-stick-garden")

    def test_context_note_is_bounded_metadata_not_full_story(self) -> None:
        library = StoryLibrary()
        story = library.choose("Magic Girl moon")
        note = library.context_note(story)
        self.assertIn(story.title, note)
        self.assertIn("Summary:", note)
        self.assertLess(len(note), 600)
        self.assertNotIn("One, two—banana", note)

    def test_story_audio_density_is_bounded_and_reserves_tail_purr(self) -> None:
        library = StoryLibrary()
        for story in library.search("story", limit=5):
            spoken = library.spoken_text(story)
            words = len(re.findall(r"\b[\w’'-]+\b", spoken))
            total_budget = library.sound_budget(spoken)
            rendered = library.with_audio_cues(spoken, rng=random.Random(7))
            inline = rendered.count("[meow]") + rendered.count("[meow:thanks]")
            with self.subTest(story=story.story_id):
                self.assertEqual(inline, total_budget - 1)
                self.assertGreaterEqual(words / total_budget, 50)
                self.assertLessEqual(words / total_budget, 100)
                self.assertIn("[meow]", rendered)
                self.assertIn("[meow:thanks]", rendered)
                self.assertFalse(rendered.startswith("["))
                self.assertFalse(rendered.endswith("]"))

    def test_short_story_does_not_force_an_inline_sound(self) -> None:
        text = "A tiny cat waved."
        self.assertEqual(StoryLibrary.sound_budget(text), 1)
        self.assertEqual(StoryLibrary.with_audio_cues(text), text)

    def test_every_approved_story_has_hash_verified_mini_recordings(self) -> None:
        library = StoryLibrary()
        section_count = 0
        for story in library.search("story", limit=100):
            recording = library.recording_for(story)
            with self.subTest(story=story.story_id):
                self.assertIsNotNone(recording)
                assert recording is not None
                self.assertTrue(recording.sections)
                self.assertTrue(all(item.path.suffix == ".flac" for item in recording.sections))
                self.assertTrue(
                    all(
                        item.cue_after in (None, "meow_general", "meow_thank_you")
                        for item in recording.sections
                    )
                )
                section_count += len(recording.sections)
        self.assertEqual(section_count, 53)

    def test_stale_source_hash_rejects_recording(self) -> None:
        library = StoryLibrary()
        story = library.choose("Luna stick garden")
        entry = library.recordings[story.story_id]
        original = entry["source_sha256"]
        entry["source_sha256"] = "0" * 64
        try:
            with self.assertRaisesRegex(ValueError, "source is stale"):
                library.recording_for(story)
        finally:
            entry["source_sha256"] = original

    def test_recording_manifest_hot_reloads_after_background_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            data = json.loads(DEFAULT_RECORDING_MANIFEST.read_text(encoding="utf-8"))
            manifest.write_text(json.dumps(data), encoding="utf-8")
            library = StoryLibrary(recording_manifest_path=manifest)
            story = library.choose("Luna stick garden")
            self.assertIsNotNone(library.recording_for(story))

            data["stories"] = [
                item for item in data["stories"] if item["story_id"] != story.story_id
            ]
            replacement = manifest.with_suffix(".tmp")
            replacement.write_text(json.dumps(data), encoding="utf-8")
            replacement.replace(manifest)
            current = manifest.stat().st_mtime_ns
            os.utime(manifest, ns=(current + 1_000_000, current + 1_000_000))
            self.assertIsNone(library.recording_for(story))


if __name__ == "__main__":
    unittest.main()
