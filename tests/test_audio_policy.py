from __future__ import annotations

import unittest

from neko.audio_policy import (
    AudioNode,
    AudioPolicy,
    MIRROR_SINK,
    PROCESSED_SOURCE,
    choose_routes,
    is_respeaker,
)


def node(name: str, description: str = "", **properties: str) -> AudioNode:
    return AudioNode(name, description, properties)


RESPEAKER_SINK = node(
    "alsa_output.usb-SEEED_ReSpeaker.analog-stereo",
    "ReSpeaker 4 Mic Array",
    **{"device.vendor.id": "0x2886", "device.product.id": "0x0018"},
)
RESPEAKER_SOURCE = node(
    "alsa_input.usb-SEEED_ReSpeaker.analog-surround-21",
    "ReSpeaker 4 Mic Array",
    **{"alsa.card_name": "ReSpeaker 4 Mic Array (UAC1.0)"},
)
BLUETOOTH_SINK = node("bluez_output.headphones.1", **{"device.api": "bluez5"})
BLUETOOTH_SOURCE = node("bluez_input.headphones.0", **{"device.api": "bluez5"})
WEBCAM_SOURCE = node(
    "alsa_input.usb-webcam.analog-stereo",
    "C922 Pro Stream Webcam",
    **{"device.form_factor": "webcam"},
)


class AudioRouteChoiceTests(unittest.TestCase):
    def test_respeaker_usb_ids_and_text_are_stable_matches(self) -> None:
        self.assertTrue(is_respeaker(RESPEAKER_SINK))
        self.assertTrue(is_respeaker(RESPEAKER_SOURCE))
        self.assertFalse(is_respeaker(WEBCAM_SOURCE))

    def test_both_outputs_mirror_and_respeaker_microphone_wins(self) -> None:
        choice = choose_routes(
            [BLUETOOTH_SINK, RESPEAKER_SINK],
            [BLUETOOTH_SOURCE, WEBCAM_SOURCE, RESPEAKER_SOURCE],
        )
        self.assertEqual(choice.output_mode, "mirror")
        self.assertEqual(
            choice.output_names,
            (RESPEAKER_SINK.name, BLUETOOTH_SINK.name),
        )
        self.assertEqual(choice.source_kind, "respeaker")
        self.assertEqual(choice.source_name, RESPEAKER_SOURCE.name)

    def test_bluetooth_is_full_backup_when_respeaker_is_absent(self) -> None:
        choice = choose_routes(
            [BLUETOOTH_SINK],
            [WEBCAM_SOURCE, BLUETOOTH_SOURCE],
        )
        self.assertEqual(choice.output_mode, "bluetooth")
        self.assertEqual(choice.source_kind, "bluetooth")

    def test_webcam_is_last_microphone_fallback(self) -> None:
        choice = choose_routes([], [WEBCAM_SOURCE])
        self.assertEqual(choice.output_mode, "unmanaged")
        self.assertEqual(choice.source_kind, "webcam")


class FakeBackend:
    def __init__(self) -> None:
        self.sinks = [RESPEAKER_SINK, BLUETOOTH_SINK]
        self.sources = [RESPEAKER_SOURCE, BLUETOOTH_SOURCE, WEBCAM_SOURCE]
        self.defaults: dict[str, str] = {}
        self.loaded: list[tuple[str, str]] = []
        self.unloaded: list[int] = []
        self.stale = (44,)

    def stale_owned_modules(self) -> tuple[int, ...]:
        stale, self.stale = self.stale, ()
        return stale

    def nodes(self, kind: str) -> tuple[AudioNode, ...]:
        return tuple(self.sinks if kind == "sinks" else self.sources)

    def set_default(self, kind: str, name: str) -> None:
        self.defaults[kind] = name

    def load_mirror(self, members: tuple[str, str]) -> int:
        self.loaded.append(members)
        return 99

    def load_processed_source(self, master: str) -> int:
        self.loaded.append(("processed", master))
        return 100

    def unload_module(self, module_id: int) -> None:
        self.unloaded.append(module_id)


class AudioPolicyTests(unittest.TestCase):
    def test_mirror_is_loaded_once_and_stale_instance_is_removed(self) -> None:
        backend = FakeBackend()
        policy = AudioPolicy(backend)  # type: ignore[arg-type]

        policy.reconcile()
        policy.reconcile()

        self.assertEqual(backend.unloaded, [44])
        self.assertEqual(
            backend.loaded,
            [
                (RESPEAKER_SINK.name, BLUETOOTH_SINK.name),
                ("processed", RESPEAKER_SOURCE.name),
            ],
        )
        self.assertEqual(backend.defaults["sink"], MIRROR_SINK)
        self.assertEqual(backend.defaults["source"], PROCESSED_SOURCE)

    def test_source_hotplug_change_requests_voice_restart(self) -> None:
        backend = FakeBackend()
        restarts: list[bool] = []
        policy = AudioPolicy(backend, restart_voice=lambda: restarts.append(True))  # type: ignore[arg-type]
        policy.reconcile()

        backend.sinks = [BLUETOOTH_SINK]
        backend.sources = [BLUETOOTH_SOURCE, WEBCAM_SOURCE]
        policy.reconcile()

        self.assertEqual(restarts, [True])
        self.assertEqual(backend.defaults["sink"], BLUETOOTH_SINK.name)
        self.assertEqual(backend.defaults["source"], BLUETOOTH_SOURCE.name)
        self.assertIn(99, backend.unloaded)
        self.assertIn(100, backend.unloaded)


if __name__ == "__main__":
    unittest.main()
