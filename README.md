# Neko the Kitty Carrier

Local-first software, deployment records, and research for Neko: a playful,
cat-shaped, manually driven people carrier with an offline voice assistant,
stories, sound/vibration effects, and privacy-conscious social perception.

Start with [`AGENTS.md`](AGENTS.md). It is the durable system inventory and
operations index for humans, Codex, Claude Code, and other project agents.

The repository intentionally excludes model weights, generated engines, private
audio/images/transcripts, credentials, and runtime caches. It does include a
reviewed set of third-party Creative Commons cat recordings, each under its own
recorded licence rather than the root MIT licence. The maintained catalog and
processing queue are [Cat Sounds Master](docs/cat-sounds/CAT_SOUNDS_MASTER.md)
and [Processing and Remix Queue](docs/cat-sounds/PROCESSING_AND_REMIX_QUEUE.md).
The first 25 lossless P0 speaker/transducer bench candidates, deterministic
recipes, mastering measurements, attribution, and disabled semantic allowlist are
documented in [Derived Cat-Audio Bench](docs/cat-sounds/DERIVED_AUDIO_BENCH.md).
Exact external artifacts and host changes are pinned and recorded in
[`docs/operations/setup-log.md`](docs/operations/setup-log.md).

Current status: the Jetson is configured to boot headless. Its normal local
conversation profile is LFM2.5-1.2B Q5_K_M in CUDA llama.cpp with an explicit
16K context, served only on loopback. A resident Piper worker provides the fast
TTS path; the owner-selected KittenTTS Micro/Kiki 1.2x worker remains active for
quality comparison and rollback. Readiness and warm restart tests pass, but an
actual cold-reboot acceptance test is still pending. The old bounded Gemma 4
E2B/LiteRT unit is installed but disabled; Audex is staged on NVMe for stopped,
sequential evaluation. ZipDepth's source, checkpoints, isolated
export environment, faithful ONNX, and board-built FP32/FP16 TensorRT engines are
provisioned. Local Nemotron streaming ASR, Supertonic 3 TTS, deterministic
session/social behavior, and an RF-DETR Nano TensorRT webcam loop now pass bounded
bench tests. The attended continuous-audio loop now performs Nemotron decoding
while speech is still arriving, streams LFM text only to the first complete
short sentence, and begins Piper PCM an estimated 1.309 seconds after speech
ends in one private-fixture run. It also passes dedicated `Neko Neko` detection,
real TTS barge-in, and local `bye bye`/`goodbye` sleep. It retains no live
microphone media and is not boot-enabled. The 16K context is the accepted minimum;
story mode will retrieve or summarize bounded material into that window instead
of loading a whole library. Production P50/P95 latency, acoustic-onset,
false-wake/AEC, camera calibration, combined soak, and cold-boot tests remain.
This is a research prototype.
Perception is for social behavior and is
not a vehicle safety or motion-control system.

While production peripherals are in transit, use the non-recording bench harness
described in
[`docs/operations/2026-07-14-pre-hardware-smoke-tests.md`](docs/operations/2026-07-14-pre-hardware-smoke-tests.md)
to exercise temporary V4L2/USB audio devices, synthetic media paths, and the
local Gemma API.

The current low-latency measurements, exact model/runtime pins, deployment,
memory comparison, and rollback are in
[`docs/plan/2026-07-16-low-latency-voice.md`](docs/plan/2026-07-16-low-latency-voice.md).

Neko-authored source and documentation are licensed under the [MIT License](LICENSE).
External model/runtime terms remain controlling; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). In particular, YOLO26 is an
isolated benchmark and is not part of the MIT runtime.
