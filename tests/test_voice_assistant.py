from __future__ import annotations

from types import SimpleNamespace
import threading
import unittest

from neko.cat_audio import CatAudioDenied
from scripts.neko_voice_assistant import ContinuousSpeechInput
from scripts.neko_voice_assistant import VoiceAssistant


class FakeVad:
    def __init__(self) -> None:
        self.frames: list[list[float]] = []
        self.pending = False
        self.front = SimpleNamespace(samples=[0.1, 0.2, 0.0])

    def accept_waveform(self, samples: list[float]) -> None:
        self.frames.append(samples)
        if len(self.frames) == 3:
            self.pending = True

    def is_speech_detected(self) -> bool:
        return len(self.frames) < 3

    def empty(self) -> bool:
        return not self.pending

    def pop(self) -> None:
        self.pending = False


class FakeKeywordStream:
    def accept_waveform(self, _rate: int, _samples: list[float]) -> None:
        return None


class FakeKeywordSpotter:
    def create_stream(self) -> FakeKeywordStream:
        return FakeKeywordStream()

    def is_ready(self, _stream: FakeKeywordStream) -> bool:
        return False


class FakeAsrStream:
    def __init__(self) -> None:
        self.frames: list[tuple[float, ...]] = []
        self.finished = False
        self.language = ""

    def set_option(self, _name: str, value: str) -> None:
        self.language = value

    def accept_waveform(self, _rate: int, samples: tuple[float, ...] | list[float]) -> None:
        self.frames.append(tuple(samples))

    def input_finished(self) -> None:
        self.finished = True


class FakeRecognizer:
    def __init__(self) -> None:
        self.stream: FakeAsrStream | None = None

    def create_stream(self) -> FakeAsrStream:
        self.stream = FakeAsrStream()
        return self.stream

    def is_ready(self, _stream: FakeAsrStream) -> bool:
        return False

    def get_result_all(self, stream: FakeAsrStream) -> SimpleNamespace:
        if not stream.finished:
            raise AssertionError("ASR stream was not finalized")
        return SimpleNamespace(text="Neko Neko tell me something silly")


class VoiceAssistantInputTests(unittest.TestCase):
    def test_asr_runs_during_capture_and_is_attached_to_vad_segment(self) -> None:
        recognizer = FakeRecognizer()
        speech_starts: list[bool] = []
        source = ContinuousSpeechInput(
            "fake",
            FakeVad(),
            FakeKeywordSpotter(),
            recognizer,
            "en",
            lambda: speech_starts.append(True),
            lambda: None,
        )

        source._accept_samples([0.1] * 512)
        source._accept_samples([0.2] * 512)
        source._accept_samples([0.0] * 512)

        segment = source.segments.get_nowait()
        self.assertEqual(speech_starts, [True])
        self.assertEqual(segment.transcript, "Neko Neko tell me something silly")
        self.assertEqual(segment.sequence, 1)
        self.assertGreaterEqual(segment.asr_finalize_seconds, 0.0)
        assert recognizer.stream is not None
        self.assertEqual(recognizer.stream.language, "en")
        self.assertEqual(len(recognizer.stream.frames), 3)


class VoiceAssistantMixedAudioTests(unittest.TestCase):
    def test_disabled_cat_marker_falls_back_to_tts_and_remains_interruptible(self) -> None:
        class FakeTts:
            def __init__(self) -> None:
                self.texts: list[str] = []

            def synthesize(self, text: str, **values: object) -> dict[str, object]:
                self.texts.append(text)
                callback = values.get("on_first_pcm")
                assert callable(callback)
                callback()
                return {"cancelled": False}

        class DisabledCatalog:
            def select(self, *_args: object, **_values: object) -> object:
                raise CatAudioDenied("cat-sound runtime is disabled")

        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.args = SimpleNamespace(
            no_speak=False,
            min_silence_seconds=0.6,
            cat_sound_output="speaker",
        )
        assistant.cancel_speech = threading.Event()
        assistant.speaking = threading.Event()
        assistant.tts = FakeTts()
        assistant.cat_sounds = DisabledCatalog()
        assistant.cat_sound_player = None
        events: list[tuple[str, dict[str, object]]] = []
        assistant._event = lambda kind, **values: events.append((kind, values))

        self.assertTrue(assistant._speak("[purr] Cozy!"))
        self.assertEqual(assistant.tts.texts, ["purr", "Cozy!"])
        self.assertFalse(assistant.speaking.is_set())
        self.assertEqual(
            [kind for kind, _values in events].count("first_pcm_written"),
            1,
        )
        self.assertIn("cat_sound_fallback", [kind for kind, _values in events])


if __name__ == "__main__":
    unittest.main()
