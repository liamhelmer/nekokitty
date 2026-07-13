# Neko the Kitty Carrier

Local-first software, deployment records, and research for Neko: a playful,
cat-shaped, manually driven people carrier with an offline voice assistant,
stories, sound/vibration effects, and privacy-conscious social perception.

Start with [`AGENTS.md`](AGENTS.md). It is the durable system inventory and
operations index for humans, Codex, Claude Code, and other project agents.

The repository intentionally excludes model weights, generated engines, private
audio/images/transcripts, credentials, and runtime caches. Exact external
artifacts and host changes are pinned and recorded in
[`docs/operations/setup-log.md`](docs/operations/setup-log.md).

Current status: the Jetson is configured to boot headless and its bounded,
loopback-only Gemma 4 E2B unit is enabled; readiness and warm restart tests pass,
but an actual cold-reboot acceptance test is still pending. Audex is staged on
NVMe for stopped, sequential evaluation. ZipDepth's source, checkpoints, isolated
export environment, faithful ONNX, and board-built FP32/FP16 TensorRT engines are
provisioned. Deterministic PyTorch/FP32/FP16 numerical gates pass; the real camera
pipeline, scene-quality review, and combined soak remain pending. This is a
research prototype. Perception is for social behavior and is
not a vehicle safety or motion-control system.
