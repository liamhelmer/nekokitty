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

Current status: the Jetson is configured to boot headless. Its bounded,
loopback-only Gemma 4 E2B unit and private-Unix-socket English TTS worker are
enabled; readiness and warm restart tests pass, but an actual cold-reboot
acceptance test is still pending. English uses the owner-selected KittenTTS
Micro/Kiki voice at 1.2x; French and Spanish use on-demand Supertonic. Audex is staged on
NVMe for stopped, sequential evaluation. ZipDepth's source, checkpoints, isolated
export environment, faithful ONNX, and board-built FP32/FP16 TensorRT engines are
provisioned. Local Nemotron streaming ASR, Supertonic 3 TTS, deterministic
wake/social behavior, and an RF-DETR Nano TensorRT webcam loop now pass bounded
bench tests. Camera ground calibration, a trained wake-word model, production
audio integration, remaining systemd worker units, and soak tests remain pending. This is
a research prototype. Perception is for social behavior and is
not a vehicle safety or motion-control system.

While production peripherals are in transit, use the non-recording bench harness
described in
[`docs/operations/2026-07-14-pre-hardware-smoke-tests.md`](docs/operations/2026-07-14-pre-hardware-smoke-tests.md)
to exercise temporary V4L2/USB audio devices, synthetic media paths, and the
local Gemma API.

Neko-authored source and documentation are licensed under the [MIT License](LICENSE).
External model/runtime terms remain controlling; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). In particular, YOLO26 is an
isolated benchmark and is not part of the MIT runtime.
