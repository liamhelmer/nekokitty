from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import random
import tempfile
import threading
import unittest
from unittest.mock import patch

from neko.cat_audio import (
    CatAudioDenied,
    CatSoundCatalog,
    CatSoundPart,
    CatSoundPlayer,
    TextPart,
    db_to_linear,
    parse_audio_script,
    peak_limited_gain_db,
    playback_multiplier,
)


class CatAudioNormalizationTests(unittest.TestCase):
    def test_db_conversion(self) -> None:
        self.assertAlmostEqual(db_to_linear(0.0), 1.0)
        self.assertAlmostEqual(db_to_linear(20.0), 10.0)

    def test_quiet_source_retains_replaygain_correction(self) -> None:
        applied = peak_limited_gain_db(12.28, 0.05584717, 0.35)
        self.assertAlmostEqual(applied, 12.28)

    def test_peak_heavy_source_is_limited(self) -> None:
        multiplier, applied, peak = playback_multiplier(13.81, 0.99267578, 0.35)
        self.assertLess(applied, 13.81)
        self.assertAlmostEqual(peak, 10 ** (-1.0 / 20.0))
        self.assertGreater(multiplier, 0.0)

    def test_invalid_peak_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            peak_limited_gain_db(1.0, 0.0, 0.35)
        with self.assertRaises(ValueError):
            peak_limited_gain_db(1.0, math.inf, 0.35)


class AudioScriptTests(unittest.TestCase):
    def test_only_strict_markers_become_semantic_actions(self) -> None:
        parts = parse_audio_script("[purr] You're funny! [meow]")
        self.assertEqual(
            parts,
            (
                CatSoundPart("purr_short", "purr"),
                TextPart("You're funny!"),
                CatSoundPart("meow_general", "meow"),
            ),
        )
        self.assertEqual(
            parse_audio_script("Cats purr when comfy."),
            (TextPart("Cats purr when comfy."),),
        )

    def test_marker_count_is_bounded(self) -> None:
        parts = parse_audio_script("[meow] [purr] [meow]", max_markers=1)
        self.assertEqual(parts[0], CatSoundPart("meow_general", "meow"))
        self.assertEqual(parts[1], TextPart("[purr] [meow]"))

    def test_emotion_and_specific_sound_cues_are_closed_and_semantic(self) -> None:
        parts = parse_audio_script(
            "[feeling:curious] What is that? [purr:playful] Let's peek!"
        )
        self.assertEqual(
            parts,
            (
                CatSoundPart("meow_general", "meow"),
                TextPart("What is that?"),
                CatSoundPart("purr_playful_affection", "purr"),
                TextPart("Let's peek!"),
            ),
        )
        self.assertEqual(
            parse_audio_script("[feeling:worried] Nope."),
            (TextPart("[feeling:worried] Nope."),),
        )
        self.assertEqual(
            parse_audio_script("That was lovely. [purr:tail]"),
            (
                TextPart("That was lovely."),
                CatSoundPart("purr_primary", "purr"),
            ),
        )


class CatSoundCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        asset_dir = self.root / "assets"
        asset_dir.mkdir()
        entries = []
        for name in ("one", "two"):
            path = asset_dir / f"{name}.wav"
            path.write_bytes(f"sound-{name}".encode())
            entries.append(
                {
                    "asset_id": f"{name}.speaker.v1",
                    "repo_path": f"assets/{name}.wav",
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "target_output": "speaker",
                    "duration_seconds": 0.5,
                    "approvals": {
                        "derived_content_review": "accepted",
                        "hardware_acceptance": "accepted",
                        "release_status": "accepted",
                    },
                }
            )
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"entries": entries}))
        allowlist = self.root / "allowlist.json"
        allowlist.write_text(
            json.dumps(
                {
                    "default_policy": "deny",
                    "runtime_status": "enabled",
                    "actions": {
                        "meow_general": {
                            "enabled": True,
                            "autonomous_allowed": True,
                            "allowed_outputs": ["speaker"],
                            "candidates": [
                                {"asset_id": "one.speaker.v1", "weight": 1},
                                {"asset_id": "two.speaker.v1", "weight": 1},
                            ],
                            "cooldown_seconds": 3,
                            "max_duration_seconds": 2,
                            "min_gain_db": -18,
                            "max_gain_db": 0,
                            "default_gain_db": -3,
                            "interruptible": True,
                        }
                    },
                }
            )
        )
        self.catalog = CatSoundCatalog(
            manifest,
            allowlist,
            repo_root=self.root,
            rng=random.Random(7),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_selection_is_integrity_checked_nonrepeating_and_cooled_down(self) -> None:
        first = self.catalog.select("meow_general", "speaker", now=10)
        self.assertEqual(first.gain_db, -3)
        self.catalog.mark_played(first, now=10)
        with self.assertRaisesRegex(CatAudioDenied, "cooling down"):
            self.catalog.select("meow_general", "speaker", now=12)
        second = self.catalog.select("meow_general", "speaker", now=13)
        self.assertNotEqual(first.asset_id, second.asset_id)

    def test_supervisor_can_start_an_explicit_continuous_state_during_cooldown(self) -> None:
        first = self.catalog.select("meow_general", "speaker", now=10)
        self.catalog.mark_played(first, now=10)
        selection = self.catalog.select(
            "meow_general",
            "speaker",
            now=11,
            enforce_cooldown=False,
        )
        self.assertIn(selection.asset_id, {"one.speaker.v1", "two.speaker.v1"})

    def test_unknown_raw_global_and_action_disable_fail_closed(self) -> None:
        with self.assertRaisesRegex(CatAudioDenied, "unknown"):
            self.catalog.select("assets/one.wav", "speaker", now=10)
        self.catalog.runtime_enabled = False
        with self.assertRaisesRegex(CatAudioDenied, "runtime is disabled"):
            self.catalog.select("meow_general", "speaker", now=10)
        self.catalog.runtime_enabled = True
        self.catalog.allowlist["actions"]["meow_general"]["enabled"] = False
        with self.assertRaisesRegex(CatAudioDenied, "disabled"):
            self.catalog.select("meow_general", "speaker", now=10)

    def test_pending_or_modified_assets_fail_closed(self) -> None:
        self.catalog.assets["one.speaker.v1"]["approvals"][
            "hardware_acceptance"
        ] = "pending"
        self.catalog.assets["two.speaker.v1"]["approvals"][
            "hardware_acceptance"
        ] = "pending"
        with self.assertRaisesRegex(CatAudioDenied, "no approved"):
            self.catalog.select("meow_general", "speaker", now=10)
        for asset in self.catalog.assets.values():
            asset["approvals"]["hardware_acceptance"] = "accepted"
            (self.root / asset["repo_path"]).write_bytes(b"modified")
        with self.assertRaisesRegex(CatAudioDenied, "failed integrity"):
            self.catalog.select("meow_general", "speaker", now=10)

    def test_attended_bench_mode_requires_named_test_policy(self) -> None:
        manifest_path = self.root / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for asset in manifest["entries"]:
            asset["approvals"] = {
                "derived_content_review": "pending",
                "hardware_acceptance": "pending",
                "release_status": "bench_candidate",
            }
        manifest_path.write_text(json.dumps(manifest))
        allowlist_path = self.root / "allowlist.json"
        allowlist = json.loads(allowlist_path.read_text())
        allowlist["attended_test_only"] = True
        allowlist_path.write_text(json.dumps(allowlist))
        self.catalog = CatSoundCatalog(
            manifest_path,
            allowlist_path,
            repo_root=self.root,
            attended_bench_test=True,
        )
        selected = self.catalog.select("meow_general", "speaker", now=10)
        self.assertIn(selected.asset_id, {"one.speaker.v1", "two.speaker.v1"})


class CatSoundPlayerTests(unittest.TestCase):
    @patch("neko.cat_audio.subprocess.Popen")
    def test_player_uses_fixed_gain_and_target(self, popen: object) -> None:
        class Process:
            returncode = 0

            def poll(self) -> int:
                return 0

        popen.return_value = Process()
        selection = type(
            "Selection",
            (),
            {
                "gain_db": -6.0,
                "output": "speaker",
                "path": Path("/tmp/approved.wav"),
            },
        )()
        started: list[bool] = []
        completed = CatSoundPlayer({"speaker": "bluez-output"}).play(
            selection,
            cancel_event=threading.Event(),
            on_started=lambda: started.append(True),
        )
        self.assertTrue(completed)
        self.assertEqual(started, [True])
        command = popen.call_args.args[0]
        self.assertIn("0.501187", command)
        self.assertIn("bluez-output", command)


if __name__ == "__main__":
    unittest.main()
