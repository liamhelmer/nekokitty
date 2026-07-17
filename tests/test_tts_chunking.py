from __future__ import annotations

import unittest

from neko.tts_chunking import chunk_text


class TtsChunkingTests(unittest.TestCase):
    def test_questions_and_exclamations_keep_prosody(self) -> None:
        self.assertEqual(
            chunk_text("Are you ready? I am! This is Neko."),
            ["Are you ready?", "I am!", "This is Neko."],
        )

    def test_abbreviation_decimal_and_time_are_not_sentence_breaks(self) -> None:
        self.assertEqual(
            chunk_text("Dr. Neko arrives at 3:30 p.m. Ready?"),
            ["Dr. Neko arrives at 3:30 p.m.", "Ready?"],
        )
        self.assertEqual(
            chunk_text("Version 1.2 is quick. Good!"),
            ["Version 1.2 is quick.", "Good!"],
        )

    def test_unpunctuated_tail_receives_comma(self) -> None:
        self.assertEqual(chunk_text("A soft hello"), ["A soft hello,"])

    def test_long_sentence_splits_only_at_words(self) -> None:
        chunks = chunk_text("one two three four five six seven", max_len=13)
        self.assertEqual(chunks, ["one two three,", "four five six,", "seven,"])

    def test_invalid_max_length_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            chunk_text("hello", max_len=0)


if __name__ == "__main__":
    unittest.main()
