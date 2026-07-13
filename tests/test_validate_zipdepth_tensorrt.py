"""Pure-logic tests for the ZipDepth TensorRT numerical validator.

These tests never import TensorRT, load libcudart, deserialize a plan, import
ZipDepth, or execute a model.  NumPy-dependent metric tests run in the pinned
ZipDepth export environment and skip cleanly under a bare system Python.
"""

from __future__ import annotations

from enum import Enum
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "validate_zipdepth_tensorrt.py"
SPEC = importlib.util.spec_from_file_location("validate_zipdepth_tensorrt", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

try:
    import numpy as NUMPY
except ModuleNotFoundError:
    NUMPY = None


class IntegrityTests(unittest.TestCase):
    def test_sha256_verification_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.bin"
            payload = b"pinned TensorRT plan\n"
            path.write_bytes(payload)
            expected = hashlib.sha256(payload).hexdigest()
            self.assertEqual(VALIDATOR.verify_sha256(path, expected, "test"), expected)
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "SHA-256 mismatch"):
                VALIDATOR.verify_sha256(path, "0" * 64, "test")

    def test_sha256_text_is_exact(self) -> None:
        self.assertEqual(VALIDATOR.require_sha256_text("A" * 64, "hash"), "a" * 64)
        for value in ("a" * 63, "a" * 65, "g" * 64):
            with self.subTest(value=value):
                with self.assertRaises(VALIDATOR.ValidationError):
                    VALIDATOR.require_sha256_text(value, "hash")

    def test_manifest_value_checks_nested_identity(self) -> None:
        manifest = {"model": {"variant": "base"}}
        VALIDATOR.require_manifest_value(manifest, "model.variant", "base")
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "mismatch"):
            VALIDATOR.require_manifest_value(manifest, "model.variant", "large")
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "missing"):
            VALIDATOR.require_manifest_value(manifest, "model.width", 672)

    def test_cli_defaults_pin_both_current_plans(self) -> None:
        args = VALIDATOR.build_parser().parse_args([])
        self.assertEqual(args.fp32_plan, VALIDATOR.DEFAULT_FP32_PLAN)
        self.assertEqual(args.fp16_plan, VALIDATOR.DEFAULT_FP16_PLAN)
        self.assertEqual(args.fp32_plan_sha256, VALIDATOR.EXPECTED_FP32_PLAN_SHA256)
        self.assertEqual(args.fp16_plan_sha256, VALIDATOR.EXPECTED_FP16_PLAN_SHA256)
        self.assertEqual(args.device, 0)
        self.assertFalse(args.force)

    def test_atomic_json_rejects_nan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            VALIDATOR.atomic_write_json(path, {"status": "passed", "value": 1.0})
            self.assertEqual(json.loads(path.read_text())["status"], "passed")
            with self.assertRaises(ValueError):
                VALIDATOR.atomic_write_json(path, {"value": float("nan")})


@unittest.skipIf(NUMPY is None, "NumPy is only present in the export environment")
class NumericalLogicTests(unittest.TestCase):
    def test_average_ranks_handles_ties(self) -> None:
        values = NUMPY.array([30.0, 10.0, 20.0, 20.0])
        ranks = VALIDATOR.average_ranks(NUMPY, values)
        NUMPY.testing.assert_allclose(ranks, [4.0, 1.0, 2.5, 2.5])

    def test_spearman_handles_identity_and_reverse(self) -> None:
        values = NUMPY.array([0.1, 0.4, 0.2, 0.3])
        self.assertAlmostEqual(
            VALIDATOR.spearman_correlation(NUMPY, values, values), 1.0
        )
        self.assertAlmostEqual(
            VALIDATOR.spearman_correlation(NUMPY, values, -values), -1.0
        )

    def test_comparison_metrics_and_gates(self) -> None:
        expected = NUMPY.array([0.01, 0.02, 0.03, 0.04], dtype=NUMPY.float32)
        identical = VALIDATOR.comparison_metrics(
            NUMPY, expected, expected.copy(), relative_floor=1.0e-6
        )
        self.assertEqual(identical["mae"], 0.0)
        self.assertEqual(identical["max_abs"], 0.0)
        self.assertAlmostEqual(identical["cosine_similarity"], 1.0)
        self.assertEqual(
            VALIDATOR.numerical_gate_failures(
                identical, VALIDATOR.DEFAULT_FP32_THRESHOLDS
            ),
            [],
        )
        broken = dict(identical)
        broken["max_abs"] = 1.0
        failures = VALIDATOR.numerical_gate_failures(
            broken, VALIDATOR.DEFAULT_FP32_THRESHOLDS
        )
        self.assertTrue(any("max_abs" in item for item in failures))

    def test_affine_alignment_recovers_scale_and_shift(self) -> None:
        expected = NUMPY.array([1.0, 2.0, 4.0, 8.0])
        actual = (expected - 0.25) / 2.0
        metrics = VALIDATOR.affine_alignment_metrics(NUMPY, expected, actual)
        self.assertAlmostEqual(metrics["actual_to_expected_scale"], 2.0)
        self.assertAlmostEqual(metrics["actual_to_expected_shift"], 0.25)
        self.assertLess(metrics["max_abs"], 1.0e-12)

    def test_depth_validation_rejects_shape_nan_and_negative(self) -> None:
        valid = NUMPY.ones(VALIDATOR.EXPECTED_OUTPUT_SHAPE, dtype=NUMPY.float32)
        VALIDATOR.require_depth_array(
            NUMPY, valid, VALIDATOR.EXPECTED_OUTPUT_SHAPE, "valid"
        )
        for candidate in (
            NUMPY.ones((1, 1, 1, 1), dtype=NUMPY.float32),
            NUMPY.full(VALIDATOR.EXPECTED_OUTPUT_SHAPE, NUMPY.nan, dtype=NUMPY.float32),
            NUMPY.full(VALIDATOR.EXPECTED_OUTPUT_SHAPE, -0.1, dtype=NUMPY.float32),
        ):
            with self.subTest(shape=candidate.shape):
                with self.assertRaises(VALIDATOR.ValidationError):
                    VALIDATOR.require_depth_array(
                        NUMPY,
                        candidate,
                        VALIDATOR.EXPECTED_OUTPUT_SHAPE,
                        "invalid",
                    )


class Mode(Enum):
    INPUT = 0
    OUTPUT = 1


class Location(Enum):
    DEVICE = 0
    HOST = 1


class Format(Enum):
    LINEAR = 0
    CHW4 = 1


class FakeEngine:
    num_io_tensors = 2
    num_optimization_profiles = 1

    def __init__(
        self,
        tensor_format: Format = Format.LINEAR,
        component_metadata: tuple[int, int] = (-1, -1),
    ) -> None:
        self.tensor_format = tensor_format
        self.component_metadata = component_metadata

    def get_tensor_name(self, index: int) -> str:
        return ("image", "depth")[index]

    def get_tensor_mode(self, name: str) -> Mode:
        return Mode.INPUT if name == "image" else Mode.OUTPUT

    def get_tensor_shape(self, name: str) -> tuple[int, ...]:
        return (
            VALIDATOR.EXPECTED_INPUT_SHAPE
            if name == "image"
            else VALIDATOR.EXPECTED_OUTPUT_SHAPE
        )

    def is_shape_inference_io(self, name: str) -> bool:
        return False

    def get_tensor_location(self, name: str) -> Location:
        return Location.DEVICE

    def get_tensor_format(self, name: str) -> Format:
        return self.tensor_format

    def get_tensor_vectorized_dim(self, name: str) -> int:
        return -1

    def get_tensor_components_per_element(self, name: str) -> int:
        return self.component_metadata[0]

    def get_tensor_bytes_per_component(self, name: str) -> int:
        return self.component_metadata[1]

    def get_tensor_dtype(self, name: str) -> str:
        return "float32"

    def get_tensor_format_desc(self, name: str) -> str:
        return "Row major linear FP32"


class FakeContext:
    def get_tensor_shape(self, name: str) -> tuple[int, ...]:
        return (
            VALIDATOR.EXPECTED_INPUT_SHAPE
            if name == "image"
            else VALIDATOR.EXPECTED_OUTPUT_SHAPE
        )

    def get_tensor_strides(self, name: str) -> tuple[int, ...]:
        return VALIDATOR._contiguous_strides(self.get_tensor_shape(name))


@unittest.skipIf(NUMPY is None, "NumPy is only present in the export environment")
class EngineInspectionLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.trt = SimpleNamespace(
            TensorIOMode=Mode,
            TensorLocation=Location,
            TensorFormat=Format,
            nptype=lambda value: NUMPY.float32,
        )

    def test_exact_static_linear_io_passes(self) -> None:
        image, depth, image_dtype, depth_dtype = VALIDATOR.inspect_static_engine_io(
            self.trt, NUMPY, FakeEngine(), FakeContext()
        )
        self.assertEqual(image.shape, VALIDATOR.EXPECTED_INPUT_SHAPE)
        self.assertEqual(depth.shape, VALIDATOR.EXPECTED_OUTPUT_SHAPE)
        self.assertEqual(str(image_dtype), "float32")
        self.assertEqual(str(depth_dtype), "float32")
        self.assertEqual(image.components_per_element, -1)
        self.assertEqual(image.bytes_per_component, -1)
        self.assertEqual(image.effective_element_size_bytes, 4)

    def test_explicit_scalar_component_metadata_also_passes(self) -> None:
        image, _, _, _ = VALIDATOR.inspect_static_engine_io(
            self.trt,
            NUMPY,
            FakeEngine(component_metadata=(1, 4)),
            FakeContext(),
        )
        self.assertEqual(image.components_per_element, 1)
        self.assertEqual(image.effective_element_size_bytes, 4)

    def test_mixed_or_unexpected_component_metadata_fails_closed(self) -> None:
        for metadata in ((-1, 4), (1, -1), (2, 4), (-2, -2)):
            with self.subTest(metadata=metadata):
                with self.assertRaisesRegex(
                    VALIDATOR.ValidationError, "unexpected component metadata"
                ):
                    VALIDATOR.inspect_static_engine_io(
                        self.trt,
                        NUMPY,
                        FakeEngine(component_metadata=metadata),
                        FakeContext(),
                    )

    def test_vectorized_format_fails_closed(self) -> None:
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "not LINEAR"):
            VALIDATOR.inspect_static_engine_io(
                self.trt, NUMPY, FakeEngine(Format.CHW4), FakeContext()
            )

    def test_engine_metadata_does_not_probe_unsupported_weight_budget(self) -> None:
        class MetadataEngine:
            name = "zipdepth"
            num_layers = 41
            num_io_tensors = 2
            num_optimization_profiles = 1
            device_memory_size_v2 = 1024
            num_aux_streams = 0
            streamable_weights_size = 0

            @property
            def weight_streaming_budget_v2(self) -> int:
                raise AssertionError("unsupported TensorRT property was probed")

        metadata = VALIDATOR._engine_metadata(MetadataEngine())
        self.assertEqual(metadata["streamable_weights_size"], 0)
        self.assertNotIn("weight_streaming_budget_v2", metadata)


class StaticImplementationTests(unittest.TestCase):
    def test_validator_uses_required_low_level_path(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("execute_async_v3", source)
        self.assertIn("set_tensor_address", source)
        self.assertIn("ctypes.CDLL", source)
        self.assertIn("cudaMallocHost", source)
        self.assertIn("engine_host_code_allowed", source)
        self.assertNotIn("import pycuda", source.lower())
        self.assertNotIn("from cuda", source.lower())
        self.assertNotIn("import scipy", source.lower())

    def test_tensorrt_import_is_lazy(self) -> None:
        source = inspect.getsource(VALIDATOR.load_tensorrt)
        self.assertIn('importlib.import_module("tensorrt")', source)
        self.assertNotIn("execute_async_v3", source)

    def test_metadata_omits_weight_streaming_budget_probe(self) -> None:
        source = inspect.getsource(VALIDATOR._engine_metadata)
        self.assertNotIn('"weight_streaming_budget_v2"', source)


if __name__ == "__main__":
    unittest.main()
