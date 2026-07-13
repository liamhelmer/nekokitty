#!/usr/bin/env python3
"""Numerically validate the two pinned ZipDepth TensorRT plans.

Run this with the ZipDepth export virtual environment so its audited CPU
PyTorch and NumPy are used.  TensorRT is imported explicitly from Ubuntu's
system dist-packages, and CUDA memory/stream operations use only ``ctypes``
against the pinned ``libcudart``.  No CUDA Python, PyCUDA, SciPy, or model
runtime package is required.

This is a one-shot acceptance validator, not the production camera loop.  It
reconstructs the same deterministic fused PyTorch reference as the audited
ONNX exporter, checks every artifact and runtime identity before engine
deserialization, executes the FP32 and FP16 plans sequentially, applies strict
numerical gates, and publishes an atomic JSON manifest only after every gate
passes.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import ctypes
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import gc
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import shlex
import sys
import tempfile
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORTER_PATH = PROJECT_ROOT / "scripts" / "export_zipdepth_onnx.py"
ENGINE_ROOT = Path("/home/neko/models/ZipDepth/engines")
DEFAULT_EXPORT_MANIFEST = ENGINE_ROOT / "zipdepth_base_b1_384x672_op17.manifest.json"
DEFAULT_ONNX = ENGINE_ROOT / "zipdepth_base_b1_384x672_op17.onnx"
DEFAULT_FP32_PLAN = (
    ENGINE_ROOT / "zipdepth_base_trt10.16.2_sm87_b1_384x672_fp32.plan"
)
DEFAULT_FP16_PLAN = (
    ENGINE_ROOT / "zipdepth_base_trt10.16.2_sm87_b1_384x672_fp16.plan"
)
DEFAULT_OUTPUT = ENGINE_ROOT / "zipdepth_base_trt10.16.2_sm87_b1_384x672.validation.json"
DEFAULT_TENSORRT_DIST_PACKAGES = Path("/usr/lib/python3.12/dist-packages")
DEFAULT_CUDART = Path("/usr/local/cuda/targets/sbsa-linux/lib/libcudart.so.13")

EXPECTED_EXPORT_MANIFEST_SHA256 = (
    "343920624f72a518d2d0dc2d3eed1c505128e48620284540555a321e9a135655"
)
EXPECTED_EXPORTER_SHA256 = (
    "21030c6a9a2e8882ef899370e94d3c868fbc9af5b141cacb8b7317d55409e18b"
)
EXPECTED_ONNX_SHA256 = (
    "38a9cc74be691be98190fd460ac1bba2986c5a7c16e3f33f5404463d74d2cbd0"
)
EXPECTED_FP32_PLAN_SHA256 = (
    "c4c3e7fd67b8e9204e24d2981aab21d635266ead121a5fa203a074d5a72012ba"
)
EXPECTED_FP16_PLAN_SHA256 = (
    "13ed532b2ce2fa3cbcf6ad4cfb1dcb9e2c1498705477a328171dc750da1a4b78"
)
EXPECTED_TENSORRT_BINDING_SHA256 = (
    "dabdbe9dbdd9f91af55693d3840c040ea59f50c39c2ca3862eee01eb23b45219"
)
EXPECTED_CUDART_SHA256 = (
    "2537479bafd2d6f3066a21fb54a2d05cd044bb0bf3705ea51ac3f0ccb0c02665"
)
EXPECTED_TENSORRT_VERSION = "10.16.2.10"
EXPECTED_CUDA_RUNTIME_VERSION = 13_020
EXPECTED_COMPUTE_CAPABILITY = (8, 7)
EXPECTED_EXPORT_SCHEMA = "neko.zipdepth-onnx-export/v1"
VALIDATION_SCHEMA = "neko.zipdepth-tensorrt-validation/v1"
EXPECTED_INPUT_NAME = "image"
EXPECTED_OUTPUT_NAME = "depth"
EXPECTED_INPUT_SHAPE = (1, 3, 384, 672)
EXPECTED_OUTPUT_SHAPE = (1, 1, 384, 672)
EXPECTED_IO_DTYPE = "float32"
HASH_CHUNK_SIZE = 1024 * 1024

CUDA_MEMCPY_HOST_TO_DEVICE = 1
CUDA_MEMCPY_DEVICE_TO_HOST = 2
CUDA_STREAM_NON_BLOCKING = 1
CUDA_DEV_ATTR_COMPUTE_CAPABILITY_MAJOR = 75
CUDA_DEV_ATTR_COMPUTE_CAPABILITY_MINOR = 76


class ValidationError(RuntimeError):
    """An artifact, runtime, execution, cleanup, or numerical gate failed."""


@dataclass(frozen=True)
class NumericalThresholds:
    """Fail-closed numerical gates for one comparison."""

    mae_max: float
    max_abs_max: float
    max_relative_max: float
    cosine_min: float
    spearman_min: float


DEFAULT_FP32_THRESHOLDS = NumericalThresholds(
    mae_max=1.0e-5,
    max_abs_max=1.0e-4,
    max_relative_max=1.0e-3,
    cosine_min=0.999_999,
    spearman_min=0.999_9,
)
DEFAULT_FP16_THRESHOLDS = NumericalThresholds(
    mae_max=2.5e-4,
    max_abs_max=2.0e-3,
    max_relative_max=5.0e-2,
    cosine_min=0.999,
    spearman_min=0.995,
)


@dataclass(frozen=True)
class ArtifactPaths:
    export_manifest: Path
    onnx: Path
    fp32_plan: Path
    fp16_plan: Path
    output: Path
    tensorrt_dist_packages: Path
    cudart: Path


@dataclass(frozen=True)
class TensorDescription:
    name: str
    mode: str
    shape: tuple[int, ...]
    dtype: str
    location: str
    format: str
    format_description: str
    vectorized_dimension: int
    components_per_element: int
    bytes_per_component: int
    effective_element_size_bytes: int
    strides: tuple[int, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise ValidationError(f"{label} is not a regular file: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ValidationError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual}: {path}"
        )
    return actual


def require_sha256_text(value: str, label: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise ValidationError(f"{label} must be exactly 64 hexadecimal characters")
    return normalized


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{label} must be a JSON object")
    return value


def _nested(mapping: Mapping[str, Any], path: str) -> Any:
    value: Any = mapping
    traversed: list[str] = []
    for component in path.split("."):
        traversed.append(component)
        if not isinstance(value, Mapping) or component not in value:
            raise ValidationError(
                f"export manifest is missing {'.'.join(traversed)!r}"
            )
        value = value[component]
    return value


def require_manifest_value(
    manifest: Mapping[str, Any], path: str, expected: Any
) -> None:
    actual = _nested(manifest, path)
    if actual != expected:
        raise ValidationError(
            f"export manifest {path!r} mismatch: expected {expected!r}, got {actual!r}"
        )


def load_verified_export_manifest(
    path: Path,
    *,
    expected_manifest_sha256: str,
    expected_exporter_sha256: str,
    expected_onnx_sha256: str,
) -> Mapping[str, Any]:
    verify_sha256(path, expected_manifest_sha256, "ZipDepth export manifest")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot read export manifest {path}: {error}") from error
    manifest = _mapping(payload, "export manifest")
    require_manifest_value(manifest, "schema", EXPECTED_EXPORT_SCHEMA)
    require_manifest_value(manifest, "exporter.sha256", expected_exporter_sha256)
    require_manifest_value(manifest, "onnx.sha256", expected_onnx_sha256)
    require_manifest_value(manifest, "model.variant", "base")
    require_manifest_value(manifest, "model.global_mode", "balanced")
    require_manifest_value(manifest, "model.upsample_unfold", True)
    require_manifest_value(manifest, "model.batch", 1)
    require_manifest_value(manifest, "model.height", EXPECTED_INPUT_SHAPE[2])
    require_manifest_value(manifest, "model.width", EXPECTED_INPUT_SHAPE[3])
    require_manifest_value(manifest, "onnx.input.name", EXPECTED_INPUT_NAME)
    require_manifest_value(manifest, "onnx.input.shape", list(EXPECTED_INPUT_SHAPE))
    require_manifest_value(manifest, "onnx.input.element_type", EXPECTED_IO_DTYPE)
    require_manifest_value(manifest, "onnx.output.name", EXPECTED_OUTPUT_NAME)
    require_manifest_value(manifest, "onnx.output.shape", list(EXPECTED_OUTPUT_SHAPE))
    require_manifest_value(manifest, "onnx.output.element_type", EXPECTED_IO_DTYPE)
    return manifest


def load_verified_exporter(path: Path, expected_sha256: str) -> Any:
    verify_sha256(path, expected_sha256, "audited ZipDepth exporter")
    spec = importlib.util.spec_from_file_location("neko_zipdepth_exporter", path)
    if spec is None or spec.loader is None:
        raise ValidationError(f"cannot construct import spec for exporter: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        sys.modules.pop(spec.name, None)
        raise ValidationError(f"cannot import audited exporter {path}: {error}") from error
    return module


def array_sha256(numpy: Any, array: Any) -> str:
    contiguous = numpy.ascontiguousarray(array)
    return hashlib.sha256(contiguous.tobytes(order="C")).hexdigest()


def require_depth_array(
    numpy: Any, array: Any, expected_shape: tuple[int, ...], label: str
) -> Any:
    candidate = numpy.asarray(array)
    if tuple(int(item) for item in candidate.shape) != expected_shape:
        raise ValidationError(
            f"{label} shape mismatch: expected {expected_shape}, got {candidate.shape}"
        )
    if candidate.dtype.kind != "f":
        raise ValidationError(f"{label} is not floating point: {candidate.dtype}")
    if not bool(numpy.isfinite(candidate).all()):
        raise ValidationError(f"{label} contains NaN or infinite values")
    minimum = float(candidate.min())
    if minimum < 0.0:
        raise ValidationError(f"{label} contains negative inverse depth: min={minimum}")
    return candidate


def array_summary(numpy: Any, array: Any) -> dict[str, Any]:
    candidate = numpy.ascontiguousarray(array)
    return {
        "shape": [int(item) for item in candidate.shape],
        "dtype": str(candidate.dtype),
        "finite": bool(numpy.isfinite(candidate).all()),
        "nonnegative": bool(float(candidate.min()) >= 0.0),
        "min": float(candidate.min()),
        "max": float(candidate.max()),
        "mean": float(candidate.mean(dtype=numpy.float64)),
        "std": float(candidate.astype(numpy.float64, copy=False).std()),
        "sha256": array_sha256(numpy, candidate),
    }


def average_ranks(numpy: Any, values: Any) -> Any:
    """Return one-based average ranks with stable, deterministic tie handling."""

    flat = numpy.asarray(values, dtype=numpy.float64).reshape(-1)
    if flat.size == 0:
        raise ValidationError("cannot rank an empty array")
    if not bool(numpy.isfinite(flat).all()):
        raise ValidationError("cannot rank non-finite values")
    order = numpy.argsort(flat, kind="mergesort")
    sorted_values = flat[order]
    boundaries = numpy.concatenate(
        (
            numpy.array([0], dtype=numpy.int64),
            numpy.nonzero(sorted_values[1:] != sorted_values[:-1])[0].astype(
                numpy.int64
            )
            + 1,
            numpy.array([flat.size], dtype=numpy.int64),
        )
    )
    ranks = numpy.empty(flat.size, dtype=numpy.float64)
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        # One-based ranks start+1 through stop have this average.
        ranks[order[int(start) : int(stop)]] = (float(start) + float(stop) + 1.0) / 2.0
    return ranks


def correlation(numpy: Any, left: Any, right: Any, label: str) -> float:
    left64 = numpy.asarray(left, dtype=numpy.float64).reshape(-1)
    right64 = numpy.asarray(right, dtype=numpy.float64).reshape(-1)
    if left64.shape != right64.shape or left64.size == 0:
        raise ValidationError(f"{label} requires equally sized non-empty arrays")
    left_centered = left64 - left64.mean()
    right_centered = right64 - right64.mean()
    denominator = math.sqrt(
        float(numpy.dot(left_centered, left_centered))
        * float(numpy.dot(right_centered, right_centered))
    )
    if denominator == 0.0:
        if bool(numpy.array_equal(left64, right64)):
            return 1.0
        raise ValidationError(f"{label} is undefined for a constant unequal array")
    value = float(numpy.dot(left_centered, right_centered) / denominator)
    return max(-1.0, min(1.0, value))


def spearman_correlation(numpy: Any, expected: Any, actual: Any) -> float:
    return correlation(
        numpy,
        average_ranks(numpy, expected),
        average_ranks(numpy, actual),
        "Spearman correlation",
    )


def affine_alignment_metrics(numpy: Any, expected: Any, actual: Any) -> dict[str, float]:
    expected64 = numpy.asarray(expected, dtype=numpy.float64).reshape(-1)
    actual64 = numpy.asarray(actual, dtype=numpy.float64).reshape(-1)
    actual_centered = actual64 - actual64.mean()
    variance = float(numpy.dot(actual_centered, actual_centered))
    if variance <= numpy.finfo(numpy.float64).tiny:
        raise ValidationError("cannot affine-align a constant actual output")
    expected_centered = expected64 - expected64.mean()
    scale = float(numpy.dot(actual_centered, expected_centered) / variance)
    shift = float(expected64.mean() - scale * actual64.mean())
    aligned_difference = scale * actual64 + shift - expected64
    absolute = numpy.abs(aligned_difference)
    return {
        "actual_to_expected_scale": scale,
        "actual_to_expected_shift": shift,
        "mae": float(absolute.mean()),
        "rmse": float(numpy.sqrt(numpy.mean(aligned_difference * aligned_difference))),
        "max_abs": float(absolute.max()),
    }


def comparison_metrics(
    numpy: Any,
    expected: Any,
    actual: Any,
    *,
    relative_floor: float,
) -> dict[str, Any]:
    expected64 = numpy.asarray(expected, dtype=numpy.float64).reshape(-1)
    actual64 = numpy.asarray(actual, dtype=numpy.float64).reshape(-1)
    if expected64.shape != actual64.shape or expected64.size == 0:
        raise ValidationError("comparison requires equally sized non-empty arrays")
    if not bool(numpy.isfinite(expected64).all()) or not bool(
        numpy.isfinite(actual64).all()
    ):
        raise ValidationError("comparison inputs must be finite")

    difference = actual64 - expected64
    absolute = numpy.abs(difference)
    relative_mask = numpy.abs(expected64) >= relative_floor
    if not bool(relative_mask.any()):
        raise ValidationError(
            f"no reference values meet relative-error floor {relative_floor}"
        )
    relative = absolute[relative_mask] / numpy.abs(expected64[relative_mask])
    expected_norm = float(numpy.linalg.norm(expected64))
    actual_norm = float(numpy.linalg.norm(actual64))
    if expected_norm == 0.0 or actual_norm == 0.0:
        raise ValidationError("cosine similarity is undefined for a zero-norm output")
    cosine = float(numpy.dot(expected64, actual64) / (expected_norm * actual_norm))
    cosine = max(-1.0, min(1.0, cosine))
    percentiles = numpy.percentile(absolute, [50.0, 95.0, 99.0, 99.9])
    return {
        "element_count": int(expected64.size),
        "bias": float(difference.mean()),
        "mae": float(absolute.mean()),
        "rmse": float(numpy.sqrt(numpy.mean(difference * difference))),
        "max_abs": float(absolute.max()),
        "abs_error_percentiles": {
            "p50": float(percentiles[0]),
            "p95": float(percentiles[1]),
            "p99": float(percentiles[2]),
            "p99_9": float(percentiles[3]),
        },
        "relative_error_floor": relative_floor,
        "relative_element_count": int(relative.size),
        "mean_relative_away_from_zero": float(relative.mean()),
        "max_relative_away_from_zero": float(relative.max()),
        "cosine_similarity": cosine,
        "pearson_correlation": correlation(
            numpy, expected64, actual64, "Pearson correlation"
        ),
        "spearman_rank_correlation": spearman_correlation(
            numpy, expected64, actual64
        ),
        "affine_aligned": affine_alignment_metrics(numpy, expected64, actual64),
    }


def numerical_gate_failures(
    metrics: Mapping[str, Any], thresholds: NumericalThresholds
) -> list[str]:
    checks = (
        ("mae", float(metrics["mae"]), "<=", thresholds.mae_max),
        ("max_abs", float(metrics["max_abs"]), "<=", thresholds.max_abs_max),
        (
            "max_relative_away_from_zero",
            float(metrics["max_relative_away_from_zero"]),
            "<=",
            thresholds.max_relative_max,
        ),
        (
            "cosine_similarity",
            float(metrics["cosine_similarity"]),
            ">=",
            thresholds.cosine_min,
        ),
        (
            "spearman_rank_correlation",
            float(metrics["spearman_rank_correlation"]),
            ">=",
            thresholds.spearman_min,
        ),
    )
    failures: list[str] = []
    for name, actual, operator, limit in checks:
        if not math.isfinite(actual):
            failures.append(f"{name} is non-finite: {actual}")
        elif operator == "<=" and actual > limit:
            failures.append(f"{name}={actual:.9g} exceeds {limit:.9g}")
        elif operator == ">=" and actual < limit:
            failures.append(f"{name}={actual:.9g} is below {limit:.9g}")
    return failures


def require_numerical_gates(
    label: str,
    metrics: Mapping[str, Any],
    thresholds: NumericalThresholds,
) -> None:
    failures = numerical_gate_failures(metrics, thresholds)
    if failures:
        raise ValidationError(f"{label} numerical gates failed: " + "; ".join(failures))


class CudaRuntime:
    """Small checked wrapper around the CUDA Runtime C API."""

    def __init__(self, library_path: Path, expected_sha256: str) -> None:
        requested = library_path.expanduser()
        if not requested.is_file():
            raise ValidationError(f"libcudart is not a regular file: {requested}")
        self.requested_path = requested.absolute()
        self.path = requested.resolve()
        self.sha256 = verify_sha256(self.path, expected_sha256, "libcudart")
        try:
            self.lib = ctypes.CDLL(str(self.path), mode=ctypes.RTLD_LOCAL)
        except OSError as error:
            raise ValidationError(f"cannot load libcudart {self.path}: {error}") from error
        self._declare_functions()

    def _declare_functions(self) -> None:
        lib = self.lib
        lib.cudaGetErrorName.argtypes = [ctypes.c_int]
        lib.cudaGetErrorName.restype = ctypes.c_char_p
        lib.cudaGetErrorString.argtypes = [ctypes.c_int]
        lib.cudaGetErrorString.restype = ctypes.c_char_p
        lib.cudaSetDevice.argtypes = [ctypes.c_int]
        lib.cudaSetDevice.restype = ctypes.c_int
        lib.cudaGetDevice.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.cudaGetDevice.restype = ctypes.c_int
        lib.cudaRuntimeGetVersion.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.cudaRuntimeGetVersion.restype = ctypes.c_int
        lib.cudaDriverGetVersion.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.cudaDriverGetVersion.restype = ctypes.c_int
        lib.cudaDeviceGetAttribute.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
        ]
        lib.cudaDeviceGetAttribute.restype = ctypes.c_int
        lib.cudaMalloc.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_size_t,
        ]
        lib.cudaMalloc.restype = ctypes.c_int
        lib.cudaFree.argtypes = [ctypes.c_void_p]
        lib.cudaFree.restype = ctypes.c_int
        lib.cudaMallocHost.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_size_t,
        ]
        lib.cudaMallocHost.restype = ctypes.c_int
        lib.cudaFreeHost.argtypes = [ctypes.c_void_p]
        lib.cudaFreeHost.restype = ctypes.c_int
        lib.cudaMemcpyAsync.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        lib.cudaMemcpyAsync.restype = ctypes.c_int
        lib.cudaStreamCreateWithFlags.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_uint,
        ]
        lib.cudaStreamCreateWithFlags.restype = ctypes.c_int
        lib.cudaStreamSynchronize.argtypes = [ctypes.c_void_p]
        lib.cudaStreamSynchronize.restype = ctypes.c_int
        lib.cudaStreamDestroy.argtypes = [ctypes.c_void_p]
        lib.cudaStreamDestroy.restype = ctypes.c_int
        lib.cudaPeekAtLastError.argtypes = []
        lib.cudaPeekAtLastError.restype = ctypes.c_int

    def _error_text(self, code: int) -> str:
        name_bytes = self.lib.cudaGetErrorName(code)
        description_bytes = self.lib.cudaGetErrorString(code)
        name = name_bytes.decode("utf-8", errors="replace") if name_bytes else "unknown"
        description = (
            description_bytes.decode("utf-8", errors="replace")
            if description_bytes
            else "unknown error"
        )
        return f"{name} ({code}): {description}"

    def check(self, code: int, operation: str) -> None:
        numeric = int(code)
        if numeric != 0:
            raise ValidationError(
                f"CUDA Runtime call {operation} failed: {self._error_text(numeric)}"
            )

    def set_device(self, device: int) -> None:
        self.check(self.lib.cudaSetDevice(device), f"cudaSetDevice({device})")
        actual = ctypes.c_int()
        self.check(self.lib.cudaGetDevice(ctypes.byref(actual)), "cudaGetDevice")
        if actual.value != device:
            raise ValidationError(
                f"CUDA active-device mismatch: requested {device}, got {actual.value}"
            )

    def _get_version(self, function: Any, name: str) -> int:
        value = ctypes.c_int()
        self.check(function(ctypes.byref(value)), name)
        return int(value.value)

    def runtime_version(self) -> int:
        return self._get_version(self.lib.cudaRuntimeGetVersion, "cudaRuntimeGetVersion")

    def driver_version(self) -> int:
        return self._get_version(self.lib.cudaDriverGetVersion, "cudaDriverGetVersion")

    def device_attribute(self, attribute: int, device: int, label: str) -> int:
        value = ctypes.c_int()
        self.check(
            self.lib.cudaDeviceGetAttribute(
                ctypes.byref(value), int(attribute), int(device)
            ),
            f"cudaDeviceGetAttribute({label}, device={device})",
        )
        return int(value.value)

    def create_stream(self) -> int:
        stream = ctypes.c_void_p()
        self.check(
            self.lib.cudaStreamCreateWithFlags(
                ctypes.byref(stream), CUDA_STREAM_NON_BLOCKING
            ),
            "cudaStreamCreateWithFlags(non-blocking)",
        )
        if stream.value is None:
            raise ValidationError("cudaStreamCreateWithFlags returned a null stream")
        return int(stream.value)

    def destroy_stream(self, stream: int) -> None:
        self.check(
            self.lib.cudaStreamDestroy(ctypes.c_void_p(stream)),
            "cudaStreamDestroy",
        )

    def synchronize(self, stream: int) -> None:
        self.check(
            self.lib.cudaStreamSynchronize(ctypes.c_void_p(stream)),
            "cudaStreamSynchronize",
        )

    def peek_last_error(self) -> None:
        self.check(self.lib.cudaPeekAtLastError(), "cudaPeekAtLastError")

    def malloc(self, size_bytes: int) -> int:
        if size_bytes <= 0:
            raise ValidationError(f"invalid CUDA allocation size: {size_bytes}")
        pointer = ctypes.c_void_p()
        self.check(
            self.lib.cudaMalloc(ctypes.byref(pointer), ctypes.c_size_t(size_bytes)),
            f"cudaMalloc({size_bytes})",
        )
        if pointer.value is None:
            raise ValidationError("cudaMalloc returned a null pointer")
        if int(pointer.value) % 256:
            # TensorRT documents at least 256-byte alignment for registered buffers.
            try:
                self.free(int(pointer.value))
            finally:
                raise ValidationError(
                    f"cudaMalloc returned insufficiently aligned pointer {pointer.value:#x}"
                )
        return int(pointer.value)

    def free(self, pointer: int) -> None:
        self.check(self.lib.cudaFree(ctypes.c_void_p(pointer)), "cudaFree")

    def malloc_host(self, size_bytes: int) -> int:
        if size_bytes <= 0:
            raise ValidationError(f"invalid pinned-host allocation size: {size_bytes}")
        pointer = ctypes.c_void_p()
        self.check(
            self.lib.cudaMallocHost(
                ctypes.byref(pointer), ctypes.c_size_t(size_bytes)
            ),
            f"cudaMallocHost({size_bytes})",
        )
        if pointer.value is None:
            raise ValidationError("cudaMallocHost returned a null pointer")
        return int(pointer.value)

    def free_host(self, pointer: int) -> None:
        self.check(self.lib.cudaFreeHost(ctypes.c_void_p(pointer)), "cudaFreeHost")

    def memcpy_async(
        self,
        destination: int,
        source: int,
        size_bytes: int,
        direction: int,
        stream: int,
        label: str,
    ) -> None:
        self.check(
            self.lib.cudaMemcpyAsync(
                ctypes.c_void_p(destination),
                ctypes.c_void_p(source),
                ctypes.c_size_t(size_bytes),
                int(direction),
                ctypes.c_void_p(stream),
            ),
            label,
        )


class PinnedHostArray:
    """A NumPy array backed by cudaMallocHost memory."""

    def __init__(
        self, cuda: CudaRuntime, numpy: Any, shape: tuple[int, ...], dtype: Any
    ) -> None:
        self.cuda = cuda
        self.numpy = numpy
        self.shape = shape
        self.dtype = numpy.dtype(dtype)
        element_count = math.prod(shape)
        self.size_bytes = int(element_count * self.dtype.itemsize)
        self.pointer = cuda.malloc_host(self.size_bytes)
        self._backing = (ctypes.c_ubyte * self.size_bytes).from_address(self.pointer)
        raw = numpy.ctypeslib.as_array(self._backing)
        self.array = raw.view(self.dtype).reshape(shape)

    def close(self) -> None:
        pointer = self.pointer
        if not pointer:
            return
        self.pointer = 0
        self.array = None
        self._backing = None
        self.cuda.free_host(pointer)


def _cleanup_resources(
    *,
    cuda: CudaRuntime,
    stream: int | None,
    device_pointers: list[int],
    host_arrays: list[PinnedHostArray],
    primary_error: BaseException | None,
) -> None:
    errors: list[str] = []
    if stream is not None:
        try:
            cuda.synchronize(stream)
        except Exception as error:  # Cleanup must continue after a failed sync.
            errors.append(f"final stream synchronization: {error}")
    for pointer in reversed(device_pointers):
        try:
            cuda.free(pointer)
        except Exception as error:
            errors.append(f"device buffer cleanup: {error}")
    for host_array in reversed(host_arrays):
        try:
            host_array.close()
        except Exception as error:
            errors.append(f"pinned host buffer cleanup: {error}")
    if stream is not None:
        try:
            cuda.destroy_stream(stream)
        except Exception as error:
            errors.append(f"stream cleanup: {error}")

    if errors and primary_error is not None:
        for cleanup_error in errors:
            primary_error.add_note(cleanup_error)
    elif errors:
        raise ValidationError("CUDA cleanup failed: " + "; ".join(errors))


def load_tensorrt(
    dist_packages: Path,
    *,
    expected_version: str,
    expected_binding_sha256: str,
) -> tuple[Any, Path, str]:
    root = dist_packages.expanduser().resolve()
    if not root.is_dir():
        raise ValidationError(f"TensorRT dist-packages directory is missing: {root}")

    already_loaded = sys.modules.get("tensorrt")
    if already_loaded is not None:
        module_file = getattr(already_loaded, "__file__", None)
        if not module_file or not Path(module_file).resolve().is_relative_to(root):
            raise ValidationError(
                "TensorRT was already imported outside the audited dist-packages: "
                f"{module_file}"
            )
    if str(root) not in sys.path:
        # Append so the export venv's pinned torch/numpy remain authoritative.
        sys.path.append(str(root))
    try:
        tensorrt = importlib.import_module("tensorrt")
        binding = importlib.import_module("tensorrt.tensorrt")
    except (ImportError, ModuleNotFoundError, OSError) as error:
        raise ValidationError(
            f"cannot import system TensorRT from {root}: {error}"
        ) from error

    module_file = Path(tensorrt.__file__).resolve()
    binding_file = Path(binding.__file__).resolve()
    if not module_file.is_relative_to(root) or not binding_file.is_relative_to(root):
        raise ValidationError(
            "TensorRT import escaped audited dist-packages: "
            f"module={module_file}, binding={binding_file}"
        )
    version = str(tensorrt.__version__)
    if version != expected_version:
        raise ValidationError(
            f"TensorRT version mismatch: expected {expected_version}, got {version}"
        )
    binding_sha = verify_sha256(
        binding_file, expected_binding_sha256, "TensorRT Python binding"
    )
    return tensorrt, binding_file, binding_sha


def _enum_name(value: Any) -> str:
    name = getattr(value, "name", None)
    return str(name) if name is not None else str(value)


def _contiguous_strides(shape: tuple[int, ...]) -> tuple[int, ...]:
    strides: list[int] = []
    running = 1
    for dimension in reversed(shape):
        strides.append(running)
        running *= dimension
    return tuple(reversed(strides))


def inspect_static_engine_io(
    tensorrt: Any,
    numpy: Any,
    engine: Any,
    context: Any,
) -> tuple[TensorDescription, TensorDescription, Any, Any]:
    if int(engine.num_io_tensors) != 2:
        raise ValidationError(
            f"TensorRT engine must have exactly two I/O tensors, got {engine.num_io_tensors}"
        )
    if int(engine.num_optimization_profiles) != 1:
        raise ValidationError(
            "TensorRT engine must have exactly one static profile, got "
            f"{engine.num_optimization_profiles}"
        )
    tensor_names = [engine.get_tensor_name(index) for index in range(2)]
    if set(tensor_names) != {EXPECTED_INPUT_NAME, EXPECTED_OUTPUT_NAME}:
        raise ValidationError(
            "TensorRT I/O names mismatch: expected image/depth, got "
            f"{tensor_names}"
        )

    descriptions: dict[str, TensorDescription] = {}
    dtypes: dict[str, Any] = {}
    expected = {
        EXPECTED_INPUT_NAME: (tensorrt.TensorIOMode.INPUT, EXPECTED_INPUT_SHAPE),
        EXPECTED_OUTPUT_NAME: (tensorrt.TensorIOMode.OUTPUT, EXPECTED_OUTPUT_SHAPE),
    }
    for name in tensor_names:
        expected_mode, expected_shape = expected[name]
        mode = engine.get_tensor_mode(name)
        if mode != expected_mode:
            raise ValidationError(
                f"TensorRT tensor {name!r} mode mismatch: {_enum_name(mode)}"
            )
        engine_shape = tuple(int(item) for item in engine.get_tensor_shape(name))
        if engine_shape != expected_shape or any(item <= 0 for item in engine_shape):
            raise ValidationError(
                f"TensorRT tensor {name!r} is not expected static shape "
                f"{expected_shape}: {engine_shape}"
            )
        context_shape = tuple(int(item) for item in context.get_tensor_shape(name))
        if context_shape != expected_shape:
            raise ValidationError(
                f"TensorRT context tensor {name!r} shape mismatch: {context_shape}"
            )
        if bool(engine.is_shape_inference_io(name)):
            raise ValidationError(f"TensorRT tensor {name!r} is shape-inference I/O")
        location = engine.get_tensor_location(name)
        if location != tensorrt.TensorLocation.DEVICE:
            raise ValidationError(
                f"TensorRT tensor {name!r} is not device I/O: {_enum_name(location)}"
            )
        tensor_format = engine.get_tensor_format(name)
        if tensor_format != tensorrt.TensorFormat.LINEAR:
            raise ValidationError(
                f"TensorRT tensor {name!r} is not LINEAR: {_enum_name(tensor_format)}"
            )
        vectorized_dimension = int(engine.get_tensor_vectorized_dim(name))
        components = int(engine.get_tensor_components_per_element(name))
        bytes_per_component = int(engine.get_tensor_bytes_per_component(name))
        if vectorized_dimension != -1:
            raise ValidationError(
                f"TensorRT tensor {name!r} uses vectorized/padded storage: "
                f"vectorized_dim={vectorized_dimension}, components={components}"
            )

        trt_dtype = engine.get_tensor_dtype(name)
        try:
            numpy_dtype = numpy.dtype(tensorrt.nptype(trt_dtype))
        except (TypeError, ValueError) as error:
            raise ValidationError(
                f"TensorRT tensor {name!r} has unsupported dtype {_enum_name(trt_dtype)}"
            ) from error
        if str(numpy_dtype) != EXPECTED_IO_DTYPE:
            raise ValidationError(
                f"TensorRT tensor {name!r} dtype mismatch: expected "
                f"{EXPECTED_IO_DTYPE}, got {numpy_dtype}"
            )
        # TensorRT 10.16 reports -1/-1 when component metadata is not
        # applicable to a non-vectorized LINEAR tensor.  Some versions report
        # the explicit scalar pair 1/itemsize instead.  Accept exactly those
        # two representations and reject mixed/other sentinels or padding.
        component_metadata = (components, bytes_per_component)
        valid_component_metadata = {
            (-1, -1),
            (1, int(numpy_dtype.itemsize)),
        }
        if component_metadata not in valid_component_metadata:
            raise ValidationError(
                f"TensorRT tensor {name!r} has unexpected component metadata "
                f"{component_metadata}; expected (-1,-1) for non-vectorized "
                f"LINEAR or (1,{numpy_dtype.itemsize})"
            )
        strides = tuple(int(item) for item in context.get_tensor_strides(name))
        expected_strides = _contiguous_strides(expected_shape)
        if strides != expected_strides:
            raise ValidationError(
                f"TensorRT tensor {name!r} has non-contiguous strides: "
                f"expected {expected_strides}, got {strides}"
            )
        descriptions[name] = TensorDescription(
            name=name,
            mode=_enum_name(mode),
            shape=engine_shape,
            dtype=str(numpy_dtype),
            location=_enum_name(location),
            format=_enum_name(tensor_format),
            format_description=str(engine.get_tensor_format_desc(name)),
            vectorized_dimension=vectorized_dimension,
            components_per_element=components,
            bytes_per_component=bytes_per_component,
            effective_element_size_bytes=int(numpy_dtype.itemsize),
            strides=strides,
        )
        dtypes[name] = numpy_dtype

    return (
        descriptions[EXPECTED_INPUT_NAME],
        descriptions[EXPECTED_OUTPUT_NAME],
        dtypes[EXPECTED_INPUT_NAME],
        dtypes[EXPECTED_OUTPUT_NAME],
    )


def _engine_metadata(engine: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "name": str(engine.name),
        "num_layers": int(engine.num_layers),
        "num_io_tensors": int(engine.num_io_tensors),
        "num_optimization_profiles": int(engine.num_optimization_profiles),
        "device_memory_size_bytes": int(engine.device_memory_size_v2),
    }
    # Do not probe the budget property on a plan that lacks kWEIGHT_STREAMING:
    # even hasattr() invokes TensorRT's getter and emits an API error.  The
    # capability-neutral size property is safe and sufficient for this record.
    for attribute in ("num_aux_streams", "streamable_weights_size"):
        if hasattr(engine, attribute):
            value = getattr(engine, attribute)
            fields[attribute] = int(value)
    for attribute in (
        "engine_capability",
        "hardware_compatibility_level",
        "profiling_verbosity",
        "tactic_sources",
    ):
        if hasattr(engine, attribute):
            fields[attribute] = _enum_name(getattr(engine, attribute))
    return fields


def execute_plan_once(
    *,
    tensorrt: Any,
    numpy: Any,
    cuda: CudaRuntime,
    plan_path: Path,
    expected_plan_sha256: str,
    input_array: Any,
    precision_label: str,
) -> tuple[Any, dict[str, Any]]:
    plan_sha256 = verify_sha256(
        plan_path, expected_plan_sha256, f"ZipDepth {precision_label} TensorRT plan"
    )
    try:
        serialized_engine = plan_path.read_bytes()
    except OSError as error:
        raise ValidationError(f"cannot read TensorRT plan {plan_path}: {error}") from error
    logger = tensorrt.Logger(tensorrt.Logger.ERROR)
    runtime = tensorrt.Runtime(logger)
    if runtime is None:
        raise ValidationError("TensorRT Runtime construction returned None")
    runtime.engine_host_code_allowed = False
    if bool(runtime.engine_host_code_allowed):
        raise ValidationError("TensorRT runtime unexpectedly allows engine host code")

    engine = None
    context = None
    try:
        engine = runtime.deserialize_cuda_engine(serialized_engine)
        if engine is None:
            raise ValidationError(
                f"TensorRT could not deserialize the pinned {precision_label} plan"
            )
        context = engine.create_execution_context()
        if context is None:
            raise ValidationError(
                f"TensorRT could not create a context for the {precision_label} plan"
            )
        input_description, output_description, input_dtype, output_dtype = (
            inspect_static_engine_io(tensorrt, numpy, engine, context)
        )
        engine_metadata = _engine_metadata(engine)

        converted_input = numpy.ascontiguousarray(input_array, dtype=input_dtype)
        if tuple(converted_input.shape) != EXPECTED_INPUT_SHAPE:
            raise ValidationError(
                f"converted TensorRT input shape mismatch: {converted_input.shape}"
            )

        stream: int | None = None
        device_pointers: list[int] = []
        host_arrays: list[PinnedHostArray] = []
        primary_error: BaseException | None = None
        output_copy = None
        elapsed_ms = 0.0
        try:
            stream = cuda.create_stream()
            host_input = PinnedHostArray(cuda, numpy, EXPECTED_INPUT_SHAPE, input_dtype)
            host_arrays.append(host_input)
            host_output = PinnedHostArray(
                cuda, numpy, EXPECTED_OUTPUT_SHAPE, output_dtype
            )
            host_arrays.append(host_output)
            numpy.copyto(host_input.array, converted_input, casting="no")
            host_output.array.fill(numpy.nan)

            device_input = cuda.malloc(host_input.size_bytes)
            device_pointers.append(device_input)
            device_output = cuda.malloc(host_output.size_bytes)
            device_pointers.append(device_output)

            if not bool(context.set_tensor_address(EXPECTED_INPUT_NAME, device_input)):
                raise ValidationError("TensorRT rejected the image device address")
            if not bool(context.set_tensor_address(EXPECTED_OUTPUT_NAME, device_output)):
                raise ValidationError("TensorRT rejected the depth device address")
            unresolved = list(context.infer_shapes())
            if unresolved:
                raise ValidationError(
                    f"TensorRT context has unresolved inference tensors: {unresolved}"
                )

            start = time.perf_counter()
            cuda.memcpy_async(
                device_input,
                host_input.pointer,
                host_input.size_bytes,
                CUDA_MEMCPY_HOST_TO_DEVICE,
                stream,
                "cudaMemcpyAsync(H2D image)",
            )
            if not bool(context.execute_async_v3(stream)):
                raise ValidationError("TensorRT execute_async_v3 returned False")
            cuda.peek_last_error()
            cuda.memcpy_async(
                host_output.pointer,
                device_output,
                host_output.size_bytes,
                CUDA_MEMCPY_DEVICE_TO_HOST,
                stream,
                "cudaMemcpyAsync(D2H depth)",
            )
            cuda.synchronize(stream)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            output_copy = numpy.array(host_output.array, copy=True, order="C")
        except BaseException as error:
            primary_error = error
            raise
        finally:
            # Drop TensorRT's registered-address context before releasing buffers.
            context = None
            gc.collect()
            _cleanup_resources(
                cuda=cuda,
                stream=stream,
                device_pointers=device_pointers,
                host_arrays=host_arrays,
                primary_error=primary_error,
            )

        if output_copy is None:
            raise ValidationError("TensorRT execution produced no copied output")
        require_depth_array(
            numpy, output_copy, EXPECTED_OUTPUT_SHAPE, f"{precision_label} output"
        )
        details = {
            "precision_label": precision_label,
            "plan": {
                "path": str(plan_path),
                "size_bytes": plan_path.stat().st_size,
                "sha256": plan_sha256,
            },
            "engine": engine_metadata,
            "input": asdict(input_description),
            "output": asdict(output_description),
            "one_shot_h2d_execute_d2h_ms": elapsed_ms,
            "timing_note": "single acceptance run; not a warmed performance benchmark",
            "output_summary": array_summary(numpy, output_copy),
        }
        return output_copy, details
    finally:
        context = None
        engine = None
        runtime = None
        logger = None
        gc.collect()


def _read_l4t_release() -> str | None:
    path = Path("/etc/nv_tegra_release")
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _cuda_version_text(version: int) -> str:
    major = version // 1000
    minor = (version % 1000) // 10
    return f"{major}.{minor}"


def _temporary_path_for(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    os.close(descriptor)
    return Path(name)


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = _temporary_path_for(path)
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_paths(args: argparse.Namespace) -> ArtifactPaths:
    paths = ArtifactPaths(
        export_manifest=args.export_manifest.expanduser().resolve(),
        onnx=args.onnx.expanduser().resolve(),
        fp32_plan=args.fp32_plan.expanduser().resolve(),
        fp16_plan=args.fp16_plan.expanduser().resolve(),
        output=args.output.expanduser().resolve(),
        tensorrt_dist_packages=args.tensorrt_dist_packages.expanduser().resolve(),
        cudart=args.cudart.expanduser().resolve(),
    )
    inputs = {
        paths.export_manifest,
        paths.onnx,
        paths.fp32_plan,
        paths.fp16_plan,
        EXPORTER_PATH.resolve(),
    }
    if paths.output in inputs:
        raise ValidationError("validation manifest must not replace an input artifact")
    if paths.output.suffix.lower() != ".json":
        raise ValidationError(
            f"validation manifest output must end in .json: {paths.output}"
        )
    if paths.fp32_plan == paths.fp16_plan:
        raise ValidationError("FP32 and FP16 plan paths must differ")
    if paths.output.exists() and not args.force:
        raise ValidationError(
            f"validation manifest exists; pass --force to replace it: {paths.output}"
        )
    return paths


def validate_args(args: argparse.Namespace) -> None:
    if args.device < 0:
        raise ValidationError(f"CUDA device must be non-negative, got {args.device}")
    if args.relative_floor <= 0.0 or not math.isfinite(args.relative_floor):
        raise ValidationError(
            f"relative error floor must be finite and positive: {args.relative_floor}"
        )
    for label in (
        "export_manifest_sha256",
        "exporter_sha256",
        "onnx_sha256",
        "fp32_plan_sha256",
        "fp16_plan_sha256",
        "tensorrt_binding_sha256",
        "cudart_sha256",
    ):
        setattr(args, label, require_sha256_text(getattr(args, label), label))
    for prefix in ("fp32", "fp16"):
        for suffix in ("mae_max", "max_abs_max", "max_relative_max"):
            value = float(getattr(args, f"{prefix}_{suffix}"))
            if value < 0.0 or not math.isfinite(value):
                raise ValidationError(
                    f"{prefix}_{suffix} must be finite and non-negative: {value}"
                )
        for suffix in ("cosine_min", "spearman_min"):
            value = float(getattr(args, f"{prefix}_{suffix}"))
            if not math.isfinite(value) or not -1.0 <= value <= 1.0:
                raise ValidationError(
                    f"{prefix}_{suffix} must be finite in [-1,1]: {value}"
                )


def thresholds_from_args(
    args: argparse.Namespace,
) -> tuple[NumericalThresholds, NumericalThresholds]:
    return (
        NumericalThresholds(
            mae_max=args.fp32_mae_max,
            max_abs_max=args.fp32_max_abs_max,
            max_relative_max=args.fp32_max_relative_max,
            cosine_min=args.fp32_cosine_min,
            spearman_min=args.fp32_spearman_min,
        ),
        NumericalThresholds(
            mae_max=args.fp16_mae_max,
            max_abs_max=args.fp16_max_abs_max,
            max_relative_max=args.fp16_max_relative_max,
            cosine_min=args.fp16_cosine_min,
            spearman_min=args.fp16_spearman_min,
        ),
    )


def _verify_reference_provenance(
    *,
    exporter: Any,
    manifest: Mapping[str, Any],
    onnx_path: Path,
    expected_onnx_sha256: str,
) -> tuple[Path, Path, int]:
    source_root = Path(str(_nested(manifest, "source.checkout"))).resolve()
    checkpoint = Path(str(_nested(manifest, "checkpoint.path"))).resolve()
    seed = int(_nested(manifest, "deterministic_test.seed"))
    require_manifest_value(manifest, "source.commit", exporter.EXPECTED_SOURCE_COMMIT)
    require_manifest_value(
        manifest, "checkpoint.sha256", exporter.EXPECTED_CHECKPOINT_SHA256
    )
    require_manifest_value(manifest, "export.opset", exporter.ONNX_OPSET)
    require_manifest_value(manifest, "export.dynamo", False)
    require_manifest_value(manifest, "export.onnxsim", False)
    verify_sha256(onnx_path, expected_onnx_sha256, "faithful ZipDepth ONNX")
    if Path(str(_nested(manifest, "onnx.path"))).resolve() != onnx_path:
        raise ValidationError(
            "ONNX path differs from the path attested by the export manifest"
        )
    source = exporter.verify_source_checkout(source_root)
    if source.commit != str(_nested(manifest, "source.commit")):
        raise ValidationError("source commit differs from export manifest")
    exporter.verify_file_sha256(
        checkpoint,
        exporter.EXPECTED_CHECKPOINT_SHA256,
        "ZipDepth checkpoint",
    )
    return source_root, checkpoint, seed


def recreate_fused_reference(
    *,
    exporter: Any,
    manifest: Mapping[str, Any],
    source_root: Path,
    checkpoint: Path,
    seed: int,
) -> tuple[Any, Any, Any, Mapping[str, Any]]:
    modules = exporter.load_runtime_modules(source_root)
    reference_model = exporter.load_reference_model(modules, checkpoint, seed)
    fused_model, export_model, remaining_fusions, context_count = exporter.prepare_models(
        modules, reference_model
    )
    if remaining_fusions != int(_nested(manifest, "model.remaining_conv_bn_fusions")):
        raise ValidationError(
            "current fusion count differs from the audited export manifest: "
            f"{remaining_fusions}"
        )
    if context_count != int(
        _nested(manifest, "model.global_context_blocks_verified_faithful")
    ):
        raise ValidationError(
            "current faithful GlobalContext count differs from export manifest"
        )

    test_input = exporter.deterministic_test_input(
        modules.torch, EXPECTED_INPUT_SHAPE[2], EXPECTED_INPUT_SHAPE[3], seed
    )
    with modules.torch.inference_mode():
        fused_output = fused_model(test_input)
    exporter.require_valid_depth_output(
        modules.torch,
        fused_output,
        EXPECTED_OUTPUT_SHAPE[2],
        EXPECTED_OUTPUT_SHAPE[3],
        "recreated fused PyTorch output",
    )
    input_sha = exporter.tensor_sha256(test_input)
    reference_sha = exporter.tensor_sha256(fused_output)
    if input_sha != str(_nested(manifest, "deterministic_test.input_sha256")):
        raise ValidationError(
            "recreated deterministic input hash differs from export manifest: "
            f"{input_sha}"
        )
    expected_reference_sha = str(
        _nested(manifest, "deterministic_test.parity.fused_output.sha256")
    )
    if reference_sha != expected_reference_sha:
        raise ValidationError(
            "recreated fused PyTorch output hash differs from export manifest: "
            f"expected {expected_reference_sha}, got {reference_sha}"
        )
    input_array = test_input.detach().cpu().contiguous().numpy()
    reference_array = fused_output.detach().cpu().contiguous().numpy()
    require_depth_array(
        modules.numpy,
        reference_array,
        EXPECTED_OUTPUT_SHAPE,
        "fused PyTorch reference",
    )
    details = {
        "source_commit": exporter.EXPECTED_SOURCE_COMMIT,
        "checkpoint_sha256": exporter.EXPECTED_CHECKPOINT_SHA256,
        "model": {
            "variant": "base",
            "global_mode": "balanced",
            "upsample_unfold": True,
            "remaining_conv_bn_fusions": remaining_fusions,
            "faithful_global_context_blocks": context_count,
        },
        "seed": seed,
        "input_summary": array_summary(modules.numpy, input_array),
        "output_summary": array_summary(modules.numpy, reference_array),
    }
    # Release the duplicate unfused/export-prepared models before GPU validation.
    reference_model = None
    export_model = None
    fused_model = None
    gc.collect()
    return modules, input_array, reference_array, details


def build_validation_manifest(
    *,
    args: argparse.Namespace,
    paths: ArtifactPaths,
    exporter: Any,
    export_manifest: Mapping[str, Any],
    modules: Any,
    reference_details: Mapping[str, Any],
    tensorrt: Any,
    tensorrt_binding_path: Path,
    tensorrt_binding_sha256: str,
    cuda: CudaRuntime,
    cuda_details: Mapping[str, Any],
    fp32_details: Mapping[str, Any],
    fp16_details: Mapping[str, Any],
    fp32_metrics: Mapping[str, Any],
    fp16_metrics: Mapping[str, Any],
    cross_metrics: Mapping[str, Any],
    fp32_thresholds: NumericalThresholds,
    fp16_thresholds: NumericalThresholds,
) -> dict[str, Any]:
    validator = Path(__file__).resolve()
    tensorrt_init = Path(tensorrt.__file__).resolve()
    return {
        "schema": VALIDATION_SCHEMA,
        "status": "passed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "one-shot numerical acceptance of pinned ZipDepth TensorRT plans",
        "artifacts": {
            "export_manifest": {
                "path": str(paths.export_manifest),
                "sha256": sha256_file(paths.export_manifest),
                "schema": str(export_manifest["schema"]),
            },
            "exporter": {
                "path": str(EXPORTER_PATH.resolve()),
                "sha256": sha256_file(EXPORTER_PATH),
            },
            "onnx": {
                "path": str(paths.onnx),
                "size_bytes": paths.onnx.stat().st_size,
                "sha256": sha256_file(paths.onnx),
            },
        },
        "reference": dict(reference_details),
        "engines": {
            "fp32": {
                **dict(fp32_details),
                "comparison_to_fused_pytorch": dict(fp32_metrics),
                "thresholds": asdict(fp32_thresholds),
                "gates_passed": True,
            },
            "fp16": {
                **dict(fp16_details),
                "comparison_to_fused_pytorch": dict(fp16_metrics),
                "thresholds": asdict(fp16_thresholds),
                "gates_passed": True,
            },
        },
        "fp16_vs_fp32": {
            "metrics": dict(cross_metrics),
            "thresholds": asdict(fp16_thresholds),
            "gates_passed": True,
        },
        "relative_error_floor": args.relative_floor,
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "l4t_release": _read_l4t_release(),
            "torch": str(modules.torch.__version__),
            "numpy": str(modules.numpy.__version__),
            "onnx": str(modules.onnx.__version__),
            "tensorrt": {
                "version": str(tensorrt.__version__),
                "package_init": str(tensorrt_init),
                "package_init_sha256": sha256_file(tensorrt_init),
                "binding": str(tensorrt_binding_path),
                "binding_sha256": tensorrt_binding_sha256,
                "dist_packages": str(paths.tensorrt_dist_packages),
                "engine_host_code_allowed": False,
            },
            "cuda": dict(cuda_details),
        },
        "validator": {
            "path": str(validator),
            "sha256": sha256_file(validator),
            "invocation": shlex.join(sys.argv),
            "working_directory": str(Path.cwd()),
            "implementation": {
                "tensor_api": "TensorRT 10 name-based I/O / execute_async_v3",
                "cuda_api": "stdlib ctypes against libcudart",
                "host_staging": "cudaMallocHost pinned memory",
                "stream": "single non-default non-blocking CUDA stream",
                "scipy": False,
                "rank_correlation": "full-array stable average-tie Spearman",
            },
        },
    }


def run_validation(args: argparse.Namespace) -> Path:
    validate_args(args)
    paths = resolve_paths(args)
    fp32_thresholds, fp16_thresholds = thresholds_from_args(args)

    print("[1/7] verifying export manifest, exporter, ONNX, and plans", flush=True)
    export_manifest = load_verified_export_manifest(
        paths.export_manifest,
        expected_manifest_sha256=args.export_manifest_sha256,
        expected_exporter_sha256=args.exporter_sha256,
        expected_onnx_sha256=args.onnx_sha256,
    )
    exporter = load_verified_exporter(EXPORTER_PATH.resolve(), args.exporter_sha256)
    source_root, checkpoint, seed = _verify_reference_provenance(
        exporter=exporter,
        manifest=export_manifest,
        onnx_path=paths.onnx,
        expected_onnx_sha256=args.onnx_sha256,
    )
    verify_sha256(paths.fp32_plan, args.fp32_plan_sha256, "FP32 TensorRT plan")
    verify_sha256(paths.fp16_plan, args.fp16_plan_sha256, "FP16 TensorRT plan")

    print("[2/7] recreating exact deterministic fused PyTorch reference", flush=True)
    modules, input_array, reference_array, reference_details = recreate_fused_reference(
        exporter=exporter,
        manifest=export_manifest,
        source_root=source_root,
        checkpoint=checkpoint,
        seed=seed,
    )

    print("[3/7] loading pinned TensorRT binding and libcudart", flush=True)
    tensorrt, binding_path, binding_sha = load_tensorrt(
        paths.tensorrt_dist_packages,
        expected_version=EXPECTED_TENSORRT_VERSION,
        expected_binding_sha256=args.tensorrt_binding_sha256,
    )
    cuda = CudaRuntime(paths.cudart, args.cudart_sha256)
    cuda.set_device(args.device)
    runtime_version = cuda.runtime_version()
    driver_version = cuda.driver_version()
    if runtime_version != EXPECTED_CUDA_RUNTIME_VERSION:
        raise ValidationError(
            "CUDA Runtime version mismatch: expected "
            f"{_cuda_version_text(EXPECTED_CUDA_RUNTIME_VERSION)}, got "
            f"{_cuda_version_text(runtime_version)} ({runtime_version})"
        )
    if driver_version < runtime_version:
        raise ValidationError(
            f"CUDA driver API {driver_version} is older than runtime {runtime_version}"
        )
    compute_capability = (
        cuda.device_attribute(
            CUDA_DEV_ATTR_COMPUTE_CAPABILITY_MAJOR,
            args.device,
            "compute capability major",
        ),
        cuda.device_attribute(
            CUDA_DEV_ATTR_COMPUTE_CAPABILITY_MINOR,
            args.device,
            "compute capability minor",
        ),
    )
    if compute_capability != EXPECTED_COMPUTE_CAPABILITY:
        raise ValidationError(
            "GPU compute capability mismatch: expected sm_87, got "
            f"sm_{compute_capability[0]}{compute_capability[1]}"
        )
    cuda_details = {
        "device": args.device,
        "compute_capability": f"{compute_capability[0]}.{compute_capability[1]}",
        "runtime_version_number": runtime_version,
        "runtime_version": _cuda_version_text(runtime_version),
        "driver_api_version_number": driver_version,
        "driver_api_version": _cuda_version_text(driver_version),
        "libcudart_requested": str(cuda.requested_path),
        "libcudart_resolved": str(cuda.path),
        "libcudart_sha256": cuda.sha256,
    }

    print("[4/7] running pinned FP32 diagnostic plan once", flush=True)
    fp32_output, fp32_details = execute_plan_once(
        tensorrt=tensorrt,
        numpy=modules.numpy,
        cuda=cuda,
        plan_path=paths.fp32_plan,
        expected_plan_sha256=args.fp32_plan_sha256,
        input_array=input_array,
        precision_label="fp32_no_tf32",
    )
    fp32_metrics = comparison_metrics(
        modules.numpy,
        reference_array,
        fp32_output,
        relative_floor=args.relative_floor,
    )
    require_numerical_gates(
        "fused PyTorch vs FP32 TensorRT", fp32_metrics, fp32_thresholds
    )

    print("[5/7] running pinned FP16 candidate plan once", flush=True)
    fp16_output, fp16_details = execute_plan_once(
        tensorrt=tensorrt,
        numpy=modules.numpy,
        cuda=cuda,
        plan_path=paths.fp16_plan,
        expected_plan_sha256=args.fp16_plan_sha256,
        input_array=input_array,
        precision_label="fp16_internal_fp32_io",
    )
    fp16_metrics = comparison_metrics(
        modules.numpy,
        reference_array,
        fp16_output,
        relative_floor=args.relative_floor,
    )
    require_numerical_gates(
        "fused PyTorch vs FP16 TensorRT", fp16_metrics, fp16_thresholds
    )

    print("[6/7] comparing FP16 directly with diagnostic FP32", flush=True)
    cross_metrics = comparison_metrics(
        modules.numpy,
        fp32_output,
        fp16_output,
        relative_floor=args.relative_floor,
    )
    require_numerical_gates(
        "FP32 TensorRT vs FP16 TensorRT", cross_metrics, fp16_thresholds
    )

    print("[7/7] atomically publishing passed validation manifest", flush=True)
    validation_manifest = build_validation_manifest(
        args=args,
        paths=paths,
        exporter=exporter,
        export_manifest=export_manifest,
        modules=modules,
        reference_details=reference_details,
        tensorrt=tensorrt,
        tensorrt_binding_path=binding_path,
        tensorrt_binding_sha256=binding_sha,
        cuda=cuda,
        cuda_details=cuda_details,
        fp32_details=fp32_details,
        fp16_details=fp16_details,
        fp32_metrics=fp32_metrics,
        fp16_metrics=fp16_metrics,
        cross_metrics=cross_metrics,
        fp32_thresholds=fp32_thresholds,
        fp16_thresholds=fp16_thresholds,
    )
    atomic_write_json(paths.output, validation_manifest)
    print(
        f"TENSORRT_VALIDATION_PASSED path={paths.output} "
        f"sha256={sha256_file(paths.output)}",
        flush=True,
    )
    return paths.output


def _add_threshold_arguments(
    parser: argparse.ArgumentParser,
    prefix: str,
    defaults: NumericalThresholds,
) -> None:
    parser.add_argument(f"--{prefix}-mae-max", type=float, default=defaults.mae_max)
    parser.add_argument(
        f"--{prefix}-max-abs-max", type=float, default=defaults.max_abs_max
    )
    parser.add_argument(
        f"--{prefix}-max-relative-max",
        type=float,
        default=defaults.max_relative_max,
    )
    parser.add_argument(
        f"--{prefix}-cosine-min", type=float, default=defaults.cosine_min
    )
    parser.add_argument(
        f"--{prefix}-spearman-min", type=float, default=defaults.spearman_min
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-manifest", type=Path, default=DEFAULT_EXPORT_MANIFEST)
    parser.add_argument("--onnx", type=Path, default=DEFAULT_ONNX)
    parser.add_argument("--fp32-plan", type=Path, default=DEFAULT_FP32_PLAN)
    parser.add_argument("--fp16-plan", type=Path, default=DEFAULT_FP16_PLAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--tensorrt-dist-packages",
        type=Path,
        default=DEFAULT_TENSORRT_DIST_PACKAGES,
        help="system TensorRT path appended after the export venv site-packages",
    )
    parser.add_argument("--cudart", type=Path, default=DEFAULT_CUDART)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--relative-floor", type=float, default=1.0e-6)
    parser.add_argument(
        "--export-manifest-sha256", default=EXPECTED_EXPORT_MANIFEST_SHA256
    )
    parser.add_argument("--exporter-sha256", default=EXPECTED_EXPORTER_SHA256)
    parser.add_argument("--onnx-sha256", default=EXPECTED_ONNX_SHA256)
    parser.add_argument("--fp32-plan-sha256", default=EXPECTED_FP32_PLAN_SHA256)
    parser.add_argument("--fp16-plan-sha256", default=EXPECTED_FP16_PLAN_SHA256)
    parser.add_argument(
        "--tensorrt-binding-sha256", default=EXPECTED_TENSORRT_BINDING_SHA256
    )
    parser.add_argument("--cudart-sha256", default=EXPECTED_CUDART_SHA256)
    _add_threshold_arguments(parser, "fp32", DEFAULT_FP32_THRESHOLDS)
    _add_threshold_arguments(parser, "fp16", DEFAULT_FP16_THRESHOLDS)
    parser.add_argument(
        "--force",
        action="store_true",
        help="atomically replace an existing passed-validation manifest",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_validation(args)
    except ValidationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
