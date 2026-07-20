from __future__ import annotations

import array
import importlib.util
from pathlib import Path
import unittest
import wave

from neko.audio_tagging import AudioTagResult, AudioTagger, should_meow_back


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = Path(
    "/home/neko/models/sherpa-onnx-zipformer-small-audio-tagging-2024-04-15"
)
FIXTURE = REPO_ROOT / "tests/fixtures/audio/human-meow-owner-20260719.wav"


class MeowBackPolicyTests(unittest.TestCase):
    def test_requires_empty_stt(self) -> None:
        result = AudioTagResult("Meow", 0.9, 0.9)
        self.assertFalse(should_meow_back("hello", result))

    def test_meow_score_must_be_strictly_above_ten_percent(self) -> None:
        self.assertFalse(
            should_meow_back("", AudioTagResult("Speech", 0.8, 0.10))
        )
        self.assertTrue(
            should_meow_back("", AudioTagResult("Speech", 0.8, 0.1001))
        )

    def test_music_and_mantra_are_owner_approved_alternates(self) -> None:
        self.assertTrue(should_meow_back("", AudioTagResult("Music", 0.2, 0.0)))
        self.assertTrue(should_meow_back("", AudioTagResult("Mantra", 0.2, 0.0)))
        self.assertFalse(should_meow_back("", AudioTagResult("Speech", 0.9, 0.01)))


@unittest.skipUnless(
    MODEL_ROOT.joinpath("model.int8.onnx").is_file()
    and MODEL_ROOT.joinpath("class_labels_indices.csv").is_file()
    and FIXTURE.is_file()
    and importlib.util.find_spec("sherpa_onnx") is not None,
    "local sherpa audio-tagging model/fixture is unavailable",
)
class LocalAudioTaggerIntegrationTests(unittest.TestCase):
    def test_owner_fixture_contains_a_strong_meow_example(self) -> None:
        # The 15.27-16.51 second event scored 0.414 during installation. Use a
        # slightly wider stable slice so minor VAD implementation changes do
        # not alter the model input used by this integration check.
        with wave.open(str(FIXTURE), "rb") as source:
            self.assertEqual(source.getframerate(), 16_000)
            source.setpos(int(15.2 * 16_000))
            raw = array.array("h", source.readframes(int(1.4 * 16_000)))
        samples = [value / 32768.0 for value in raw]
        tagger = AudioTagger(
            MODEL_ROOT / "model.int8.onnx",
            MODEL_ROOT / "class_labels_indices.csv",
            num_threads=2,
        )
        result = tagger.classify(samples)
        self.assertGreater(result.meow_score, 0.10)


if __name__ == "__main__":
    unittest.main()
