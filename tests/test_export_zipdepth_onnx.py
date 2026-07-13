"""Focused tests for the ZipDepth exporter's integrity and pure logic.

These tests do not import PyTorch, ONNX, or ZipDepth and do not execute model
code.  A full export/parity test belongs in the pinned export environment.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "export_zipdepth_onnx.py"
SPEC = importlib.util.spec_from_file_location("export_zipdepth_onnx", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
EXPORTER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXPORTER
SPEC.loader.exec_module(EXPORTER)


class IntegrityTests(unittest.TestCase):
    def test_sha256_file_and_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.bin"
            payload = b"neko faithful export\n"
            path.write_bytes(payload)
            expected = hashlib.sha256(payload).hexdigest()
            self.assertEqual(EXPORTER.sha256_file(path), expected)
            self.assertEqual(
                EXPORTER.verify_file_sha256(path, expected, "test artifact"),
                expected,
            )
            with self.assertRaisesRegex(EXPORTER.ExportError, "SHA-256 mismatch"):
                EXPORTER.verify_file_sha256(path, "0" * 64, "test artifact")

    def test_state_keys_fail_closed(self) -> None:
        missing, unexpected = EXPORTER.state_key_diff(
            ["encoder.weight", "decoder.weight"],
            ["encoder.weight", "surprise.weight"],
        )
        self.assertEqual(missing, ["decoder.weight"])
        self.assertEqual(unexpected, ["surprise.weight"])
        with self.assertRaisesRegex(
            EXPORTER.ExportError, "missing.*decoder.weight.*unexpected.*surprise.weight"
        ):
            EXPORTER.require_exact_state_keys(
                ["encoder.weight", "decoder.weight"],
                ["encoder.weight", "surprise.weight"],
            )
        EXPORTER.require_exact_state_keys(["a", "b"], ["b", "a"])

    def test_export_dependency_versions_are_exact(self) -> None:
        matching = EXPORTER.RuntimeModules(
            torch=SimpleNamespace(__version__="2.12.1+cpu"),
            onnx=SimpleNamespace(__version__="1.18.0"),
            numpy=SimpleNamespace(__version__="1.26.2"),
            create_model=None,
            fuse_remaining_conv_bn=None,
            strip_state_dict_prefixes=None,
        )
        EXPORTER.verify_runtime_versions(matching)
        drifted = EXPORTER.RuntimeModules(
            torch=SimpleNamespace(__version__="2.13.0+cpu"),
            onnx=matching.onnx,
            numpy=matching.numpy,
            create_model=None,
            fuse_remaining_conv_bn=None,
            strip_state_dict_prefixes=None,
        )
        with self.assertRaisesRegex(
            EXPORTER.ExportError, "torch: expected 2.12.1\\+cpu, got 2.13.0\\+cpu"
        ):
            EXPORTER.verify_runtime_versions(drifted)

    def test_exact_clean_git_commit_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            tracked = root / "tracked.txt"
            tracked.write_text("pinned\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "-c",
                    "user.name=Neko Test",
                    "-c",
                    "user.email=neko-test@example.invalid",
                    "commit",
                    "-q",
                    "-m",
                    "pinned",
                ],
                check=True,
            )
            commit = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()

            verified = EXPORTER.verify_source_checkout(root, commit)
            self.assertEqual(verified.commit, commit)
            with self.assertRaisesRegex(EXPORTER.ExportError, "commit mismatch"):
                EXPORTER.verify_source_checkout(root, "f" * 40)

            tracked.write_text("modified\n", encoding="utf-8")
            with self.assertRaisesRegex(EXPORTER.ExportError, "tracked changes"):
                EXPORTER.verify_source_checkout(root, commit)


class GeometryAndPathTests(unittest.TestCase):
    def test_static_geometry_requires_multiples_of_32(self) -> None:
        EXPORTER.validate_dimensions(384, 672)
        EXPORTER.validate_dimensions(384, 384)
        for height, width in ((0, 672), (383, 672), (384, 681)):
            with self.subTest(height=height, width=width):
                with self.assertRaises(EXPORTER.ExportError):
                    EXPORTER.validate_dimensions(height, width)

    def test_cli_defaults_are_audited_static_profile(self) -> None:
        args = EXPORTER.build_parser().parse_args([])
        self.assertEqual(args.height, 384)
        self.assertEqual(args.width, 672)
        self.assertEqual(args.seed, 20_260_713)
        self.assertIsNone(args.output)
        self.assertIsNone(args.manifest)
        self.assertFalse(args.force)

    def test_default_artifacts_are_outside_source_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commit"
            source.mkdir()
            args = argparse.Namespace(
                source_root=source,
                checkpoint=None,
                output=None,
                manifest=None,
                height=384,
                width=672,
                force=False,
            )
            paths = EXPORTER.resolve_artifact_paths(args)
            self.assertEqual(
                paths.checkpoint, source / "checkpoints" / "zipdepth_base.pth"
            )
            self.assertEqual(paths.output.parent, source.parent / "engines")
            self.assertEqual(paths.output.suffix, ".onnx")
            self.assertEqual(paths.manifest.suffix, ".json")

    def test_output_inside_pinned_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commit"
            source.mkdir()
            args = argparse.Namespace(
                source_root=source,
                checkpoint=None,
                output=source / "generated.onnx",
                manifest=None,
                height=384,
                width=672,
                force=False,
            )
            with self.assertRaisesRegex(EXPORTER.ExportError, "outside"):
                EXPORTER.resolve_artifact_paths(args)


class GraphAuditTests(unittest.TestCase):
    def test_operator_histogram_is_domain_qualified_and_sorted(self) -> None:
        nodes = [
            SimpleNamespace(domain="", op_type="Conv"),
            SimpleNamespace(domain="", op_type="Relu"),
            SimpleNamespace(domain="", op_type="Conv"),
            SimpleNamespace(domain="example.custom", op_type="Mystery"),
        ]
        self.assertEqual(
            EXPORTER.count_onnx_operators(nodes),
            {
                "ai.onnx::Conv": 2,
                "ai.onnx::Relu": 1,
                "example.custom::Mystery": 1,
            },
        )

    def test_global_context_must_keep_learned_weight_and_class_forward(self) -> None:
        faithful_context = type(
            "GlobalContextBlock", (), {"context_weight": object(), "forward": lambda self: None}
        )()
        faithful_model = SimpleNamespace(modules=lambda: [faithful_context])
        self.assertEqual(
            EXPORTER.require_faithful_global_context(faithful_model), 1
        )

        patched_context = type(
            "GlobalContextBlock", (), {"context_weight": object(), "forward": lambda self: None}
        )()
        patched_context.forward = lambda: None
        patched_model = SimpleNamespace(modules=lambda: [patched_context])
        with self.assertRaisesRegex(EXPORTER.ExportError, "instance-patched"):
            EXPORTER.require_faithful_global_context(patched_model)

    def test_export_is_explicitly_legacy_and_has_no_onnxsim(self) -> None:
        source = inspect.getsource(EXPORTER.export_static_onnx)
        self.assertIn("dynamo=False", source)
        self.assertIn("opset_version=ONNX_OPSET", source)
        self.assertNotIn("onnxsim", source.lower())
        self.assertEqual(EXPORTER.ONNX_OPSET, 17)


if __name__ == "__main__":
    unittest.main()
