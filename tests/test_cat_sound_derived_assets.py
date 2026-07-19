from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import unittest
import wave


REPO_ROOT = Path(__file__).resolve().parents[1]
DERIVED_MANIFEST = REPO_ROOT / "assets/cat-sounds/derived/manifest.json"
SOURCE_MANIFEST = REPO_ROOT / "config/cat-sounds/curated-freesound.json"
RECIPES = REPO_ROOT / "config/cat-sounds/derived-assets-recipes.json"
ALLOWLIST = REPO_ROOT / "config/cat-sounds/runtime-allowlist.json"
ATTRIBUTION = REPO_ROOT / "assets/cat-sounds/ATTRIBUTION.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class DerivedCatSoundAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_json(DERIVED_MANIFEST)
        cls.sources = load_json(SOURCE_MANIFEST)
        cls.recipes = load_json(RECIPES)
        cls.allowlist = load_json(ALLOWLIST)
        cls.attribution = ATTRIBUTION.read_text(encoding="utf-8")

    def test_manifest_and_recipe_identity_are_complete(self) -> None:
        entries = self.manifest["entries"]
        recipes = self.recipes["entries"]
        self.assertEqual(self.manifest["asset_count"], 25)
        self.assertEqual(len(entries), 25)
        self.assertEqual(
            [entry["asset_id"] for entry in entries],
            [entry["asset_id"] for entry in recipes],
        )
        self.assertEqual(len({entry["asset_id"] for entry in entries}), len(entries))
        self.assertEqual(len({entry["repo_path"] for entry in entries}), len(entries))
        self.assertEqual(len({entry["sha256"] for entry in entries}), len(entries))
        self.assertFalse(self.manifest["root_mit_license_applies"])
        self.assertEqual(self.manifest["runtime_default"], "disabled")

    def test_files_hash_media_and_mastering_contract(self) -> None:
        policy = self.manifest["mastering_policy"]
        expected_paths = {
            REPO_ROOT / entry["repo_path"] for entry in self.manifest["entries"]
        }
        actual_paths = set((REPO_ROOT / self.manifest["asset_root"]).glob("*.wav"))
        self.assertEqual(actual_paths, expected_paths)
        self.assertEqual(
            self.manifest["content_bytes"],
            sum(path.stat().st_size for path in expected_paths),
        )

        for entry in self.manifest["entries"]:
            path = REPO_ROOT / entry["repo_path"]
            self.assertEqual(sha256_file(path), entry["sha256"], entry["asset_id"])
            self.assertEqual(path.stat().st_size, entry["byte_size"])
            with wave.open(str(path), "rb") as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getframerate(), 48000)
                self.assertEqual(handle.getsampwidth(), 3)
                self.assertEqual(handle.getnframes(), entry["sample_frames"])
            self.assertAlmostEqual(
                entry["sample_frames"] / 48000,
                entry["duration_seconds"],
                places=5,
            )
            measured = entry["measured_mastering"]
            self.assertEqual(entry["recipe_id"], entry["asset_id"])
            for operation in entry["processing"]:
                self.assertEqual(operation["tool"], "ffmpeg")
                self.assertTrue(operation["tool_version"])
            for field in ("integrated_lufs", "loudness_range_lu", "true_peak_dbtp"):
                self.assertTrue(math.isfinite(measured[field]), (entry["asset_id"], field))
            self.assertLessEqual(
                measured["true_peak_dbtp"],
                policy["max_true_peak_dbtp"] + 0.01,
                entry["asset_id"],
            )
            self.assertEqual(entry["clipped_sample_count"], 0, entry["asset_id"])
            if measured["target_reached"]:
                self.assertIsNone(measured["target_miss_reason"])
                self.assertLessEqual(
                    abs(measured["integrated_lufs"] - policy["target_lufs_i"]),
                    policy["loudness_tolerance_lu"],
                )
            else:
                self.assertEqual(
                    measured["target_miss_reason"],
                    "true_peak_limited_without_destructive_dynamics_processing",
                )
                gain = next(
                    operation["parameters"]
                    for operation in entry["processing"]
                    if operation["operation"] == "linear_gain"
                )
                self.assertTrue(gain["peak_limited"])

    def test_provenance_rights_and_attribution_cover_every_derivative(self) -> None:
        source_by_id = {entry["id"]: entry for entry in self.sources["entries"]}
        licenses = Counter()
        for entry in self.manifest["entries"]:
            source = entry["sources"][0]
            canonical = source_by_id[source["source_id"]]
            self.assertEqual(source["source_sha256"], canonical["sha256"])
            self.assertLess(source["start_seconds"], source["end_seconds"])
            self.assertLessEqual(
                source["end_seconds"], source["source_duration_seconds_probed"] + 1e-6
            )
            rights = entry["rights"]
            for field in (
                "license",
                "license_url",
                "creator",
                "title",
                "source_url",
                "attribution_text",
                "changes_notice",
            ):
                self.assertTrue(rights[field], (entry["asset_id"], field))
            self.assertFalse(rights["root_mit_license_applies"])
            if "-NC-" in rights["license"]:
                self.assertFalse(rights["commercial_use_allowed"])
            self.assertIn(Path(entry["repo_path"]).name, self.attribution)
            licenses[rights["license"]] += 1
        self.assertEqual(
            licenses,
            Counter({"CC0-1.0": 10, "CC-BY-4.0": 14, "CC-BY-NC-3.0": 1}),
        )

    def test_loop_metadata_is_bounded_and_unapproved(self) -> None:
        loops = [entry for entry in self.manifest["entries"] if entry["variant"] == "loop"]
        self.assertEqual(len(loops), 2)
        for entry in loops:
            loop = entry["loop"]
            self.assertEqual(loop["loop_start_frame"], 0)
            self.assertEqual(loop["loop_end_frame"], entry["sample_frames"])
            self.assertGreater(loop["crossfade_frames"], 0)
            self.assertLess(loop["crossfade_frames"], entry["sample_frames"])
            self.assertEqual(loop["listening_approval"], "pending")
            self.assertLess(entry["loop_boundary_amplitude_delta"], 0.001)
            self.assertLess(entry["loop_boundary_slope_delta"], 0.001)

    def test_runtime_allowlist_fails_closed(self) -> None:
        self.assertEqual(self.allowlist["default_policy"], "deny")
        contract = self.allowlist["supervisor_contract"]
        self.assertTrue(contract["accept_semantic_actions_only"])
        self.assertTrue(contract["raw_paths_denied"])
        self.assertFalse(contract["llm_may_choose_path_gain_or_output"])
        manifest_by_id = {
            entry["asset_id"]: entry for entry in self.manifest["entries"]
        }
        referenced: set[str] = set()
        for action_name, action in self.allowlist["actions"].items():
            self.assertFalse(action["enabled"], action_name)
            self.assertFalse(action["autonomous_allowed"], action_name)
            self.assertGreater(action["cooldown_seconds"], 0)
            self.assertGreater(action["max_duration_seconds"], 0)
            self.assertLessEqual(action["min_gain_db"], action["max_gain_db"])
            self.assertLessEqual(action["max_gain_db"], 0)
            self.assertGreaterEqual(action["default_gain_db"], action["min_gain_db"])
            self.assertLessEqual(action["default_gain_db"], action["max_gain_db"])
            for candidate in action["candidates"]:
                asset_id = candidate["asset_id"]
                entry = manifest_by_id[asset_id]
                self.assertIn(entry["target_output"], action["allowed_outputs"])
                self.assertEqual(entry["approvals"]["hardware_acceptance"], "pending")
                referenced.add(asset_id)
        self.assertEqual(referenced, set(manifest_by_id))
        serialized = ALLOWLIST.read_text(encoding="utf-8")
        self.assertNotIn("freesound-428552", serialized)
        self.assertNotIn(".wav", serialized)


if __name__ == "__main__":
    unittest.main()
