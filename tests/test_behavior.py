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

    def test_followup_inside_session_does_not_require_wake(self) -> None:
        self.controller.handle(self.transcript("Neko Neko", 1.0))
        self.assertEqual(
            self.controller.handle(self.transcript("another one", 2.0)),
            (DialogueRequest("another one", "en"),),
        )

    def test_expired_session_requires_wake_again(self) -> None:
        self.controller.handle(self.transcript("Neko Neko", 1.0))
        self.assertEqual(self.controller.handle(self.transcript("hello", 40.0)), ())

    def test_stop_bypasses_wake_and_model(self) -> None:
        self.assertEqual(
            self.controller.handle(self.transcript("stop")),
            (CancelAudio(reason="voice-command"),),
        )

    def test_mute_fails_closed_until_unmute(self) -> None:
        actions = self.controller.handle(self.transcript("mute"))
        self.assertEqual(actions, (CancelAudio(reason="mute"), SetMuted(True)))
        self.assertEqual(self.controller.handle(self.transcript("Neko Neko", 11.0)), ())
        self.assertEqual(self.controller.handle(self.transcript("unmute", 12.0))[0], SetMuted(False))


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
