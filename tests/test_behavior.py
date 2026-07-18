from __future__ import annotations

import unittest

from neko.behavior import BehaviorConfig, BehaviorController, normalize_phrase
from neko.events import (
    Acknowledge,
    CancelAudio,
    DialogueRequest,
    GreetingRequest,
    PersonObservation,
    SetMuted,
    SetParked,
    TranscriptEvent,
)


class ConversationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = BehaviorController()

    def transcript(self, text: str, at: float = 10.0) -> TranscriptEvent:
        return TranscriptEvent(text=text, language="en", monotonic_s=at)

    def test_normalization_handles_case_and_punctuation(self) -> None:
        self.assertEqual(normalize_phrase(" Neko,  NEKO! "), "neko neko")

    def test_ignores_ordinary_speech_outside_session(self) -> None:
        self.assertEqual(self.controller.handle(self.transcript("tell me a story")), ())

    def test_wake_only_acknowledges(self) -> None:
        self.assertEqual(self.controller.handle(self.transcript("Neko, Neko!")), (Acknowledge(),))

    def test_wake_with_request_opens_dialogue(self) -> None:
        actions = self.controller.handle(self.transcript("Neko Neko, tell me a cat joke"))
        self.assertEqual(actions[0], Acknowledge())
        self.assertEqual(actions[1], DialogueRequest("tell me a cat joke", "en"))

    def test_observed_asr_wake_alias_opens_dialogue(self) -> None:
        actions = self.controller.handle(self.transcript("Eko Neko tell me something silly"))
        self.assertEqual(actions[0], Acknowledge())
        self.assertEqual(actions[1], DialogueRequest("tell me something silly", "en"))

    def test_second_observed_asr_wake_alias_opens_dialogue(self) -> None:
        actions = self.controller.handle(
            self.transcript("Echo Necho, tell me something silly")
        )
        self.assertEqual(actions[0], Acknowledge())
        self.assertEqual(actions[1], DialogueRequest("tell me something silly", "en"))

    def test_nico_asr_alias_is_removed_from_request(self) -> None:
        actions = self.controller.handle(
            self.transcript("Nico, what's going on Sat day at eight PM")
        )
        self.assertEqual(
            actions[1],
            DialogueRequest("what s going on sat day at eight pm", "en"),
        )

    def test_repetition_collapsed_asr_alias_only_matches_at_start(self) -> None:
        actions = self.controller.handle(self.transcript("Neko tell me something silly"))
        self.assertEqual(actions[1], DialogueRequest("tell me something silly", "en"))
        controller = BehaviorController()
        self.assertEqual(controller.handle(self.transcript("I saw Neko over there")), ())

    def test_followup_inside_session_does_not_require_address_prefix(self) -> None:
        self.controller.handle(self.transcript("Neko Neko", 1.0))
        self.assertEqual(
            self.controller.handle(self.transcript("another one", 2.0)),
            (DialogueRequest("another one", "en"),),
        )
        self.assertEqual(
            self.controller.handle(self.transcript("Neko, another one", 3.0)),
            (Acknowledge(), DialogueRequest("another one", "en")),
        )

    def test_expired_session_requires_wake_again(self) -> None:
        self.controller.handle(self.transcript("Neko Neko", 1.0))
        self.assertEqual(self.controller.handle(self.transcript("hello", 40.0)), ())

    def test_tail_purr_extension_renews_only_an_existing_session(self) -> None:
        self.controller.handle(self.transcript("Neko Neko", 1.0))
        self.controller.extend_active_session(25.0)
        self.assertEqual(
            self.controller.handle(self.transcript("another story", 40.0)),
            (DialogueRequest("another story", "en"),),
        )
        self.assertEqual(
            self.controller.handle(self.transcript("Neko another story", 41.0)),
            (Acknowledge(), DialogueRequest("another story", "en")),
        )
        inactive = BehaviorController()
        inactive.extend_active_session(25.0)
        self.assertEqual(inactive.handle(self.transcript("another story", 26.0)), ())

    def test_stop_requires_an_active_session_or_address_and_bypasses_model(self) -> None:
        self.assertEqual(self.controller.handle(self.transcript("stop")), ())
        self.controller.handle(self.transcript("Neko Neko", 11.0))
        self.assertEqual(
            self.controller.handle(self.transcript("stop", 12.0)),
            (CancelAudio(reason="voice-command"),),
        )
        self.assertFalse(self.controller.session_active)
        self.assertEqual(
            self.controller.handle(self.transcript("Neko stop")),
            (CancelAudio(reason="voice-command"),),
        )

    def test_sleep_words_close_session_without_model(self) -> None:
        for words in ("bye bye", "goodbye", "good bye"):
            with self.subTest(words=words):
                controller = BehaviorController()
                controller.handle(self.transcript("Neko Neko", 1.0))
                self.assertEqual(
                    controller.handle(self.transcript(words, 2.0)),
                    (CancelAudio(reason="sleep-word"),),
                )
                self.assertFalse(controller.session_active)

    def test_mute_fails_closed_until_unmute(self) -> None:
        self.assertEqual(self.controller.handle(self.transcript("mute")), ())
        actions = self.controller.handle(self.transcript("Neko mute"))
        self.assertEqual(actions, (CancelAudio(reason="mute"), SetMuted(True)))
        self.assertEqual(
            self.controller.handle(self.transcript("Neko stop", 10.5)),
            (CancelAudio(reason="voice-command"),),
        )
        self.assertEqual(self.controller.handle(self.transcript("Neko Neko", 11.0)), ())
        self.assertEqual(self.controller.handle(self.transcript("unmute", 12.0)), ())
        self.assertEqual(
            self.controller.handle(self.transcript("Neko unmute", 13.0))[0],
            SetMuted(False),
        )


class SocialTests(unittest.TestCase):
    def observation(self, **changes: object) -> PersonObservation:
        values = {
            "camera_id": "bench",
            "track_id": "ephemeral-1",
            "confidence": 0.9,
            "monotonic_s": 10.0,
            "stable_observations": 4,
            "dwell_s": 2.0,
            "estimated_distance_m": 2.0,
            "approaching": True,
        }
        values.update(changes)
        return PersonObservation(**values)  # type: ignore[arg-type]

    def test_never_greets_when_not_parked(self) -> None:
        controller = BehaviorController()
        self.assertEqual(controller.handle(self.observation()), ())

    def test_qualified_parked_observation_requests_greeting(self) -> None:
        controller = BehaviorController()
        controller.handle(SetParked(True, 1.0))
        self.assertEqual(
            controller.handle(self.observation()),
            (GreetingRequest("bench", "ephemeral-1", 2.0),),
        )

    def test_distance_confidence_stability_dwell_and_approach_gate(self) -> None:
        fields = {
            "confidence": 0.1,
            "stable_observations": 1,
            "dwell_s": 0.2,
            "estimated_distance_m": None,
            "approaching": False,
        }
        for field, bad_value in fields.items():
            with self.subTest(field=field):
                controller = BehaviorController()
                controller.handle(SetParked(True, 1.0))
                self.assertEqual(controller.handle(self.observation(**{field: bad_value})), ())

    def test_global_and_track_cooldowns_prevent_repeated_solicitation(self) -> None:
        cfg = BehaviorConfig(greeting_global_cooldown_s=10, greeting_track_cooldown_s=100)
        controller = BehaviorController(cfg)
        controller.handle(SetParked(True, 1.0))
        self.assertTrue(controller.handle(self.observation(monotonic_s=10.0)))
        self.assertEqual(
            controller.handle(self.observation(track_id="ephemeral-2", monotonic_s=15.0)),
            (),
        )
        self.assertEqual(controller.handle(self.observation(monotonic_s=50.0)), ())
        self.assertTrue(
            controller.handle(self.observation(track_id="ephemeral-2", monotonic_s=50.0))
        )

    def test_active_conversation_suppresses_proactive_greeting(self) -> None:
        controller = BehaviorController()
        controller.handle(SetParked(True, 1.0))
        controller.handle(TranscriptEvent("Neko Neko", "en", 2.0))
        self.assertEqual(controller.handle(self.observation(monotonic_s=3.0)), ())

    def test_expired_conversation_no_longer_suppresses_greeting(self) -> None:
        controller = BehaviorController(BehaviorConfig(session_timeout_s=5.0))
        controller.handle(SetParked(True, 1.0))
        controller.handle(TranscriptEvent("Neko Neko", "en", 2.0))
        self.assertEqual(
            controller.handle(self.observation(monotonic_s=8.0)),
            (GreetingRequest("bench", "ephemeral-1", 2.0),),
        )


if __name__ == "__main__":
    unittest.main()
