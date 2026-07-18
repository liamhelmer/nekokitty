from __future__ import annotations

from types import SimpleNamespace
import random
import threading
import unittest

from neko.cat_audio import CatAudioDenied
from neko.event_schedule import ScheduleReply
from neko.events import DialogueRequest
from scripts.neko_voice_assistant import ContinuousSpeechInput
from scripts.neko_voice_assistant import VoiceAssistant
from scripts.neko_voice_assistant import canonicalize_wake_transcript
from scripts.neko_voice_assistant import wake_is_in_prefix_window


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


class FakeStopKeywordSpotter(FakeKeywordSpotter):
    def __init__(self) -> None:
        self.pending = True

    def is_ready(self, _stream: FakeKeywordStream) -> bool:
        return self.pending

    def decode_stream(self, _stream: FakeKeywordStream) -> None:
        return None

    def get_result(self, _stream: FakeKeywordStream) -> str:
        return "STOP_NEKO_STOP"

    def reset_stream(self, _stream: FakeKeywordStream) -> None:
        self.pending = False


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
    def test_kws_canonicalizes_noisy_repeated_address_tokens(self) -> None:
        self.assertEqual(
            canonicalize_wake_transcript(
                "Neco Neko, what's going on Saturday at eight P"
            ),
            "Neko what s going on saturday at eight p",
        )

    def test_wake_keyword_is_limited_to_the_utterance_prefix(self) -> None:
        self.assertFalse(wake_is_in_prefix_window(0))
        self.assertTrue(wake_is_in_prefix_window(1))
        self.assertTrue(wake_is_in_prefix_window(62))
        self.assertFalse(wake_is_in_prefix_window(63))

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

    def test_neko_stop_keyword_marks_segment_and_cancels_immediately(self) -> None:
        stops: list[bool] = []
        source = ContinuousSpeechInput(
            "fake",
            FakeVad(),
            FakeStopKeywordSpotter(),
            FakeRecognizer(),
            "en",
            lambda: None,
            lambda: None,
            lambda: stops.append(True),
        )

        source._accept_samples([0.1] * 512)
        source._accept_samples([0.2] * 512)
        source._accept_samples([0.0] * 512)

        self.assertEqual(stops, [True])
        self.assertTrue(source.segments.get_nowait().stop_detected)


class VoiceAssistantMixedAudioTests(unittest.TestCase):
    def test_empty_schedule_refinement_lists_original_window(self) -> None:
        class FakeSchedule:
            def __init__(self) -> None:
                self.calls: list[tuple[str, bool]] = []

            def available(self) -> bool:
                return True

            def respond(self, query: str, *, force_list: bool = False) -> ScheduleReply:
                self.calls.append((query, force_list))
                if force_list:
                    return ScheduleReply("All seven original choices.", False, 7)
                if len(self.calls) == 1:
                    return ScheduleReply("Which kind?", True, 7)
                return ScheduleReply("No match.", False, 0)

        spoken: list[str] = []
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.pending_schedule_query = None
        assistant.pending_schedule_base_query = None
        assistant.event_schedule = FakeSchedule()
        assistant.current_vad_finalized_s = 1.0
        assistant._start_thinking_cue = lambda _text: None
        assistant._stop_thinking_cue_for_speech = lambda: None
        assistant._stop_tail_purr_for_neko_speech = lambda: None
        assistant._speak = lambda text, **_values: spoken.append(text) is None or True
        assistant._event = lambda _kind, **_values: None
        assistant.controller = SimpleNamespace(extend_active_session=lambda _now: None)

        assistant._dialogue(DialogueRequest("what is happening Saturday at 8 PM", "en"))
        assistant._dialogue(DialogueRequest("polka music", "en"))

        self.assertIn("I couldn't find a match", spoken[-1])
        self.assertIn("All seven original choices", spoken[-1])
        self.assertEqual(
            assistant.event_schedule.calls[-1],
            ("what is happening Saturday at 8 PM", True),
        )
        self.assertIsNone(assistant.pending_schedule_query)
        self.assertIsNone(assistant.pending_schedule_base_query)

    def test_schedule_lookup_is_ephemeral_and_refinement_keeps_tool_state(self) -> None:
        class FakeSchedule:
            def __init__(self) -> None:
                self.queries: list[str] = []

            def available(self) -> bool:
                return True

            def respond(self, query: str, *, force_list: bool = False) -> ScheduleReply:
                self.queries.append(query)
                if force_list:
                    return ScheduleReply("All seven choices.", False, 7)
                if len(self.queries) == 1:
                    return ScheduleReply("Which kind?", True, 12)
                return ScheduleReply("House Cat plays Saturday at 8 PM.", False, 2)

        class NoScheduleHistory:
            def append(self, *_args: object) -> None:
                raise AssertionError("schedule result polluted LLM history")

            def append_interrupted(self, *_args: object) -> None:
                raise AssertionError("schedule interruption polluted LLM history")

        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.pending_schedule_query = None
        assistant.pending_schedule_base_query = None
        assistant.event_schedule = FakeSchedule()
        assistant.history = NoScheduleHistory()
        assistant.current_vad_finalized_s = 1.0
        assistant._start_thinking_cue = lambda _text: None
        assistant._stop_thinking_cue_for_speech = lambda: None
        assistant._stop_tail_purr_for_neko_speech = lambda: None
        assistant._speak = lambda _text, **_values: True
        assistant._event = lambda _kind, **_values: None
        assistant.controller = SimpleNamespace(extend_active_session=lambda _now: None)

        self.assertTrue(
            assistant._dialogue(DialogueRequest("what is happening Saturday at 8 PM", "en"))
        )
        self.assertIsNotNone(assistant.pending_schedule_query)
        self.assertTrue(assistant._dialogue(DialogueRequest("house music", "en")))
        self.assertIsNone(assistant.pending_schedule_query)
        self.assertEqual(
            assistant.event_schedule.queries,
            [
                "what is happening Saturday at 8 PM",
                "what is happening Saturday at 8 PM house music",
            ],
        )

    def test_story_ignores_ordinary_speech_but_wake_phrase_arms_barge_in(self) -> None:
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.story_playing = threading.Event()
        assistant.story_playing.set()
        assistant.story_followup_pending = threading.Event()
        assistant.story_interrupt_armed = threading.Event()
        assistant.self_wake_guard = threading.Event()
        assistant.ignored_story_sequences = set()
        assistant.cancel_speech = threading.Event()
        assistant.speaking = threading.Event()
        assistant.speaking.set()
        assistant.spoken_turn_active = threading.Event()
        assistant.spoken_turn_active.set()
        assistant.audio = SimpleNamespace(speech_sequence=7)
        events: list[str] = []
        assistant._event = lambda kind, **_values: events.append(kind)

        assistant._on_speech_start()
        self.assertFalse(assistant.cancel_speech.is_set())
        self.assertIn(7, assistant.ignored_story_sequences)

        assistant._on_wake()
        self.assertTrue(assistant.cancel_speech.is_set())
        self.assertTrue(assistant.story_followup_pending.is_set())
        self.assertIn("addressed_barge_in_armed", events)

    def test_regular_output_also_ignores_nonwake_barge_in(self) -> None:
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.story_playing = threading.Event()
        assistant.story_followup_pending = threading.Event()
        assistant.story_interrupt_armed = threading.Event()
        assistant.self_wake_guard = threading.Event()
        assistant.ignored_story_sequences = set()
        assistant.cancel_speech = threading.Event()
        assistant.speaking = threading.Event()
        assistant.speaking.set()
        assistant.spoken_turn_active = threading.Event()
        assistant.spoken_turn_active.set()
        assistant.audio = SimpleNamespace(speech_sequence=9)
        assistant._event = lambda _kind, **_values: None

        assistant._on_speech_start()
        self.assertFalse(assistant.cancel_speech.is_set())
        self.assertIn(9, assistant.ignored_story_sequences)

    def test_neko_saying_her_name_does_not_trigger_her_own_wake_word(self) -> None:
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.story_followup_pending = threading.Event()
        assistant.story_interrupt_armed = threading.Event()
        assistant.self_wake_guard = threading.Event()
        assistant.self_wake_guard.set()
        assistant.cancel_speech = threading.Event()
        assistant.speaking = threading.Event()
        assistant.speaking.set()
        assistant.spoken_turn_active = threading.Event()
        assistant.spoken_turn_active.set()
        events: list[str] = []
        assistant._event = lambda kind, **_values: events.append(kind)

        self.assertFalse(assistant._on_wake())
        self.assertFalse(assistant.cancel_speech.is_set())
        self.assertEqual(events, ["self_wake_echo_ignored"])

    def test_cat_sound_alone_does_not_require_addressed_barge_in(self) -> None:
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.story_followup_pending = threading.Event()
        assistant.story_interrupt_armed = threading.Event()
        assistant.self_wake_guard = threading.Event()
        assistant.ignored_story_sequences = set()
        assistant.cancel_speech = threading.Event()
        assistant.speaking = threading.Event()
        assistant.speaking.set()
        assistant.spoken_turn_active = threading.Event()
        assistant.audio = SimpleNamespace(speech_sequence=11)
        assistant._event = lambda _kind, **_values: None

        assistant._on_speech_start()

        self.assertFalse(assistant.cancel_speech.is_set())
        self.assertNotIn(11, assistant.ignored_story_sequences)

    def test_response_scaffold_inserts_meow_between_sentences(self) -> None:
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.args = SimpleNamespace(response_cue_rate=1.0)
        assistant._cue_rng = random.Random(7)
        self.assertEqual(
            assistant._insert_response_cue(
                "Tell me a cat story",
                "Mittens found a moonbeam. Then she tucked it in her pocket.",
            ),
            "Mittens found a moonbeam. [meow] Then she tucked it in her pocket.",
        )

    def test_response_scaffold_leaves_short_single_sentence_alone(self) -> None:
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.args = SimpleNamespace(response_cue_rate=1.0)
        assistant._cue_rng = random.Random(7)
        self.assertEqual(
            assistant._insert_response_cue("Hi", "Hi, Liam!"),
            "Hi, Liam!",
        )

    def test_story_forces_one_light_inter_sentence_meow(self) -> None:
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.args = SimpleNamespace(response_cue_rate=0.0)
        assistant._cue_rng = random.Random(7)
        self.assertEqual(
            assistant._insert_response_cue(
                "Tell me a story",
                "Pip found a feather. It tickled her whiskers.",
            ),
            "Pip found a feather. [meow] It tickled her whiskers.",
        )

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
        assistant.cancel_cat_sound = threading.Event()
        assistant.speaking = threading.Event()
        assistant.spoken_turn_active = threading.Event()
        assistant.story_interrupt_armed = threading.Event()
        assistant.self_wake_guard = threading.Event()
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
