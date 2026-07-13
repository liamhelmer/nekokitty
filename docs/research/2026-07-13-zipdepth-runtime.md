# ZipDepth Jetson runtime assessment — 2026-07-13

> Provisioning update later on 2026-07-13: the hash-locked CPU export
> environment was installed, the project faithful exporter passed 11 tests and a
> real deterministic export, and TensorRT 10.16.2 built both FP32/no-TF32 and FP16
> plans on this Orin. The FP16 plan averaged 8.733 ms model-only and 9.101 ms with
> synthetic transfers across three 30-second runs. Exact deterministic
> PyTorch/FP32/FP16 numerical gates also pass. Real-camera scene quality,
> preprocessing, and combined-workload evaluation remain open. See
> `2026-07-13-local-benchmarks.md` and `../operations/setup-log.md` for the exact
> artifact hashes, build times, resource observations, and rollback.

## Decision summary

ZipDepth is likely straightforward to run as a fixed-shape TensorRT FP16 engine
on this Jetson, but the current upstream ONNX export must **not** yet be treated
as numerically faithful. Static inspection found that the exporter replaces the
model's learned spatial-attention pooling with an unweighted average and never
compares that altered model to the original. The paper supplement says the
TensorRT path needs no graph surgery, which conflicts with the checked-in export
implementation.

The lowest-risk path is therefore:

1. Use a small, isolated, CPU-only PyTorch environment for checkpoint loading
   and ONNX export. Do not install a GPU PyTorch stack on the Jetson merely to
   export this 27 MB checkpoint.
2. Export a **faithful**, batch-one, fixed-shape graph without the upstream
   attention rewrite. Explicitly select PyTorch's legacy/static ONNX exporter so
   its behavior is not changed by PyTorch 2.12's new default exporter.
3. Check and compare that graph against the original fused PyTorch model before
   building both a diagnostic FP32 engine and the production-candidate FP16
   engine with native TensorRT 10.16.2.10.
4. Standardize each deployed camera feed to `1x3x384x672`; add a separate
   `384x384` engine only if a square crop is genuinely needed. Do not begin with
   a dynamic-shape engine.
5. Keep the output at model resolution on the GPU and reduce it to per-track
   relative statistics. Do not upsample every frame to camera resolution, copy a
   full depth image to the CPU, colorize it, or write it to disk in production.

No ZipDepth code or checkpoint was executed during this assessment. No package,
ONNX file, TensorRT engine, service, or system configuration was added. The only
project change is this memo.

## Scope and evidence labels

The sections below deliberately distinguish three evidence classes:

- **Host verified**: observed locally with read-only commands on 2026-07-13.
- **Source verified**: established by static inspection of the pinned source,
  checkpoint container strings, official documentation, or an upstream release.
- **Recommendation / inference**: a proposed action that still needs a measured
  local test.

"Operator supported" does not mean "this exact exported graph has parsed, built,
and matched numerically." That claim can be made only after the acceptance tests
in this memo pass.

## Host-verified runtime baseline

The board is a Jetson Orin Nano 8 GB on JetPack 7.2 / L4T R39.2.0, Ubuntu
24.04/aarch64. The following versions were observed after the owner's approved
CUDA/TensorRT package installation:

| Component | Local version/status |
| --- | --- |
| L4T | `39.2.0-20260601141651` |
| CUDA compiler | 13.2, `nvcc` 13.2.78 |
| CUDA runtime development package | `cuda-cudart-dev-13-2` 13.2.75-1 |
| cuBLAS development package | `libcublas-dev-13-2` 13.4.0.1-1 |
| TensorRT | `tensorrt` 10.16.2.10-1+cuda13.2 |
| TensorRT Python binding | `python3-libnvinfer` 10.16.2.10; import reports `10.16.2.10` |
| TensorRT CLI | `/usr/bin/trtexec` |
| System Python | 3.12 |
| PyTorch / ONNX | not installed in system Python |

The NVIDIA R39.2 repositories, rather than a generic desktop CUDA repository,
supplied TensorRT. TensorRT's current 10.x support matrix identifies CUDA 13.2
builds and Orin iGPU support. The engine must still be built on this board and
rebuilt after a material TensorRT/CUDA/BSP change.

Relevant primary sources:

- JetPack 7.2 identifies itself as L4T R39.2:
  <https://docs.nvidia.com/jetson/agx-orin-devkit/user-guide/latest/setup_jetpack.html>
- TensorRT 10.x support and engine portability:
  <https://docs.nvidia.com/deeplearning/tensorrt/10.x.x/getting-started/support-matrix.html>
- TensorRT 10.16 release notes:
  <https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/release-notes-10/10.16.0.html>

## Upstream source and artifact state

### Source verified

- Pinned checkout:
  `/home/neko/models/ZipDepth/a302e5437bc58f15c4efd41d3e8222bf24f7d470`
- Commit: `a302e5437bc58f15c4efd41d3e8222bf24f7d470`.
- The same commit remained upstream `main`/`HEAD` when checked on 2026-07-13.
- Upstream had no issue or pull-request records at that check. This is a very
  young project, so absence of reports is not maturity evidence.
- GPU checkpoint:
  `checkpoints/zipdepth_base.pth`, 27,298,978 bytes,
  SHA-256 `a55910bb0b99c8c5e641cb9206e810b269690ad94e8a2ef08c827c4679391a65`.
- NPU checkpoint:
  `checkpoints/zipdepth_base_npu.pth`, 27,295,474 bytes,
  SHA-256 `627c04fda584133ead4310074884a4a037061b4c01ba86e73e492ea30fab570d`.

Commit permalink:
<https://github.com/fabiotosi92/ZipDepth/tree/a302e5437bc58f15c4efd41d3e8222bf24f7d470>

The GPU checkpoint is the first TensorRT candidate. It uses unfold plus
PixelShuffle for convex upsampling and is the path for which the authors report
TensorRT results. The NPU checkpoint should be evaluated only if that path proves
problematic; it is not automatically a better Jetson GPU model.

### Model role remains constrained

ZipDepth produces positive affine-invariant inverse depth, not metres. Three
monocular camera views make this limitation more important: scale and shift can
vary between cameras and frames, so raw outputs cannot be compared across the
three views to decide which person is physically closest. The model may provide
relative structure or a secondary within-frame cue, but greeting distance and
safety require metric sensors/tracks.

## PyTorch and ONNX compatibility decision

### What is officially available now

**Source verified:** NVIDIA's PyTorch-for-Jetson matrix, updated 2026-07-09,
currently lists framework containers through 26.06 but no standalone framework
wheel for the recent JetPack entries. Its newest table rows are validated for
JetPack 7.1, not 7.2. The regular NVIDIA PyTorch 26.06 container is multi-arch but
is approximately 10.19 GB compressed and contains far more than this export job
needs.

- NVIDIA Jetson PyTorch matrix:
  <https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform-release-notes/pytorch-jetson-rel.html>
- NVIDIA PyTorch container:
  <https://catalog.ngc.nvidia.com/orgs/nvidia/containers/pytorch>

Upstream PyTorch 2.12.1 publishes a CUDA 13.2 aarch64 wheel, but the PyTorch
2.12 release support matrix lists the aarch64 Ampere target as `8.0`, not Jetson
Orin's `8.7`. A current JetPack 7.2 report shows that wheel explicitly warning
that `8.7` is excluded. It should not be selected for ZipDepth GPU inference
without a separate upstream/NVIDIA resolution and a local kernel test.

- PyTorch release support matrix:
  <https://github.com/pytorch/pytorch/blob/v2.12.1/RELEASE.md#pytorch-cuda-support-matrix>
- CUDA 13.2 aarch64/Jetson enablement tracker:
  <https://github.com/pytorch/pytorch/issues/177067>
- Current JetPack 7.2 `sm_87` report:
  <https://forums.developer.nvidia.com/t/how-do-i-correctly-install-pytorch-on-jetpack-7-2/372773>

### Recommended exact export environment

**Recommendation:** use PyTorch on CPU only, solely for export and numerical
reference. The source's `scripts/export.py` explicitly exports on CPU, and this
avoids every Jetson CUDA-PyTorch compatibility question.

Pin these direct packages in a dedicated uv environment under the model cache,
not in system Python and not in the boot service environment:

| Package | Exact artifact/reason | SHA-256 of aarch64 wheel |
| --- | --- | --- |
| `torch==2.12.1+cpu` | Stable patch release matching ZipDepth's `torch>=2.12.0`; CPython 3.12, manylinux 2.28 aarch64 | `d1620bc7bcf8087f3e48821b5db994a03e32ddb083d58c000b8e032f8a6e2d15` |
| `onnx==1.18.0` | Exact ONNX release named by the TensorRT 10.16 parser project; CPython 3.12 aarch64 | `e4da451bf1c5ae381f32d430004a89f0405bc57a8471b0bddb6325a5b334aa40` |
| `numpy==1.26.2` | Exact NumPy pin used by PyTorch 2.12.1 CI for Python 3.12; sufficient for export | `6a3cdb4d9c70e6b8c0814239ead47da00934666f668426fc6e94cce869e13fd7` |

Official CPU wheel URL:

```text
https://download-r2.pytorch.org/whl/cpu/torch-2.12.1%2Bcpu-cp312-cp312-manylinux_2_28_aarch64.whl#sha256=d1620bc7bcf8087f3e48821b5db994a03e32ddb083d58c000b8e032f8a6e2d15
```

Primary package evidence:

- PyTorch 2.12.1 install index:
  <https://pytorch.org/get-started/previous-versions/#v2121>
- PyTorch 2.12.1 CI pins:
  <https://github.com/pytorch/pytorch/blob/v2.12.1/.ci/docker/requirements-ci.txt>
- ONNX-TensorRT 10.16 says to use ONNX 1.18.0:
  <https://github.com/onnx/onnx-tensorrt/tree/10.16-GA#python-modules>
- ONNX 1.18.0 release files:
  <https://pypi.org/project/onnx/1.18.0/>

This NumPy version intentionally differs from ZipDepth's broad full-training
requirement (`numpy>=2.0`). The export-only path imports the architecture and
PyTorch exporter, not the OpenCV/NumPy inference pipeline; PyTorch's own Python
3.12 CI pin is the more conservative compatibility point. Do not reuse this
environment as the production camera runtime.

Do **not** install the repository's complete `requirements.txt` for export.
Static search found no `torchvision` import anywhere in the Python source, and
training, augmentation, plotting, TensorBoard, OpenCV, TurboJPEG, and HDF5 are
unnecessary. Do not install `onnxsim` initially: TensorRT performs its own graph
optimization, and every additional rewrite complicates numerical provenance.
Do not install ONNX Runtime merely to build a TensorRT engine.

An eventual install should use the direct hashed torch wheel, binary-only PyPI
wheels for ONNX/NumPy, and a generated uv lock containing every transitive hash.
Those commands are intentionally left as a provisioning step because no packages
were installed in this assessment.

## Static export audit

### Verified upstream behavior

The export implementation is here:
<https://github.com/fabiotosi92/ZipDepth/blob/a302e5437bc58f15c4efd41d3e8222bf24f7d470/scripts/export.py>

It does several useful things:

- loads with `torch.load(..., weights_only=True)`;
- constructs the matching base architecture;
- calls `fuse_for_inference()` and performs additional Conv-BN fusion;
- exports on CPU, batch one, static height and width, ONNX opset 17;
- names the input `image` and output `depth`;
- makes no dynamic-axes declaration.

It also has deployment hazards:

1. `load_state_dict(..., strict=False)` only prints missing keys and continues.
   The inference helper likewise warns that missing keys remain randomly
   initialized. A deployment exporter must fail unless missing/unexpected keys
   are empty or match a narrow, documented allowlist.
2. The script does not explicitly choose an ONNX exporter. PyTorch changed
   `torch.onnx.export` to `dynamo=True` by default in 2.9 and removed its fallback
   option in 2.11. The script predates that behavioral pin, so the same ZipDepth
   command can produce a different graph as PyTorch changes.
3. With the current new exporter, ONNX Script is an extra dependency, but
   ZipDepth lists only `onnx`/`onnxsim` as optional export dependencies.
4. The script mutates model methods before export and performs only an output
   **shape** check. It never compares values to the original fused model.
5. The optional simplifier catches only `ImportError`; other simplifier failures
   abort rather than preserving the already-generated graph.

PyTorch's current exporter behavior is documented at:
<https://docs.pytorch.org/docs/2.12/onnx.html#torch.onnx.export>.

### The non-equivalent GlobalContext rewrite

**Source verified:** the original `GlobalContextBlock` computes a learned
spatial weighting:

```text
context_weight(x) -> softmax over H*W -> weighted bmm with x -> transform
```

The export script replaces that with a uniform full-map average followed by the
transform. It never calls `context_weight`; the checkpoint demonstrably contains
`encoder.stage3.7.context_weight.weight` and `.bias`. This is a model change, not
an ONNX spelling change.

The other two exporter rewrites appear equivalent only for the intended static,
multiple-of-32 geometry:

- strip means become equivalent adaptive-average pools;
- cross-scale resize/pool targets become constants at `H/16 x W/16` and 2x
  downsampling.

The learned-context rewrite is the blocker. It also conflicts with the
supplement's statement that ZipDepth uses natively supported operators and needs
no graph surgery or custom plugins:
<https://zipdepth.github.io/static/pdfs/zipdepth_supplementary.pdf>.

### TensorRT operator feasibility

**Source verified:** the original balanced/base architecture is composed of
convolutions, normalization fused into convolutions, activations, pooling,
elementwise operations, reductions, reshape/transpose, softmax, matrix multiply,
resize, pad, unfold decomposition, and DepthToSpace/PixelShuffle-style
rearrangement. TensorRT 10.16's ONNX parser matrix supports the relevant ONNX
operators, including `Pad`, `Range`, `Gather`, `Resize`, `MatMul`, `Softmax`, and
`DepthToSpace`. Its parser maps ONNX `Pad(mode="edge")`, the likely export of
PyTorch replicate padding, to clamp sampling.

- TensorRT 10.16 parser operator matrix:
  <https://github.com/onnx/onnx-tensorrt/blob/10.16-GA/docs/operators.md>
- Exact 10.16 parser source for operator semantics:
  <https://github.com/onnx/onnx-tensorrt/blob/10.16-GA/onnxOpImporters.cpp>

**Inference, not yet a result:** a faithful static opset-17 graph is therefore
likely to parse without a custom plugin. It still must be exported and submitted
to this exact local parser before the project says it "exports cleanly."

## Required export behavior

### Recommendation

Create a project-owned exporter or a recorded patch against the pinned source;
do not silently edit the model-cache checkout. It should:

1. Verify the source commit and checkpoint SHA-256 before import.
2. Construct `base`, `balanced`, `upsample_unfold=True`.
3. Load with `weights_only=True` and fail closed on key mismatches.
4. Preserve a deep-copied, fused FP32 reference model before any export-specific
   mutation.
5. Attempt the original, faithful forward graph first; do **not** replace
   `GlobalContextBlock`.
6. Call `torch.onnx.export(..., opset_version=17, dynamo=False)` explicitly.
   This matches the static/tracing style of the upstream script and needs only
   ONNX, not ONNX Script.
7. Export without `onnxsim` and run `onnx.checker.check_model` plus ONNX shape
   inference.
8. Record graph IR/opset, input/output names/shapes/types, operator histogram,
   file size, and SHA-256.
9. If the faithful graph fails, preserve the complete error and minimize the
   unsupported operation. Only then test a local, narrowly-scoped equivalent
   lowering. Do not fall back to the non-equivalent average-pool rewrite without
   a quality study.

Export two candidates only if the deployed image geometry needs both:

```text
batch 1, RGB, FP32 input in [0,1], 3x384x672 -> depth 1x384x672
batch 1, RGB, FP32 input in [0,1], 3x384x384 -> depth 1x384x384
```

The model graph itself performs ImageNet mean/std normalization. The runtime
must not normalize twice.

## Fixed shape versus dynamic shape

### Source verified

- Upstream exports static shapes only.
- The published TensorRT result uses a static FP16 engine.
- Upstream preprocessing scales the shorter side to 384 and rounds each
  dimension to the nearest multiple of 32. A 16:9 frame becomes `384x672`.
- Model downsampling and convex upsampling assume coherent dimensions through
  factors of 2; multiple-of-32 inputs are the supported operating envelope.
- The export code bakes `H/16`, `W/16`, and cross-scale sizes into Python method
  closures. Adding a TensorRT optimization profile does not make that graph
  genuinely dynamic.

### Recommendation

Use fixed `384x672`, batch one, for all three wide cameras and time-multiplex the
same engine. Fixed shape gives TensorRT the best tactic selection, enables CUDA
graph capture, bounds memory, and prevents invalid profile shapes. A separate
square engine is preferable to a broad dynamic profile if square imagery is
actually required.

Do not build batch three first. Three synchronized full-frame depth maps are not
needed for social behavior, while batch one makes it easier to schedule brief
GPU slices around ASR/TTS/LLM work. Start by measuring an aggregate perception
rate of 5–10 Hz and allocate frames across cameras according to active tracks.

A future dynamic exporter would need real source work: preserve symbolic spatial
dimensions, remove fixed closure sizes, express dynamic shapes through the
PyTorch exporter, restrict every TensorRT profile dimension to multiples of 32,
and test every min/opt/max combination. That complexity offers little benefit
until camera geometry is final.

## TensorRT build plan

### Diagnostic engine first

Build on this Jetson, never on a different GPU. Stop memory-heavy model workers
during engine construction. First build an FP32/TF32-disabled diagnostic engine
to isolate export correctness; then build FP16.

Illustrative commands, to be executed only after a checked ONNX artifact exists:

```bash
/usr/bin/trtexec \
  --onnx=/home/neko/models/ZipDepth/engines/zipdepth_base_b1_384x672_op17.onnx \
  --saveEngine=/home/neko/models/ZipDepth/engines/zipdepth_base_trt10.16.2_sm87_b1_384x672_fp32.plan \
  --noTF32 \
  --builderOptimizationLevel=5 \
  --memPoolSize=workspace:512M \
  --maxAuxStreams=0 \
  --timingCacheFile=/home/neko/models/ZipDepth/engines/trt10.16.2_sm87_384x672.timing \
  --skipInference
```

```bash
/usr/bin/trtexec \
  --onnx=/home/neko/models/ZipDepth/engines/zipdepth_base_b1_384x672_op17.onnx \
  --saveEngine=/home/neko/models/ZipDepth/engines/zipdepth_base_trt10.16.2_sm87_b1_384x672_fp16.plan \
  --fp16 \
  --builderOptimizationLevel=5 \
  --memPoolSize=workspace:512M \
  --maxAuxStreams=0 \
  --timingCacheFile=/home/neko/models/ZipDepth/engines/trt10.16.2_sm87_384x672.timing \
  --skipInference
```

`--fp16` is deprecated in TensorRT 10.16 in favor of newer strong-typing and
autocast workflows, but remains supported. The newer TensorRT Model Optimizer
route is not currently supported on Jetson according to NVIDIA's Jetson PyTorch
release notes. Starting with the simple weakly-typed FP16 build is therefore the
reproducible path for this unquantized FP32 ONNX graph. Do not use INT8 until a
representative calibration and accuracy protocol exists.

Use `--maxAuxStreams=0` initially to bound unified-memory use. Increase workspace
or auxiliary streams only if layer/tactic logs show a measured benefit. Preserve
the builder log, ONNX hash, engine hash, timing-cache hash, exact CLI, and peak
build memory. An engine filename is metadata, not a substitute for a manifest.

## Numerical acceptance plan

No engine should be called valid merely because `trtexec` builds it.

1. Generate a deterministic FP32 test tensor and preprocess several local test
   images exactly once to RGB `[0,1]`, NCHW.
2. Save original fused PyTorch outputs before export-specific mutation.
3. Run the faithful ONNX graph through ONNX's reference evaluator if practical,
   and always run the local TensorRT diagnostic FP32 engine on the same tensors.
4. Compare shape, finiteness, min/max, mean absolute error, maximum absolute
   error, relative error away from zero, cosine similarity, and per-image rank
   correlation. Also compare scale/shift-aligned depth because that matches the
   model's published evaluation protocol.
5. Repeat against FP16. Choose tolerances from the observed FP32 baseline rather
   than hiding a structural mismatch behind a loose FP16 tolerance.
6. Separately run the upstream mutated exporter and compare it to the original.
   This quantifies the learned-context rewrite instead of assuming it is benign.
7. Visually inspect local-only depth on thin structures, people at multiple
   ranges, glare, low light, and overlapping subjects. Never upload test imagery
   without the owner's human-in-the-loop consent.

Initial engineering gates, subject to tightening after the diagnostic run:

- no missing/unexpected checkpoint keys;
- ONNX checker and TensorRT parser return no errors or custom/plugin nodes;
- all outputs are finite, non-negative, and correctly shaped;
- diagnostic FP32 has no unexplained structural difference from PyTorch;
- FP16 preserves person ordering and scene boundaries on the curated local set;
- the faithful export is preferred over the upstream approximate export unless
  the latter has a documented, accepted quality delta.

## Performance benchmark plan

### Model-only matrix

Benchmark both `384x384` and `384x672` only if both are candidates. For each,
measure FP32 diagnostic and FP16 production engines with:

- batch one, one inference stream;
- 2 seconds warm-up, at least 30 seconds measurement, three independent runs;
- model-only with `--noDataTransfers` and end-to-end bindings with transfers;
- CUDA Graph on and off;
- p50, p90, p95, and p99 latency plus throughput;
- engine deserialize time and first five warm-up iterations;
- peak process RSS, NvMap/unified memory, board power, GPU utilization, clocks,
  and temperature from `tegrastats`;
- fixed 15 W power mode, recorded ambient/fan state, headless system, and no
  unrelated model download/build load.

Example model-only measurement:

```bash
/usr/bin/trtexec \
  --loadEngine=/home/neko/models/ZipDepth/engines/zipdepth_base_trt10.16.2_sm87_b1_384x672_fp16.plan \
  --warmUp=2000 \
  --duration=30 \
  --infStreams=1 \
  --useCudaGraph \
  --noDataTransfers \
  --percentile=50,90,95,99 \
  --exportTimes=/home/neko/models/ZipDepth/benchmarks/model-only-fp16-384x672.json
```

Run the same command without `--noDataTransfers` for binding-transfer cost. Do
not use spin-wait in the cart profile: TensorRT documents that it may lower
synchronization latency at the cost of CPU use and power.

### End-to-end perception matrix

The production benchmark must include more than `trtexec`:

- camera capture/decode;
- resize and BGR-to-RGB conversion;
- host/GPU transfer or zero-copy import;
- TensorRT enqueue;
- association with person ROIs/tracks;
- reduction to relative per-track statistics;
- queue age and stale-frame dropping;
- all three planned camera streams under the chosen scheduler.

Avoid the upstream demonstration path in production. It upsamples output to the
original frame, transfers a full float map to CPU, creates a color map, and can
write every frame. The Neko path should retain `384x672` depth on GPU and return
only small track summaries unless a local diagnostics mode explicitly requests
visualization.

Then run a 30-minute combined soak with the real local voice/LLM profile:

- Gemma loaded and serving bounded context;
- wake word, ASR, and TTS active;
- target aggregate camera rate;
- repeated conversations and greetings;
- sensor/model worker restart and camera disconnect;
- thermal throttling, p99 latency, missed audio deadlines, memory growth, and
  degraded-mode behavior recorded.

ZipDepth is acceptable only if it yields useful secondary perception without
causing audible glitches or evicting the conversational model. A lower scheduled
depth rate is preferable to keeping all three cameras at maximum model FPS.

## Runtime integration recommendations

- Keep the TensorRT worker separate from the export environment. `trtexec` and
  the system TensorRT Python binding are already installed.
- Keep the engine loopback/local; it needs no network access.
- Preallocate one input and output binding set per active inference context.
- Use a latest-frame queue of depth one per camera and discard stale frames.
- Warm the engine before publishing readiness.
- Use one context/stream first. Additional streams trade memory and power for
  throughput and must be measured.
- Preserve GPU-resident results for detector/ROI reduction. Copy only track IDs,
  timestamps, relative summaries, and health state to the behavior service.
- Mark every result with camera ID, source-frame monotonic timestamp, engine
  manifest ID, and validity age.
- Never interpret a raw ZipDepth scalar as metres or compare unaligned raw values
  across cameras/frames.
- Do not boot-enable ZipDepth until the sensor geometry, scheduler, health check,
  restart policy, combined soak, and degraded behavior are accepted.

## Artifact and rollback contract

Keep generated files outside Git under a structure such as:

```text
/home/neko/models/ZipDepth/
  export-env/
  engines/
    MANIFEST.json
    zipdepth_base_b1_384x672_op17.onnx
    zipdepth_base_trt10.16.2_sm87_b1_384x672_fp16.plan
    trt10.16.2_sm87_384x672.timing
  benchmarks/
```

The manifest must record:

- ZipDepth commit and checkpoint checksum;
- exporter source/patch checksum;
- every wheel URL/version/hash and Python/uv version;
- ONNX IR/opset and graph/operator inventory;
- ONNX, plan, and timing-cache checksums;
- TensorRT, CUDA, driver, L4T, GPU, precision, batch, and input geometry;
- exact build command and full builder log;
- numerical comparison and benchmark result paths.

Rollback is removal of the isolated export environment, generated ONNX/engine/
timing-cache/benchmark artifacts, and any future ZipDepth unit. Do not delete the
pinned source or original checkpoints during runtime rollback. Never copy a stale
engine to another board or keep using it after a TensorRT/BSP upgrade without a
fresh deserialize, parity, and benchmark pass.

## License assessment for the owner's stated use

### Verified facts

- The ZipDepth repository has an MIT `LICENSE` and ships the checkpoints in that
  repository. It does not provide a separate checkpoint model card/license.
- The README and paper say ZipDepth was distilled from Depth Anything V2 Large.
- Depth Anything V2's official repository licenses Base/Large/Giant model weights
  under CC BY-NC 4.0; only Small is Apache-2.0.
- The owner has now stated this Neko deployment is strictly personal and
  non-commercial.

Primary sources:

- ZipDepth license:
  <https://github.com/fabiotosi92/ZipDepth/blob/a302e5437bc58f15c4efd41d3e8222bf24f7d470/LICENSE>
- ZipDepth training provenance:
  <https://github.com/fabiotosi92/ZipDepth/blob/a302e5437bc58f15c4efd41d3e8222bf24f7d470/README.md#training-data>
- Depth Anything V2 license statement:
  <https://github.com/DepthAnything/Depth-Anything-V2#license>
- CC BY-NC 4.0 legal text:
  <https://creativecommons.org/licenses/by-nc/4.0/legalcode.en>

### Recommendation

Personal, non-commercial local evaluation fits the restrictive teacher license's
non-commercial boundary, so the ambiguity is not a present blocker to this
private experiment. It does not resolve whether a distilled student inherits
teacher-weight terms, and it does not authorize a future commercial deployment.

Keep both upstream license notices, paper/model attribution, source/checkpoint
provenance, and modification notes with the private artifact manifest. Do not
commit the checkpoint, ONNX model, TensorRT engine, or timing cache to the public
project repository. Reassess and obtain author clarification before any
commercial, paid, sponsored, or redistributed use. This is a conservative
engineering interpretation, not legal advice.

## Go/no-go checklist

Proceed to an experimental TensorRT build when all are true:

- [x] Export environment lock and top-level wheel hashes match this memo.
- [x] Source commit and checkpoint hash match.
- [x] Deployment exporter fails on any unapproved key mismatch.
- [x] Faithful static export succeeds without the learned-context rewrite.
- [x] ONNX checker passes and the exact local TensorRT parser builds it.
- [x] PyTorch -> diagnostic FP32 -> FP16 numerical comparison passes.
- [ ] `384x672` is confirmed as the deployed camera transform.
- [ ] Model-only and end-to-end measurements are recorded.
- [ ] Combined voice/LLM/perception soak passes in 15 W mode.
- [ ] Behavior treats ZipDepth only as a non-metric secondary cue.

Do not enable a boot service if any of the last five items remain unknown.
