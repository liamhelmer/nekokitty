from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = REPO_ROOT / "config/cat-sounds/curated-freesound.json"
REVIEW_LEDGER = REPO_ROOT / "config/cat-sounds/curated-freesound-listening-review.json"
ASSET_MANIFEST = REPO_ROOT / "assets/cat-sounds/manifest.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class CatSoundAssetTests(unittest.TestCase):
    def test_assets_exactly_match_keep_decisions_and_source_metadata(self) -> None:
        sources = load_json(SOURCE_MANIFEST)
        review = load_json(REVIEW_LEDGER)
        assets = load_json(ASSET_MANIFEST)

        source_by_id = {entry["id"]: entry for entry in sources["entries"]}
        selected_ids = [
            entry["id"]
            for entry in review["entries"]
            if entry["decision"].startswith("keep_")
        ]
        asset_ids = [entry["id"] for entry in assets["entries"]]
        self.assertEqual(asset_ids, selected_ids)
        self.assertEqual(assets["asset_count"], 20)

        for entry in assets["entries"]:
            source = source_by_id[entry["id"]]
            for field in (
                "filename",
                "sha256",
                "source_url",
                "creator",
                "title",
                "license",
                "license_url",
            ):
                self.assertEqual(entry[field], source[field], (entry["id"], field))

    def test_files_hash_bytes_and_licence_totals(self) -> None:
        assets = load_json(ASSET_MANIFEST)
        expected_paths = {REPO_ROOT / entry["repo_path"] for entry in assets["entries"]}
        actual_paths = {
            path
            for path in (REPO_ROOT / assets["asset_root"]).iterdir()
            if path.is_file()
        }
        self.assertEqual(actual_paths, expected_paths)

        content_bytes = 0
        for entry in assets["entries"]:
            path = REPO_ROOT / entry["repo_path"]
            content_bytes += path.stat().st_size
            self.assertEqual(sha256_file(path), entry["sha256"], entry["id"])

        self.assertEqual(content_bytes, assets["content_bytes"])
        self.assertEqual(content_bytes, 74_496_458)
        self.assertEqual(
            Counter(entry["license"] for entry in assets["entries"]),
            Counter(
                {
                    "CC0-1.0": 11,
                    "CC-BY-4.0": 3,
                    "CC-BY-NC-3.0": 2,
                    "CC-BY-NC-4.0": 4,
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
