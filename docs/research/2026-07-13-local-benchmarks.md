# Local Jetson benchmark record — 2026-07-13

This note records measurements made on Neko's actual Jetson, not publisher
figures. All measurements were taken headless in America/Vancouver on the
8 GB Jetson Orin Nano (`p3768-0000+p3767-0005`), L4T R39.2.0, fixed 15 W
`nvpmodel` mode 0. They are laboratory model-only results, not proof that the
eventual audio, perception, and assistant stack fits or meets its latency gates.

## Gemma 4 E2B GGUF through llama.cpp/CUDA

Artifact:

- official repository: `google/gemma-4-E2B-it-qat-q4_0-gguf`;
- revision: `69536a21d70340464240401ba38223d805f6a709`;
- file: `gemma-4-E2B_q4_0-it.gguf`;
- bytes: `3,349,514,112`;
- SHA-256: `3646b4c147cd235a44d91df1546d3b7d8e29b547dbe4e1f80856419aa455e6fd`.

The NVIDIA-AI-IOT Orin alias resolved on the test date to:

```text
ghcr.io/nvidia-ai-iot/llama_cpp@sha256:ba196b9760fda683a84048916ec6666650cc4b05d3bfc05c02bf1917553e55f1
llama.cpp build 8966, commit 7b8443ac7
```

That image is labelled for L4T R36.4, Ubuntu 22.04, and CUDA 12.9, whereas this
host is R39.2/Ubuntu 24.04/CUDA 13.2. It also contains its llama shared objects
under `/usr/local/lib` but omits that directory from its loader path. The
digest-pinned one-line derivative in
`deploy/docker/llama-cpp-jetson/Dockerfile` fixes only `LD_LIBRARY_PATH`.
The live NVIDIA-runtime smoke found the Orin GPU, compute capability 8.7, and
7,485 MiB shared GPU-visible memory. This demonstrates that this particular
workload ran; it does not turn the older container base into a generally
supported R39 runtime.

The official `jetson-llm-benchmark` wrapper was run with Gemma's normal service
stopped, four host threads, all layers offloaded, 1,024 prompt tokens, and 256
generated tokens:

```text
n_prompt             1024
n_gen                 256
n_gpu_layers          99
prompt/prefill rate   294.70 tokens/s (derived from 3.47473 s)
generation rate       18.63 tokens/s
inter-token time      53.68 ms
derived prefill time  3,474.73 ms
peak observed RAM     about 3,802/7,485 MB
peak observed input   about 11.07 W
peak observed GPU     about 52.1 C
```

The wrapper labels the prompt-duration calculation as `ttft_ms_p50`; it is
actually `1,024 / prompt-throughput`, not an instrumented interactive
time-to-first-token percentile. The result is one run and warned that MAXN is
preferred for cross-system comparison. Neko intentionally remained in its cart
15 W profile.

Conclusion: the GGUF/CUDA path is a viable text-only alternate profile and is
faster than the measured LiteRT CPU decode path. It is not the boot default:
the container consumes about 8.23 GB on disk, uses substantially more live
shared memory than the ready LiteRT service, comes from an older JetPack base,
and has not yet been co-scheduled with audio or perception. The native CUDA
llama.cpp build under `/home/neko/.local/src/llama.cpp/build-orin-cuda` was
paused safely during its large architecture-87 kernel compile and is not a
completed runtime.

## ZipDepth faithful export and TensorRT builds

The tested source is upstream ZipDepth commit
`a302e5437bc58f15c4efd41d3e8222bf24f7d470`. The GPU checkpoint is
`27,298,978` bytes with SHA-256
`a55910bb0b99c8c5e641cb9206e810b269690ad94e8a2ef08c827c4679391a65`.

Export environment:

```text
/home/neko/models/ZipDepth/export-env
Python 3.12.3
torch 2.12.1+cpu
onnx 1.18.0
numpy 1.26.2
```

The environment is recreated from `deploy/requirements/zipdepth-export.lock`.
The project exporter preserves learned GlobalContext spatial attention, requires
an exact clean source commit and checkpoint hash, loads exact state keys with
`weights_only=True`/`strict=True`, uses the legacy static exporter explicitly
with `dynamo=False`, opset 17, no ONNX simplifier, and checks/infer-shapes the
result. This deliberately avoids upstream's approximate exporter, which replaces
learned spatial attention with average pooling.

Both system Python and the pinned environment passed the exporter's 11 focused
unit tests. A real deterministic CPU export then passed PyTorch reference/fused/
export-model parity, ONNX checker, strict shape inference, operator-domain audit,
and post-export mutation check.

Generated artifacts outside Git:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| static `b1 384x672` opset-17 ONNX | 24,639,883 | `38a9cc74be691be98190fd460ac1bba2986c5a7c16e3f33f5404463d74d2cbd0` |
| export provenance manifest | 6,428 | `343920624f72a518d2d0dc2d3eed1c505128e48620284540555a321e9a135655` |
| TensorRT FP32/no-TF32 diagnostic plan | 40,725,116 | `c4c3e7fd67b8e9204e24d2981aab21d635266ead121a5fa203a074d5a72012ba` |
| TensorRT mixed FP32/FP16 plan | 13,224,420 | `13ed532b2ce2fa3cbcf6ad4cfb1dcb9e2c1498705477a328171dc750da1a4b78` |
| TensorRT timing cache | 1,653,363 | `35c79e6a973ff91684ba1f540e5a8fa7913143808f2605bb20ebdd462d260964` |

TensorRT 10.16.2 parsed the graph as one FP32 input and one FP32 output, with no
custom/plugin nodes. Both builds used optimization level 5, a 512 MiB workspace
cap, zero auxiliary streams, and the same local timing cache. The FP32 plan was
built with TF32 disabled in 194.855 seconds; the FP16 plan was built in 446.986
seconds. The latter is a weakly typed mixed-precision plan because TensorRT's
newer Model Optimizer autocast route is not currently the reproducible Jetson
path for this graph.

### TensorRT model-only timing

All runs used one inference stream, CUDA Graph, 2 seconds warm-up, 30 seconds
measurement, and 50/90/95/99 percentiles. FP16 has three independent runs in
each mode. `model-only` suppresses binding transfers; `transfers` includes the
synthetic input/output copies performed by `trtexec`.

| Plan/mode | Runs | Mean throughput | Mean latency | P99 latency |
| --- | ---: | ---: | ---: | ---: |
| FP16 model-only | 3 | 114.485 qps | 8.733 ms | 8.805 ms |
| FP16 with transfers | 3 | 114.208 qps | 9.101 ms | 9.178 ms |
| FP32/no-TF32 model-only | 1 | 47.799 qps | 20.919 ms | 21.143 ms |
| FP32/no-TF32 with transfers | 1 | 47.728 qps | 21.232 ms | 21.293 ms |

During the captured FP16 interval, 1-second `tegrastats` samples peaked at about
2,414/7,485 MB system RAM, 55.44 C GPU/TJ, and 11.96 W input. FP32 peaked at
about 2,356 MB, 54.38 C, and 11.41 W. These are observed system-level maxima,
not isolated engine allocations. Raw logs and `trtexec --exportTimes` JSON are
under `/home/neko/models/ZipDepth/benchmarks` and intentionally outside Git.

These figures show ample model-only headroom for the target 5–10 Hz auxiliary
schedule. They do not include capture, resize/color conversion, person tracking,
queueing, or the future ASR/TTS/LLM workload.

The subsequent hash-pinned one-shot validator recreated the exact deterministic
fused PyTorch output and passed all FP32, FP16, and cross-precision gates. FP32
MAE/max absolute error were `7.13e-8`/`1.94e-7`. FP16 MAE/max absolute error
were `7.55e-5`/`4.81e-4`, with cosine similarity `0.99999915` and Spearman rank
correlation `0.99999559`. The 13,091-byte pass-only validation manifest has
SHA-256 `db2709054d61866aabeff56557bf7fcb30de7142ccbaa6ad4c25eadc0f58333a`.
Local image/scene quality and the end-to-end camera/assistant workload remain
separate required gates.

ZipDepth outputs affine-invariant relative inverse depth. Even a numerically
perfect, fast engine does not produce metres and must never own cart motion,
collision avoidance, or a physical greeting threshold.
