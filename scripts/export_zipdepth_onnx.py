#!/usr/bin/env python3
"""Export the pinned ZipDepth checkpoint to a faithful static ONNX graph.

This is intentionally an export/provenance tool, not a camera runtime.  It
leaves the pinned upstream checkout untouched, uses CPU PyTorch, rejects source
or checkpoint drift, preserves the learned GlobalContext implementation, and
writes a manifest beside the checked ONNX artifact.

The expected environment is documented in
``docs/research/2026-07-13-zipdepth-runtime.md``.  In particular, this exporter
uses PyTorch's legacy static exporter explicitly (``dynamo=False``), ONNX opset
17, and no ONNX simplifier.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import tempfile
from typing import Any


EXPECTED_SOURCE_COMMIT = "a302e5437bc58f15c4efd41d3e8222bf24f7d470"
EXPECTED_SOURCE_URL = "https://github.com/fabiotosi92/ZipDepth"
EXPECTED_CHECKPOINT_SHA256 = (
    "a55910bb0b99c8c5e641cb9206e810b269690ad94e8a2ef08c827c4679391a65"
)
DEFAULT_SOURCE_ROOT = Path(
    "/home/neko/models/ZipDepth/a302e5437bc58f15c4efd41d3e8222bf24f7d470"
)
DEFAULT_CHECKPOINT_RELATIVE = Path("checkpoints/zipdepth_base.pth")
DEFAULT_HEIGHT = 384
DEFAULT_WIDTH = 672
DEFAULT_SEED = 20_260_713
REQUIRED_MULTIPLE = 32
ONNX_OPSET = 17
MANIFEST_SCHEMA = "neko.zipdepth-onnx-export/v1"
HASH_CHUNK_SIZE = 1024 * 1024
EXPECTED_TORCH_VERSION = "2.12.1+cpu"
EXPECTED_ONNX_VERSION = "1.18.0"
EXPECTED_NUMPY_VERSION = "1.26.2"


class ExportError(RuntimeError):
    """A safety, integrity, compatibility, or export check failed."""


@dataclass(frozen=True)
class SourceVerification:
    """Verified identity of the source checkout."""

    root: Path
    commit: str
    origin: str | None


@dataclass(frozen=True)
class ArtifactPaths:
    """Resolved input and output paths for one export."""

    source_root: Path
    checkpoint: Path
    output: Path
    manifest: Path


@dataclass(frozen=True)
class RuntimeModules:
    """Late imports needed only for a real model export."""

    torch: Any
    onnx: Any
    numpy: Any
    create_model: Any
    fuse_remaining_conv_bn: Any
    strip_state_dict_prefixes: Any


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of *path* without loading it all into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file_sha256(path: Path, expected: str, label: str) -> str:
    """Require an existing regular file with the expected SHA-256."""

    if not path.is_file():
        raise ExportError(f"{label} is not a regular file: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ExportError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual}: {path}"
        )
    return actual


def validate_dimensions(height: int, width: int) -> None:
    """Require the fixed geometry supported by the audited architecture."""

    for name, value in (("height", height), ("width", width)):
        if value < REQUIRED_MULTIPLE:
            raise ExportError(
                f"{name} must be at least {REQUIRED_MULTIPLE}, got {value}"
            )
        if value % REQUIRED_MULTIPLE:
            raise ExportError(
                f"{name} must be a multiple of {REQUIRED_MULTIPLE}, got {value}"
            )


def state_key_diff(
    expected_keys: Iterable[str], actual_keys: Iterable[str]
) -> tuple[list[str], list[str]]:
    """Return sorted missing and unexpected checkpoint keys."""

    expected = set(expected_keys)
    actual = set(actual_keys)
    return sorted(expected - actual), sorted(actual - expected)


def require_exact_state_keys(
    expected_keys: Iterable[str], actual_keys: Iterable[str]
) -> None:
    """Fail closed rather than leaving any parameter randomly initialized."""

    missing, unexpected = state_key_diff(expected_keys, actual_keys)
    if not missing and not unexpected:
        return
    details: list[str] = []
    if missing:
        details.append(f"missing ({len(missing)}): {', '.join(missing[:20])}")
    if unexpected:
        details.append(
            f"unexpected ({len(unexpected)}): {', '.join(unexpected[:20])}"
        )
    raise ExportError("checkpoint state keys are not exact; " + "; ".join(details))


def _run_git(root: Path, *args: str, allow_failure: bool = False) -> str | None:
    command = ["git", "-C", str(root), *args]
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode:
        if allow_failure:
            return None
        error = completed.stderr.strip() or completed.stdout.strip()
        raise ExportError(f"git command failed ({shlex.join(command)}): {error}")
    return completed.stdout.strip()


def verify_source_checkout(
    source_root: Path, expected_commit: str = EXPECTED_SOURCE_COMMIT
) -> SourceVerification:
    """Verify exact Git commit, top-level path, and tracked-file cleanliness."""

    root = source_root.expanduser().resolve()
    if not root.is_dir():
        raise ExportError(f"ZipDepth source root is not a directory: {root}")

    top_level_text = _run_git(root, "rev-parse", "--show-toplevel")
    assert top_level_text is not None
    top_level = Path(top_level_text).resolve()
    if top_level != root:
        raise ExportError(
            f"source root is not the checkout top level: root={root}, git={top_level}"
        )

    commit = _run_git(root, "rev-parse", "HEAD")
    assert commit is not None
    if commit != expected_commit:
        raise ExportError(
            f"ZipDepth commit mismatch: expected {expected_commit}, got {commit}"
        )

    tracked_status = _run_git(
        root, "status", "--porcelain", "--untracked-files=no"
    )
    if tracked_status:
        raise ExportError(
            "ZipDepth checkout has tracked changes; refusing to import modified "
            f"upstream code:\n{tracked_status}"
        )

    origin = _run_git(root, "remote", "get-url", "origin", allow_failure=True)
    return SourceVerification(root=root, commit=commit, origin=origin)


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def resolve_artifact_paths(args: argparse.Namespace) -> ArtifactPaths:
    """Resolve paths and keep generated artifacts out of the source checkout."""

    source_root = args.source_root.expanduser().resolve()
    checkpoint = (
        args.checkpoint.expanduser().resolve()
        if args.checkpoint is not None
        else (source_root / DEFAULT_CHECKPOINT_RELATIVE).resolve()
    )
    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else source_root.parent
        / "engines"
        / f"zipdepth_base_b1_{args.height}x{args.width}_op{ONNX_OPSET}.onnx"
    )
    manifest = (
        args.manifest.expanduser().resolve()
        if args.manifest is not None
        else output.with_suffix(".manifest.json")
    )

    if output.suffix.lower() != ".onnx":
        raise ExportError(f"ONNX output must end in .onnx: {output}")
    if manifest.suffix.lower() != ".json":
        raise ExportError(f"manifest output must end in .json: {manifest}")
    if output == manifest:
        raise ExportError("ONNX and manifest paths must differ")
    if output == checkpoint or manifest == checkpoint:
        raise ExportError("generated artifacts must not replace the checkpoint")
    for label, candidate in (("ONNX output", output), ("manifest", manifest)):
        if _is_within(candidate, source_root):
            raise ExportError(
                f"{label} must be outside the pinned source checkout: {candidate}"
            )
        if candidate.exists() and not args.force:
            raise ExportError(
                f"{label} already exists; pass --force to replace it: {candidate}"
            )

    return ArtifactPaths(
        source_root=source_root,
        checkpoint=checkpoint,
        output=output,
        manifest=manifest,
    )


def _module_is_below(module: Any, source_root: Path) -> bool:
    module_file = getattr(module, "__file__", None)
    if not module_file:
        return False
    return _is_within(Path(module_file).resolve(), source_root)


def load_runtime_modules(source_root: Path) -> RuntimeModules:
    """Import PyTorch/ONNX and the architecture from the verified checkout."""

    try:
        torch = importlib.import_module("torch")
        onnx = importlib.import_module("onnx")
        numpy = importlib.import_module("numpy")
    except ModuleNotFoundError as error:
        raise ExportError(
            f"missing export dependency {error.name!r}; use the pinned export environment"
        ) from error

    already_loaded = [
        module
        for name, module in sys.modules.items()
        if (name == "zipdepth" or name.startswith("zipdepth.")) and module is not None
    ]
    wrong_modules = [
        getattr(module, "__file__", repr(module))
        for module in already_loaded
        if not _module_is_below(module, source_root)
    ]
    if wrong_modules:
        raise ExportError(
            "a ZipDepth module was already imported outside the verified checkout: "
            + ", ".join(str(item) for item in wrong_modules)
        )

    sys.path.insert(0, str(source_root))
    old_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        try:
            architecture = importlib.import_module("zipdepth.model.architecture")
            model_utils = importlib.import_module("zipdepth.utils.model_utils")
        except ModuleNotFoundError as error:
            raise ExportError(
                f"failed to import pinned ZipDepth source dependency {error.name!r}"
            ) from error
    finally:
        sys.dont_write_bytecode = old_dont_write_bytecode
        try:
            sys.path.remove(str(source_root))
        except ValueError:
            pass

    for name, module in (("architecture", architecture), ("model_utils", model_utils)):
        if not _module_is_below(module, source_root):
            raise ExportError(
                f"imported ZipDepth {name} outside verified source: "
                f"{getattr(module, '__file__', None)}"
            )

    modules = RuntimeModules(
        torch=torch,
        onnx=onnx,
        numpy=numpy,
        create_model=architecture.create_model,
        fuse_remaining_conv_bn=model_utils.fuse_remaining_conv_bn,
        strip_state_dict_prefixes=model_utils.strip_state_dict_prefixes,
    )
    verify_runtime_versions(modules)
    return modules


def verify_runtime_versions(modules: RuntimeModules) -> None:
    """Require the audited export versions rather than silently drifting."""

    expected = {
        "torch": EXPECTED_TORCH_VERSION,
        "onnx": EXPECTED_ONNX_VERSION,
        "numpy": EXPECTED_NUMPY_VERSION,
    }
    actual = {
        "torch": str(modules.torch.__version__),
        "onnx": str(modules.onnx.__version__),
        "numpy": str(modules.numpy.__version__),
    }
    mismatches = [
        f"{name}: expected {expected[name]}, got {actual[name]}"
        for name in expected
        if actual[name] != expected[name]
    ]
    if mismatches:
        raise ExportError(
            "export dependency version mismatch; " + "; ".join(mismatches)
        )


def _extract_state_dict(payload: Any) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ExportError(
            f"checkpoint payload must be a mapping, got {type(payload).__name__}"
        )
    state = payload.get("model_state_dict", payload)
    if not isinstance(state, Mapping):
        raise ExportError(
            "checkpoint model_state_dict must be a mapping, got "
            f"{type(state).__name__}"
        )
    non_string_keys = [key for key in state if not isinstance(key, str)]
    if non_string_keys:
        raise ExportError("checkpoint state_dict contains non-string keys")
    return state


def load_reference_model(modules: RuntimeModules, checkpoint: Path, seed: int) -> Any:
    """Build the exact audited model and load every state entry strictly."""

    torch = modules.torch
    torch.manual_seed(seed)
    model = modules.create_model(
        variant="base",
        global_mode="balanced",
        upsample_unfold=True,
    ).cpu().eval()
    payload = torch.load(
        str(checkpoint),
        map_location="cpu",
        weights_only=True,
    )
    state = modules.strip_state_dict_prefixes(dict(_extract_state_dict(payload)))
    require_exact_state_keys(model.state_dict().keys(), state.keys())
    model.load_state_dict(state, strict=True)
    return model.eval()


def require_faithful_global_context(model: Any) -> int:
    """Ensure learned GlobalContext modules exist and were not monkey-patched."""

    contexts = [
        module
        for module in model.modules()
        if type(module).__name__ == "GlobalContextBlock"
    ]
    if not contexts:
        raise ExportError("balanced/base model has no GlobalContextBlock")
    for module in contexts:
        if not hasattr(module, "context_weight"):
            raise ExportError("GlobalContextBlock lost learned context_weight")
        if "forward" in vars(module):
            raise ExportError(
                "GlobalContextBlock.forward is instance-patched; refusing altered export"
            )
    return len(contexts)


def prepare_models(
    modules: RuntimeModules, reference_model: Any
) -> tuple[Any, Any, int, int]:
    """Create fused and export copies without altering model semantics."""

    fused = copy.deepcopy(reference_model).cpu().eval()
    fused.fuse_for_inference()
    remaining_fusions = int(modules.fuse_remaining_conv_bn(fused))
    context_count = require_faithful_global_context(fused)

    export_model = copy.deepcopy(fused).cpu().eval()
    require_faithful_global_context(export_model)
    return fused, export_model, remaining_fusions, context_count


def deterministic_test_input(
    torch: Any, height: int, width: int, seed: int
) -> Any:
    """Create the reproducible, static, batch-one export input."""

    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    return torch.rand(
        (1, 3, height, width),
        generator=generator,
        dtype=torch.float32,
        device="cpu",
    )


def tensor_sha256(tensor: Any) -> str:
    data = tensor.detach().cpu().contiguous().numpy().tobytes(order="C")
    return hashlib.sha256(data).hexdigest()


def tensor_summary(torch: Any, tensor: Any) -> dict[str, Any]:
    detached = tensor.detach().cpu()
    return {
        "shape": list(detached.shape),
        "dtype": str(detached.dtype),
        "finite": bool(torch.isfinite(detached).all().item()),
        "min": float(detached.min().item()),
        "max": float(detached.max().item()),
        "mean": float(detached.mean().item()),
        "sha256": tensor_sha256(detached),
    }


def require_valid_depth_output(
    torch: Any, output: Any, height: int, width: int, label: str
) -> None:
    expected_shape = (1, 1, height, width)
    if tuple(output.shape) != expected_shape:
        raise ExportError(
            f"{label} shape mismatch: expected {expected_shape}, got {tuple(output.shape)}"
        )
    if not bool(torch.isfinite(output).all().item()):
        raise ExportError(f"{label} contains NaN or infinite values")
    minimum = float(output.min().item())
    if minimum < 0.0:
        raise ExportError(f"{label} contains negative inverse depth: min={minimum}")


def comparison_metrics(torch: Any, expected: Any, actual: Any) -> dict[str, Any]:
    difference = (actual - expected).abs()
    denominator = expected.abs().clamp_min(1.0e-12)
    return {
        "allclose": False,
        "max_abs": float(difference.max().item()),
        "mean_abs": float(difference.mean().item()),
        "max_relative_away_from_zero": float(
            (difference / denominator).max().item()
        ),
        "expected_sha256": tensor_sha256(expected),
        "actual_sha256": tensor_sha256(actual),
    }


def require_close(
    torch: Any,
    expected: Any,
    actual: Any,
    *,
    label: str,
    rtol: float,
    atol: float,
) -> dict[str, Any]:
    metrics = comparison_metrics(torch, expected, actual)
    metrics["rtol"] = rtol
    metrics["atol"] = atol
    metrics["allclose"] = bool(
        torch.allclose(expected, actual, rtol=rtol, atol=atol)
    )
    if not metrics["allclose"]:
        raise ExportError(
            f"{label} parity failed: max_abs={metrics['max_abs']:.9g}, "
            f"mean_abs={metrics['mean_abs']:.9g}, rtol={rtol}, atol={atol}"
        )
    return metrics


def run_pre_export_parity(
    modules: RuntimeModules,
    reference_model: Any,
    fused_model: Any,
    export_model: Any,
    test_input: Any,
    *,
    height: int,
    width: int,
    rtol: float,
    atol: float,
) -> tuple[dict[str, Any], Any]:
    torch = modules.torch
    with torch.inference_mode():
        reference_output = reference_model(test_input)
        fused_output = fused_model(test_input)
        export_output = export_model(test_input)

    for label, output in (
        ("reference output", reference_output),
        ("fused output", fused_output),
        ("export-prepared output", export_output),
    ):
        require_valid_depth_output(torch, output, height, width, label)

    parity = {
        "reference_vs_fused": require_close(
            torch,
            reference_output,
            fused_output,
            label="reference-vs-fused",
            rtol=rtol,
            atol=atol,
        ),
        "fused_vs_export_prepared": require_close(
            torch,
            fused_output,
            export_output,
            label="fused-vs-export-prepared",
            rtol=rtol,
            atol=atol,
        ),
        "reference_output": tensor_summary(torch, reference_output),
        "fused_output": tensor_summary(torch, fused_output),
        "export_prepared_output": tensor_summary(torch, export_output),
    }
    return parity, export_output.detach().clone()


def export_static_onnx(
    modules: RuntimeModules, model: Any, test_input: Any, destination: Path
) -> None:
    """Export faithfully with fixed shapes, opset 17, and the legacy exporter."""

    torch = modules.torch
    with torch.inference_mode():
        torch.onnx.export(
            model,
            (test_input,),
            str(destination),
            export_params=True,
            opset_version=ONNX_OPSET,
            do_constant_folding=True,
            input_names=["image"],
            output_names=["depth"],
            keep_initializers_as_inputs=False,
            dynamo=False,
        )


def _onnx_domain(domain: str) -> str:
    return domain or "ai.onnx"


def count_onnx_operators(nodes: Iterable[Any]) -> dict[str, int]:
    """Return a stable domain-qualified ONNX operator histogram."""

    counts = Counter(
        f"{_onnx_domain(getattr(node, 'domain', ''))}::{node.op_type}"
        for node in nodes
    )
    return dict(sorted(counts.items()))


def _value_info_shape(value_info: Any) -> list[int]:
    tensor_type = value_info.type.tensor_type
    dimensions: list[int] = []
    for dimension in tensor_type.shape.dim:
        if not dimension.HasField("dim_value"):
            raise ExportError(
                f"ONNX value {value_info.name!r} is not static: {dimension}"
            )
        dimensions.append(int(dimension.dim_value))
    return dimensions


def inspect_and_rewrite_checked_onnx(
    modules: RuntimeModules, path: Path, height: int, width: int
) -> dict[str, Any]:
    """Check, infer shapes, reject custom domains, and save the checked graph."""

    onnx = modules.onnx
    model = onnx.load_model(str(path), load_external_data=True)
    onnx.checker.check_model(model, full_check=True)
    inferred = onnx.shape_inference.infer_shapes(
        model,
        check_type=True,
        strict_mode=True,
        data_prop=True,
    )
    onnx.checker.check_model(inferred, full_check=True)

    opsets = {
        _onnx_domain(item.domain): int(item.version)
        for item in inferred.opset_import
    }
    if opsets.get("ai.onnx") != ONNX_OPSET:
        raise ExportError(
            f"ONNX opset mismatch: expected ai.onnx={ONNX_OPSET}, got {opsets}"
        )
    custom_opsets = sorted(domain for domain in opsets if domain != "ai.onnx")
    custom_nodes = sorted(
        {
            _onnx_domain(node.domain)
            for node in inferred.graph.node
            if _onnx_domain(node.domain) != "ai.onnx"
        }
    )
    if custom_opsets or custom_nodes:
        raise ExportError(
            "ONNX graph contains custom domains: "
            f"opsets={custom_opsets}, nodes={custom_nodes}"
        )
    if any(
        initializer.data_location == onnx.TensorProto.EXTERNAL
        for initializer in inferred.graph.initializer
    ):
        raise ExportError("ONNX graph unexpectedly uses external tensor data")

    inputs = list(inferred.graph.input)
    outputs = list(inferred.graph.output)
    if len(inputs) != 1 or inputs[0].name != "image":
        raise ExportError(
            f"expected one ONNX input named 'image', got {[item.name for item in inputs]}"
        )
    if len(outputs) != 1 or outputs[0].name != "depth":
        raise ExportError(
            f"expected one ONNX output named 'depth', got {[item.name for item in outputs]}"
        )

    input_shape = _value_info_shape(inputs[0])
    output_shape = _value_info_shape(outputs[0])
    expected_input = [1, 3, height, width]
    expected_output = [1, 1, height, width]
    if input_shape != expected_input:
        raise ExportError(
            f"ONNX input shape mismatch: expected {expected_input}, got {input_shape}"
        )
    if output_shape != expected_output:
        raise ExportError(
            f"ONNX output shape mismatch: expected {expected_output}, got {output_shape}"
        )
    if inputs[0].type.tensor_type.elem_type != onnx.TensorProto.FLOAT:
        raise ExportError("ONNX image input is not FP32")
    if outputs[0].type.tensor_type.elem_type != onnx.TensorProto.FLOAT:
        raise ExportError("ONNX depth output is not FP32")

    onnx.save_model(inferred, str(path), save_as_external_data=False)
    return {
        "ir_version": int(inferred.ir_version),
        "producer_name": inferred.producer_name,
        "producer_version": inferred.producer_version,
        "opset_imports": dict(sorted(opsets.items())),
        "operator_histogram": count_onnx_operators(inferred.graph.node),
        "node_count": len(inferred.graph.node),
        "initializer_count": len(inferred.graph.initializer),
        "input": {
            "name": inputs[0].name,
            "shape": input_shape,
            "element_type": "float32",
        },
        "output": {
            "name": outputs[0].name,
            "shape": output_shape,
            "element_type": "float32",
        },
    }


def _temporary_path_for(target: Path, suffix: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=suffix, dir=target.parent
    )
    os.close(descriptor)
    return Path(name)


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = _temporary_path_for(path, ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_l4t_release() -> str | None:
    release = Path("/etc/nv_tegra_release")
    if not release.is_file():
        return None
    return release.read_text(encoding="utf-8", errors="replace").strip()


def make_manifest(
    *,
    args: argparse.Namespace,
    paths: ArtifactPaths,
    source: SourceVerification,
    modules: RuntimeModules,
    checkpoint_sha256: str,
    onnx_path: Path,
    onnx_details: Mapping[str, Any],
    test_input: Any,
    parity: Mapping[str, Any],
    remaining_fusions: int,
    global_context_count: int,
) -> dict[str, Any]:
    exporter = Path(__file__).resolve()
    return {
        "schema": MANIFEST_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "faithful static ZipDepth ONNX export for local TensorRT build",
        "source": {
            "upstream_url": EXPECTED_SOURCE_URL,
            "checkout": str(source.root),
            "commit": source.commit,
            "origin": source.origin,
            "tracked_worktree_clean": True,
        },
        "checkpoint": {
            "path": str(paths.checkpoint),
            "size_bytes": paths.checkpoint.stat().st_size,
            "sha256": checkpoint_sha256,
            "load_mode": "torch.load(weights_only=True, map_location='cpu')",
            "state_keys": "exact/strict",
        },
        "model": {
            "variant": "base",
            "global_mode": "balanced",
            "upsample_unfold": True,
            "batch": 1,
            "height": args.height,
            "width": args.width,
            "global_context_blocks_verified_faithful": global_context_count,
            "remaining_conv_bn_fusions": remaining_fusions,
        },
        "export": {
            "format": "ONNX",
            "opset": ONNX_OPSET,
            "dynamo": False,
            "static_shapes": True,
            "onnxsim": False,
            "constant_folding": True,
            "input_range": "RGB float32 NCHW in [0,1]; model performs mean/std normalization",
        },
        "deterministic_test": {
            "seed": args.seed,
            "input_shape": list(test_input.shape),
            "input_dtype": str(test_input.dtype),
            "input_sha256": tensor_sha256(test_input),
            "rtol": args.rtol,
            "atol": args.atol,
            "parity": parity,
        },
        "onnx": {
            "path": str(paths.output),
            "size_bytes": onnx_path.stat().st_size,
            "sha256": sha256_file(onnx_path),
            **dict(onnx_details),
        },
        "exporter": {
            "path": str(exporter),
            "sha256": sha256_file(exporter),
            "invocation": shlex.join(sys.argv),
            "working_directory": str(Path.cwd()),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "torch": str(modules.torch.__version__),
            "onnx": str(modules.onnx.__version__),
            "numpy": str(modules.numpy.__version__),
            "l4t_release": _read_l4t_release(),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="default: SOURCE_ROOT/checkpoints/zipdepth_base.pth",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="default: SOURCE_ROOT/../engines/zipdepth_base_b1_HEIGHTxWIDTH_op17.onnx",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="default: OUTPUT with .manifest.json suffix",
    )
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--rtol",
        type=float,
        default=1.0e-4,
        help="relative tolerance for unfused/fused PyTorch parity",
    )
    parser.add_argument(
        "--atol",
        type=float,
        default=1.0e-4,
        help="absolute tolerance for unfused/fused PyTorch parity",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="atomically replace existing ONNX/manifest outputs",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    validate_dimensions(args.height, args.width)
    if args.seed < 0:
        raise ExportError(f"seed must be non-negative, got {args.seed}")
    for name, value in (("rtol", args.rtol), ("atol", args.atol)):
        if value < 0.0:
            raise ExportError(f"{name} must be non-negative, got {value}")


def run_export(args: argparse.Namespace) -> tuple[Path, Path]:
    validate_args(args)
    paths = resolve_artifact_paths(args)

    print(f"[1/8] verifying pinned source: {paths.source_root}", flush=True)
    source = verify_source_checkout(paths.source_root)
    checkpoint_sha256 = verify_file_sha256(
        paths.checkpoint,
        EXPECTED_CHECKPOINT_SHA256,
        "ZipDepth GPU checkpoint",
    )

    print("[2/8] importing CPU export dependencies and pinned architecture", flush=True)
    modules = load_runtime_modules(paths.source_root)

    print("[3/8] loading checkpoint with exact state keys", flush=True)
    reference_model = load_reference_model(modules, paths.checkpoint, args.seed)
    fused_model, export_model, remaining_fusions, context_count = prepare_models(
        modules, reference_model
    )

    print("[4/8] running deterministic faithful PyTorch parity", flush=True)
    test_input = deterministic_test_input(
        modules.torch, args.height, args.width, args.seed
    )
    parity, prepared_output = run_pre_export_parity(
        modules,
        reference_model,
        fused_model,
        export_model,
        test_input,
        height=args.height,
        width=args.width,
        rtol=args.rtol,
        atol=args.atol,
    )

    paths.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_onnx = _temporary_path_for(paths.output, ".onnx")
    try:
        print("[5/8] exporting static opset-17 ONNX with dynamo=False", flush=True)
        export_static_onnx(modules, export_model, test_input, temporary_onnx)

        print("[6/8] checking ONNX, inferring static shapes, auditing operators", flush=True)
        onnx_details = inspect_and_rewrite_checked_onnx(
            modules, temporary_onnx, args.height, args.width
        )

        with modules.torch.inference_mode():
            post_export_output = export_model(test_input)
        require_valid_depth_output(
            modules.torch,
            post_export_output,
            args.height,
            args.width,
            "post-export PyTorch output",
        )
        parity["export_prepared_before_vs_after_torch_onnx_export"] = require_close(
            modules.torch,
            prepared_output,
            post_export_output,
            label="export-prepared-before-vs-after-torch-onnx-export",
            rtol=args.rtol,
            atol=args.atol,
        )

        print("[7/8] re-verifying source and staging provenance manifest", flush=True)
        source_after = verify_source_checkout(paths.source_root)
        if source_after.commit != source.commit:
            raise ExportError("source commit changed during export")
        manifest = make_manifest(
            args=args,
            paths=paths,
            source=source_after,
            modules=modules,
            checkpoint_sha256=checkpoint_sha256,
            onnx_path=temporary_onnx,
            onnx_details=onnx_details,
            test_input=test_input,
            parity=parity,
            remaining_fusions=remaining_fusions,
            global_context_count=context_count,
        )

        print("[8/8] publishing checked ONNX and manifest", flush=True)
        os.replace(temporary_onnx, paths.output)
        atomic_write_json(paths.manifest, manifest)
    finally:
        temporary_onnx.unlink(missing_ok=True)

    print(f"ONNX_READY path={paths.output} sha256={sha256_file(paths.output)}")
    print(f"MANIFEST_READY path={paths.manifest} sha256={sha256_file(paths.manifest)}")
    return paths.output, paths.manifest


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_export(args)
    except ExportError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
