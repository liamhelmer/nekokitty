# Neko the Kitty Carrier

This file is the durable entry point for humans and coding agents working on the
local/online assistant for the cat-shaped golf cart. Keep it current whenever a
model, package, service, device, configuration, or architectural decision changes.
Do not record API keys, tokens, Wi-Fi credentials, personal recordings, or other
secrets here.

## Project goal

Build a low-latency assistant that starts automatically with the cart computer and
continues to provide a useful, cat-like experience without Internet access. The
target experience includes conversation, meows and purrs through speakers/body
transducers, selected voice commands, stories from a local library with optional
on-the-fly variation, and privacy-conscious reactions to nearby people. When a
network and an allowed remote model are available, the same interaction layer may
offer broader capabilities without making core behavior cloud-dependent.

The first model/runtime evaluation must include both:

- `nvidia/Nemotron-Labs-Audex-2B`
- `google/gemma-4-E2B-it`. Research confirmed that the owner's “gemma4 e2b” is
  an exact official model name, not Gemma 3n E2B.

The perception evaluation must include ZipDepth: <https://zipdepth.github.io/>.

## Current phase and change policy

Status on 2026-07-16: the host/model foundation is deployed, the owner reports
that the production hardware has been ordered, and pre-arrival integration work
is active. The machine permanently targets headless
`multi-user.target`; GDM, X, GNOME Shell, and Firefox are absent. CUDA 13.2
compiler/development components and TensorRT 10.16.2 are installed from the
Jetson R39 repository. The bounded CPU Gemma service is installed, enabled,
preloads successfully, binds only to loopback, and has passed API/restart tests.
Its stock LiteRT GPU backend still prints the requested output and then exits 139;
the current R39.2 evidence was reported upstream, so that backend remains disabled.
The official QAT Q4_0 GGUF is pinned on NVMe and its all-layer CUDA llama.cpp
alternate profile passed on this Jetson at 18.63 generated tokens/s.

ZipDepth source/checkpoints, a hash-locked CPU export environment, faithful
static ONNX, and local TensorRT FP32/FP16 plans are pinned and verified. The FP16
plan measured about 8.73 ms model-only at `b1 384x672`; numerical engine parity
passes against the exact deterministic fused PyTorch reference. Real-camera
quality and combined-workload validation remain required before integration.
The full pinned Audex repository is on NVMe with major weights hashed; no Audex code has
run, and the unquantized speech path cannot fit in usable DRAM. Audex is a stopped,
selectable noncommercial laboratory profile, never a core boot dependency.
System-wide changes must be documented with exact commands, versions, paths,
validation, and rollback.

The temporary C922/Ora hardware-in-the-loop bench now passes non-retaining
camera decode, microphone-level, local Gemma, Supertonic-to-Bluetooth playback,
and positive RF-DETR person-detection checks. The 2026-07-16 positive detector
run held one anonymous track for 18 seconds at roughly 0.93–0.97 confidence.
The live adapter bug it exposed was fixed by carrying normalized box-bottom
metadata through `PersonObservation`. The ASR helper now accepts bounded
PipeWire capture for Bluetooth devices and reports only privacy-safe input
levels; Ora routing/capture works, but an intelligible spoken headset transcript
still needs a deliberately timed owner sample. No Neko application service was
enabled.

MeowLLM was also auditioned as an isolated lab profile on 2026-07-16. It is a
tiny English text-generation model, not TTS. Restricted checkpoint loading,
three CPU text generations, its portable rule smoke test, and a transient
MeowLLM-text -> Supertonic -> Ora playback passed. It is not integrated or
boot-enabled; at most, consider it later for optional non-factual cat quips.

KittenTTS 0.8.1 and the 80M Mini model are now pinned as another on-demand TTS
tool. The Kiki voice at 1.2x played successfully over Ora. Its audited minimal
CPU environment avoids an unused upstream Misaki/spaCy/Torch dependency chain
and mutable model download; a clean-room hash-locked reinstall passed. The first
6.15-second sample took 8.24 seconds to synthesize and peaked at 278.9 MiB RSS,
so Kiki is a promising English voice candidate, not yet the low-latency or
multilingual default. No KittenTTS service is enabled.

CatMeows 1.0.2 is pinned externally as a 440-clip candidate library. No clip has
been played or integrated: the 221 isolation-context calls are excluded by
default, and the brushing/food calls need a human friendly/distress curation
pass. Revision one will use a manifest-driven real-sound palette. Stable Audio 3
Small SFX was installed and measured as a stopped research profile, but both
owner auditions failed quality: distress and choppiness remained after guided
prompting. Raw generation is closed for revision one.

The project is now the top-level Git repository with `main` as its default/base
branch and public MIT-licensed remote
`https://github.com/liamhelmer/nekokitty.git`. PR 2 merged the local
conversation/proximity bench at commit
`ae63d3b6cee10b0f82467d5cecdaaa55f3e300a6`. An accidental empty nested clone
was preserved outside the worktree at
`/home/neko/repos/nekokitty-empty-clone-backup-20260713`. `CLAUDE.md` points
Claude Code back to this file so assistants share one durable source of truth.

## Verified host inventory

Inventory was collected locally on 2026-07-12 in America/Vancouver.

| Item | Verified value |
| --- | --- |
| Board | NVIDIA Jetson Orin Nano Developer Kit (`p3768-0000+p3767-0005`) |
| Memory | 7.3 GiB usable (8 GB class); no active swap at inspection time |
| CPU | 6-core Arm Cortex-A78AE, up to 1.5104 GHz |
| GPU | Integrated Orin `nvgpu`; `nvidia-smi` does not expose a separate VRAM total |
| Power mode | `15W` (`nvpmodel` mode 0) |
| OS | Ubuntu 24.04.4 LTS, aarch64 |
| Kernel | `6.8.12-1021-tegra` |
| NVIDIA BSP | L4T R39.2.0, build dated 2026-06-01 |
| NVIDIA driver/API | Driver 595.78; `nvidia-smi` reports CUDA 13.2 compatibility |
| CUDA toolkit | CUDA 13.2; `nvcc` 13.2.78 at `/usr/local/cuda/bin/nvcc`; CUDART 13.2.75 and cuBLAS 13.4 development packages installed |
| TensorRT | 10.16.2.10 libraries, development files, tools, and Python bindings installed from the R39/CUDA 13.2 repository |
| Root storage | Kingston SNV3S1000G NVMe, 930 GiB root partition; 798 GiB free after models, CUDA/TensorRT, and the llama.cpp container were provisioned |
| Extra storage | 500 GiB FAT volume mounted at `/media/neko/disk`; a SanDisk USB device also enumerates |
| Network | NetworkManager reports full connectivity; Realtek RTL8822CE Wi-Fi and RTL8111/8168 Ethernet |
| Container tools | Docker client 29.1.3, containerd, NVIDIA Container Toolkit 1.19.1 and NVIDIA runtime config present; `neko` lacks Docker-socket access |
| Python/tools | Python 3.12.3 without `pip`; uv 0.11.28 and LiteRT-LM 0.14.0 now installed under `/home/neko/.local/bin` |
| Node/Codex | Node 24.18.0; Codex CLI 0.144.2 |
| Claude Code | 2.1.207 at `/home/neko/.local/bin/claude`; installed but that directory was absent from the non-interactive shell `PATH` |

### Connected devices seen during discovery

- Logitech C922 Pro Stream Webcam at `/dev/video0` and `/dev/video1`; its USB
  microphone uses ALSA card ID `Webcam` (the numeric card index can vary).
- Ora GQ Headphone paired, bonded, trusted, and reconnectable through the onboard
  Bluetooth controller. PipeWire exposes a Bluetooth sink and source; the active
  profile observed during pairing was HSP/HFP with mSBC, so it is suitable for
  temporary duplex testing but not representative of final wired playback or
  high-quality A2DP latency. Its unique Bluetooth address is intentionally not
  recorded here.
- HDMI audio outputs on the Jetson and NVIDIA APE/ADMAIF endpoints. No dedicated
  USB speaker/DAC or body transducer output was identifiable from the initial ALSA
  listing.
- Bluetooth radio, USB hubs, Logitech Bolt receiver, Microsoft wireless receiver,
  I2C buses, and the storage devices listed above.
- No dedicated stereo/depth camera, lidar, radar, ultrasonic sensor, microphone
  array, or motor-controller serial endpoint was positively identified.

### Baseline operational observations

- The board was in 15 W mode and approximately 49 C during a short `tegrastats`
  sample. That sample occurred while discovery commands were using substantial CPU,
  so it is not an idle benchmark.
- About 4.0 GiB of 7.3 GiB RAM was initially in use and there was no swap. The
  GUI was later removed from the active/default boot path. A live audit with the
  ready Gemma service reported 5,951,504 KiB available; Gemma was the largest
  process at 1,539,996 KiB PSS. `tegrastats` reported about 4.9 W input and 45 C
  at that quiet instant. Concurrent audio, language, and depth models still need
  measured scheduling; page cache and parameter counts are not resident-memory
  measurements.
- systemd reported `degraded` because `dnsmasq.service`,
  `isc-dhcp-server.service`, and `isc-dhcp-server6.service` were failed. These may
  be stale network-configuration services; they have not been modified because they
  are outside the model deployment until their intended role is known.
- Docker and containerd are enabled, but user `neko` is not in the Docker group
  and cannot access `/var/run/docker.sock`. A sudo-run, digest-pinned NVIDIA
  llama.cpp container may be used for a bounded benchmark; the normal Gemma boot
  path remains native and does not require Docker.

## Documentation map

Read these before changing the system:

- [Model evaluation](docs/research/2026-07-12-models.md) — Gemma 4/Audex facts,
  revisions, licenses, memory analysis, runtime choices, and benchmark matrix.
- [ZipDepth and proximity](docs/research/2026-07-12-zipdepth.md) — non-metric
  limitation, exact pins/checksums, TensorRT plan, licensing issue, and physical
  sensor alternatives.
- [ZipDepth runtime assessment](docs/research/2026-07-13-zipdepth-runtime.md) —
  audited export discrepancy, pinned environment, faithful graph/build method,
  numerical/performance gates, and rollback.
- [Local Jetson benchmarks](docs/research/2026-07-13-local-benchmarks.md) — actual
  Gemma GGUF/CUDA and ZipDepth/TensorRT results, hashes, power/memory observations,
  limitations, and artifact locations.
- [Assistant architecture](docs/research/2026-07-12-assistant-architecture.md) —
  online/offline voice pipeline, reusable components, persona/audio, stories,
  social behavior, boot design, safety/privacy, tests, and phased delivery.
- [Current implementation plan](docs/plan/2026-07-13-implementation-plan.md) —
  runtime profiles, offline/online architecture, delivery phases, and general
  acceptance gates. Its earlier hardware purchase sections are superseded by the
  Canadian one-week decision.
- [Conversation and camera-proximity MVP](docs/plan/2026-07-14-conversation-proximity-mvp.md)
  — current two-loop implementation order for C922/reSpeaker audio, streaming
  ASR, Gemma, TTS, person detection, calibrated camera proximity, social state,
  production swap-over, memory constraints, and acceptance gates.
- [Owner decisions](docs/decisions/2026-07-13-owner-decisions.md) — durable
  answers for licensing, model residency, headless/Git authority, manual-motion
  scope, character/languages/stories, offline-first behavior, and media privacy.
- [Canadian one-week hardware decision](docs/research/2026-07-13-canadian-one-week-bom.md)
  — controlling revision-one purchase recommendation, Canadian stock and landed
  arithmetic, Reolink/radar/audio BOM, roof geometry, power allocation, and
  checkout/acceptance gates. It supersedes earlier purchase recommendations
  wherever they conflict.
- [Audio and voice](docs/research/2026-07-13-audio-voice.md) — long-form component,
  placement/power, wake/ASR/TTS, voice-rights, privacy, and acceptance research;
  the Canadian one-week decision controls the immediate hardware purchase.
- [KittenTTS and cat-audio toolbox](docs/research/2026-07-16-kittentts-cat-audio.md)
  — Kiki 1.2x local benchmark, minimal offline package patch/lock, CatMeows
  provenance, curated palette policy, and Stable Audio 3 Small SFX research gate.
- [Cat Sounds Master](docs/cat-sounds/CAT_SOUNDS_MASTER.md) — maintained
  annotations, emotional roles, action/output guidance, review decisions, and
  licence links for all 24 owner-reviewed recordings.
- [Cat sound processing/remix queue](docs/cat-sounds/PROCESSING_AND_REMIX_QUEUE.md)
  — trim/split/cleanup/mastering priorities, manual remix boundaries, derived
  asset contract, and runtime-enablement checklist.
- [Social perception BOM](docs/research/2026-07-13-perception-bom.md) — earlier
  OAK/lidar/radar and premium-tier research, geometry, power, privacy, and tests;
  the Canadian one-week decision controls revision-one procurement.
- [Stories and cloud](docs/research/2026-07-13-stories-cloud.md) — source inventory,
  per-item rights, secure ingestion, child remix policy, subscriptions/APIs, and
  staged cloud enhancement.
- [Power, weather, and physical integration](docs/research/2026-07-13-power-weather.md)
  — supplied 24 V/3 A, 19 V/3 A, and 12–14 V/20 A recommendation boundary,
  downstream rail allocation, historical full-pack research, outdoor zones,
  solar-roof mounting, and acceptance tests.
- [LiteRT upstream report](docs/research/2026-07-13-litert-upstream-report.md) —
  exact R39.2 reproduction comment and upstream URL.
- [Setup log](docs/operations/setup-log.md) — every installation/attempt, exact
  versions/paths/hashes, sudo/headless status, rollback, and current model table.
- [Pre-hardware smoke tests](docs/operations/2026-07-14-pre-hardware-smoke-tests.md)
  — privacy-preserving temporary webcam/USB-audio harness, production swap-over
  contracts, current test boundary, and commands to repeat after device changes.
- [Owner questions](docs/questions.md) — original 52-question discovery backlog;
  answered constraints are superseded by the decisions file and plan.
- [Bounded Gemma server](scripts/serve_gemma_litert.py) and
  [systemd source unit](deploy/systemd/neko-gemma.service) — installed and tested
  CPU/2K/4-thread, readiness-notifying, resource-bounded loopback service.
- [Faithful ZipDepth exporter](scripts/export_zipdepth_onnx.py), its
  [tests](tests/test_export_zipdepth_onnx.py), the
  [TensorRT validator](scripts/validate_zipdepth_tensorrt.py), its
  [tests](tests/test_validate_zipdepth_tensorrt.py), and the
  [locked environment](deploy/requirements/zipdepth-export.lock) — reproducible
  static ONNX path that does not use upstream's learned-context approximation.

## Software and skills installed during this project

### Agent skills

Installed the requested Vercel `find-skills` workflow for both Codex and Claude
Code. Its search/reputation checks led to six official NVIDIA Jetson skills:

- `jetson-diagnostic`
- `jetson-memory-audit`
- `jetson-headless-mode`
- `jetson-inference-mem-tune`
- `jetson-llm-serve`
- `jetson-llm-benchmark`

Codex/shared copies are under `/home/neko/.agents/skills`; Claude copies are
under `/home/neko/.claude/skills`. `find-skills` also exists at
`/home/neko/.codex/skills/find-skills` and
`/home/neko/.claude/skills/find-skills`. A project-local diagnostic copy exists
at `.agents/skills/jetson-diagnostic`. All selected skill instructions were read
before use. Exact provenance, quality signals, install commands, paths, security
scan summaries, and rollback are in the setup log.

The skills materially changed the work: they supplied structured live audits,
the filtered headless change, memory/runtime flags, and the benchmark contract.
The live tuner selected llama.cpp/4-bit as the lowest-memory GPU alternative on
this SKU; it remains a measured alternate profile rather than a reason to discard
the smaller, proven LiteRT CPU resident.

### Runtime software

- uv 0.11.28 is installed at `/home/neko/.local/bin/uv` and `uvx`; both local
  hashes are recorded in the setup log.
- LiteRT-LM 0.14.0 is installed as a uv user tool and exposes the
  `/home/neko/.local/bin/litert-lm` CLI.
- Gemma 4 E2B is imported as LiteRT model ID `gemma-4-e2b-it`; the pinned source
  and imported artifact paths, checksum, generated caches, tests, and rollback
  are in the setup log.
- `scripts/serve_gemma_litert.py` is the bounded CPU/2K/4-thread loopback server
  validated against LiteRT-LM 0.14.0. `deploy/systemd/neko-gemma.service` is
  installed at `/etc/systemd/system/neko-gemma.service`, enabled for
  `multi-user.target`, active, and returns the expected model/chat responses.
  It uses `Type=notify`, explicit ready status, 2 GiB/2.3 GB memory high/max
  controls, no swap, reduced CPU/OOM priority, empty capability sets, and a task
  limit. A real cold boot is still untested. The development unit still runs as
  user `neko` and has an unauthenticated loopback API; a dedicated identity and
  supervisor-owned credential or Unix socket are pre-passenger hardening gates.
- CUDA/TensorRT's 49-package minimal dependency closure is installed; the full
  GUI-heavy CUDA meta-toolkit was deliberately avoided. Exact package versions,
  command, disk change, validation, and rollback cautions are in the setup log.
- The official Gemma QAT Q4_0 GGUF is pinned at revision
  `69536a21d70340464240401ba38223d805f6a709` under `/home/neko/models`; its
  3,349,514,112-byte file matches SHA-256
  `3646b4c147cd235a44d91df1546d3b7d8e29b547dbe4e1f80856419aa455e6fd`.
- ZipDepth source and both published checkpoints are pinned at commit
  `a302e5437bc58f15c4efd41d3e8222bf24f7d470` under `/home/neko/models/ZipDepth`.
  `/home/neko/models/ZipDepth/export-env` contains the exact CPU-only locked
  exporter dependencies. Checked static ONNX plus target-built TensorRT 10.16.2
  FP32 and FP16 plans are under `/home/neko/models/ZipDepth/engines`; hashes and
  timings are in the setup/benchmark notes. No ZipDepth service is boot-enabled.
- Audex's complete 106-file, 12,281,588,752-byte repository snapshot is pinned
  under `/home/neko/models/Nemotron-Labs-Audex-2B`; five major weight hashes are
  in the setup log. No Audex code has been executed or runtime installed.
- No PATH file was changed; use absolute paths in scripts/systemd.
- Isolated sherpa-onnx 1.13.4 and Supertonic 1.3.1 environments plus their exact
  pinned model artifacts are installed on NVMe. Standalone multilingual
  benchmarks pass; neither is a service or boot dependency yet. Pipecat remains
  uninstalled because its current release has no native sherpa-onnx adapter and
  is unnecessary for the first bounded integration loop.
- The deterministic behavior core, fixed Gemma client, text-conversation tool,
  and memory-only ALSA/PipeWire live ASR tool are in the repository with unit
  coverage. The PipeWire path handles the observed PipeWire 1.0.5 `pw-record`
  exit-1-on-bounded-SIGINT contract only when PCM is present and stderr is empty.
  No Neko application service is boot-enabled.
- RF-DETR 1.8.3 export tooling, its exact Nano checkpoint/ONNX, and the locally
  built TensorRT FP16 plan are pinned on NVMe. The hash-verifying, non-recording
  C922 loop and metadata-only tracker pass. YOLO26/Ultralytics 8.4.95 exists only
  in an external export environment for the recorded AGPL comparison; it is not
  imported by Neko, distributed, or boot-enabled.
- `scripts/smoke_test_devices.py` is a dependency-free bench harness over the
  existing GStreamer/ALSA/PipeWire tools. Its default suite retains no camera or
  microphone media and never plays sound unless explicitly requested.
- MeowLLM source is pinned cleanly at commit
  `d267a6c89bd978150ff9760ba77a37e7cee6601a` under
  `/home/neko/models/MeowLLM`; its Hugging Face checkpoint/tokenizer are pinned
  separately at revision `f3a3f6ef7e2697e1346729f65d1e44bb3df31de8` under
  `/home/neko/models/meowllm-artifacts`. No package was installed: its audition
  reused the export-only CPU Torch/tokenizers environment. Never call upstream's
  `weights_only=False` loader on downloaded checkpoints; the pinned artifact
  passes restricted `torch.load(..., weights_only=True)`.
- KittenTTS 0.8.1 is installed only in
  `/home/neko/.local/share/neko/venvs/kittentts`; the exact 80M Mini ONNX and
  voices are pinned at Hugging Face revision
  `c02725660cea441db4c383af69f1f26f5cd00947` under
  `/home/neko/models/kittentts`. The project lock plus reproducible patch remove
  unused heavy imports and the eager downloader from the local path.
  `scripts/neko_kittentts_speak.py` verifies artifact hashes before inference.
  This is an English on-demand profile with no systemd unit.
- CatMeows 1.0.2's verified external archive and 440 extracted WAVs are under
  `/home/neko/models/cat-sounds/catmeows/4008297`. They are not distributed,
  approved for unattended playback, or training input. Preserve the record's
  CC BY attribution plus author-stated personal/research noncommercial boundary.
- The owner-curated real-sound library contains 24 Freesound recordings (127
  MiB, 812.226 seconds) under `/home/neko/curated-cat-sounds`.
  Twenty reviewed `keep_*` originals (74,496,458 bytes/about 71 MiB) are now
  distributed unchanged under `assets/cat-sounds/originals`; two maybes and two
  rejected standalone sources remain external. `assets/cat-sounds/manifest.json`
  pins distributed paths, hashes, creators, titles, licences, sources, and review
  decisions. `config/cat-sounds/curated-freesound.json` pins all filenames,
  hashes, creators, titles, source/license URLs, durations, provisional tags,
  and initial disabled states; the separate review ledger is authoritative for
  current selection. The inventory is 15 CC0 1.0, three CC BY 4.0, two
  CC BY-NC 3.0, and four CC BY-NC 4.0. All source pages resolved on 2026-07-16.
  `config/cat-sounds/curated-freesound-normalization.json` records GStreamer
  ReplayGain measurements for all 24 originals. The guided-review player is
  `scripts/neko_cat_sound_review.py`; it uses a 0.35 common review master,
  per-track gain, a -1 dBFS sample-peak ceiling, and a two-second Bluetooth
  pre-roll without rewriting audio. Review outcomes are recorded separately in
  `config/cat-sounds/curated-freesound-listening-review.json`. The owner-guided
  review is complete: 19 keep/priority candidates, two secondary maybes, one
  manual-only novelty track, and two sources not selected for standalone use.
  Top assets include the clean general meow (item 10, 10/10), affectionate
  thank-you meow/purr (14, 9/10), clean split-meow source (21, 9/10), primary
  transducer purr after a 0.5-second tail trim (17, 10/10), relaxing purr (23,
  9/10), and playful/snuffly affection purr (24, 10/10). The review master is
  not calibrated cart SPL. No candidate is eligible for unattended child-facing
  playback until excerpt selection, lossless mastering/true-peak analysis,
  attribution generation, deterministic action mapping, and final speaker/
  transducer acceptance pass. The manifest is not training-data clearance.
- Stable Audio 3 source is pinned at commit
  `0385302ea26522f00c80392c4b708df5ebf1adf5` under
  `/home/neko/models/stable-audio-3`. Its isolated 24-package ARM LiteRT runtime
  is under `/home/neko/.local/share/neko/venvs/stable-audio-3-tflite`, and exact
  optimized weights are pinned at revision
  `08c64b96b1e59942aade69759f60fb88c58c90c4`. It has no service. Keep it as
  research evidence only; do not route generated audio to children.

## Research standards and evidence ledger

Research for this system is time-sensitive. For model/runtime claims, prefer model
cards, official repositories, papers, vendor documentation, release notes, and
current upstream issues over blogs or copied benchmarks. Record the retrieval date,
hardware context, precision/quantization, input/output lengths, warm/cold state,
power mode, and software commit/version for every benchmark. Never present an x86
GPU result as a Jetson result.

Current-source research was refreshed through 2026-07-16 and is recorded in the
linked notes. Important conclusions:

- Gemma 4 E2B is the default local candidate. Its Google-supported 2.59 GB LiteRT
  distribution has a publisher Orin Nano GPU result of 24.2 decode tok/s, 0.9 s
  cache-initialized TTFT excluding load, and 2,739 MB in the model card's Linux
  `ru_maxrss`-based CPU Memory column. The prebuilt LiteRT GPU accelerator does
  not currently reproduce that result on this R39.2 Jetson: it emits the answer,
  then fails in NVVM/Dawn/Vulkan and exits 139. The safe measured fallback is CPU:
  the clean-of-transfer-work 1,024/256-token run reached 142.28 prefill and 14.73
  decode tokens/s, with 7.27 s TTFT, 2,249/7,485 MB peak observed RAM, about
  8.51 W peak input and 50.2 C peak temperature. A CPU audio-input smoke test
  also correctly transcribed the bundled ALSA sample. The fixed service initializes
  in about two seconds and uses roughly 1.5 GB after a request. The official Q4_0
  GGUF through digest-pinned llama.cpp/CUDA measured 18.63 decode tok/s with all
  99 layers offloaded; it remains an alternate profile because the container base
  targets older L4T R36.4/CUDA 12.9 and combined-workload residency is unproven.
- Audex's full BF16 model plus FP32 causal speech decoder start near 8.26 GB of
  weights before runtime overhead. It is noncommercial and has no official
  quantized/Jetson result. Keep it installed/selectable for permitted experiments,
  not normally boot-resident on 8 GB.
- ZipDepth is affine-invariant inverse depth, not metric distance; its scores are
  evaluated after scale/shift alignment and its paper acknowledges flicker. Use it
  only as a relative/visual auxiliary signal. Use stereo/ToF/radar metric tracks
  for greetings and independent hardware for cart safety. The faithful local FP16
  TensorRT plan measured 114.49 qps/8.73 ms model-only and 9.10 ms with synthetic
  transfers. Deterministic FP32/FP16 parity passes; local scene quality, camera
  preprocessing, and combined scheduling are still separate gates.
- Pipecat is the provisional voice orchestrator; use a deterministic intent/policy
  and social state layer, separate streaming ASR/TTS, curated meows/purrs, and
  cloud text routing only when explicitly allowed.
- The installed sherpa/Nemotron 560 ms INT8 profile cold-loads in 3.53 s and
  decoded the supplied French/Spanish clips at 0.393/0.382 real-time factor with
  about 1.35 GiB peak process RSS. Supertonic 3 cold-loaded in 1.41 s and
  generated English/French/Spanish at 0.662/0.674/0.655 real-time factor with
  about 492 MiB peak process RSS. These standalone publisher-text/clip results
  are not far-field or combined-workload acceptance.
- A 2026-07-16 C922/Ora bench found 5,570,724 KiB available before testing,
  46.8 C hottest reported zone, and about 4.5–4.8 W input. The combined
  non-retaining device suite processed 90 C922 frames at 25.79 wall fps,
  observed webcam-microphone activity, and received a one-sentence Gemma reply
  in 2.739 s. RF-DETR then held one anonymous person track for 18 seconds at
  0.926–0.969 confidence. Gemma -> Supertonic F1 -> Ora playback completed.
  The Ora source produced valid 16 kHz PCM and level metadata, but the diagnostic
  ASR samples contained effectively no sustained speech (one three-second run:
  -67.60 dBFS RMS, -31.38 dBFS peak), so their empty transcripts are not an ASR
  accuracy result. No media was retained.
- MeowLLM is not a speech synthesizer. Its official card describes a 3.45M-
  parameter, English-only, 256-token character toy that is explicitly outside
  general assistance, factual work, translation, and production use. On this
  Jetson, the restricted-loaded CPU model initialized in 0.1483 s, generated
  three 40-token-bounded replies in 0.2802–0.4156 s, and peaked at 290,396 KiB
  process RSS. Its best role, if any, is a tightly bounded optional cat-quip
  source whose complete text still passes Neko policy before Supertonic speaks
  it. It must never replace Gemma, story policy, or TTS.
- KittenTTS Mini's Kiki voice at 1.2x passed offline Ora playback. Two cold
  single-utterance CPU runs were consistent at 1.339–1.356 real-time factor,
  roughly 1.6 s load, and 276–279 MiB peak RSS. Its size is attractive, but it
  is English-only today and slower than the installed Supertonic standalone
  result. Keep it as a voice candidate until warm/chunked and production-speaker
  listening tests establish first-audio latency and quality.
- Use curated real cat recordings for revision one. CatMeows supplies labeled
  meows under CC BY 4.0 plus an author-stated noncommercial/research condition;
  isolation calls are not routine child-facing assets. Wikimedia and Freesound
  can fill purr/trill gaps only with per-file provenance. As of July 2026,
  Freesound uploader AI-training preferences are an additional gate for training,
  distinct from ordinary playback/remix clearance.
- Prefer the owner's 24-file Freesound library before mining broader datasets.
  Its checked manifest gives 10 meow-led, 11 purr-led, two mixed, and one
  processed novelty source based on titles/descriptions. Those are provisional
  tags only: kitten-attention and multi-cat/vet sources require explicit
  distress review, and the processed alarm stays manual-only. Select and edit
  approximately 12–20 approved excerpts after listening; preserve lossless
  masters and bounded delivery copies separately.
- Stability AI's May 2026 Stable Audio 3 Small SFX was tested through its
  official ARM TFLite/XNNPACK backend after owner license acceptance. The viable
  dynamic-int8 profile generated 20 seconds in 14.4–15.0 seconds at about 2.11
  GiB peak RSS, 9.41 W peak input, and 50.4 C. The weight-only-int8 profile was
  killed before sampling at about 6.5 GiB process RSS. Both dynamic-int8 owner
  auditions failed for distress/choppiness, including guided negative prompts.
  Close raw generation for revision one and use pre-recorded library sounds.
- Neko-authored code/documentation now has an MIT root licence and explicit
  third-party notices. Ultralytics' current terms do not permit an integrated
  YOLO26 dependency to be represented as MIT merely because the repository is
  public: project-wide AGPL-3.0 compatibility or an Enterprise licence is still
  required. YOLO26 evaluation artifacts remain external and licensing-gated.
- The pre-hardware conversation MVP keeps the measured CPU LiteRT Gemma service
  and reserves GPU/TensorRT capacity for perception. A 2026-07-14 live audit with
  Gemma loaded found 6,065,396 KiB available and no swap; Gemma led at 1,669,854
  KiB PSS. Install and benchmark only one ASR/TTS/detector candidate at a time.
  The first current-source stack is sherpa-onnx's June 2026 INT8 Nemotron 3.5
  streaming ASR, Supertonic 3 CPU/ONNX TTS, and RF-DETR Nano FP16 TensorRT.
  RF-DETR Nano's local 384x384 FP16 plan measured 9.48 ms model-only and 9.63 ms
  with transfers. YOLO26n measured 3.19/3.37 ms but remains an external
  comparison because public MIT publication does not satisfy Ultralytics'
  project-wide AGPL requirement. RF-DETR's Apache-2.0 path is the selected
  runtime: it has ample 5–10 fps headroom and preserves Neko's MIT licence.
- The one-week audio purchase path uses the Canadian-stocked Seeed reSpeaker USB
  four-mic/XVF3000 array, Soberton XPCB-12BT two-channel amplifier, Visaton FR 8
  WP 15 W RMS voice speaker, and a protected Dayton TT25-8 15 W RMS body puck.
  The older XVF3000 silicon is a schedule-first compromise; XVF3800 remains the
  preferred later array. Run the 10–25 V amplifier from the supplied 12–14 V
  accessory interface, not the already-loaded 24 V lighting interface. At this
  lower supply, target about 7 W clean per 8-ohm channel at 12 V and treat
  8–10 W as a 14 V bench target—not a guaranteed output—rather than promising
  the 2 x 25 W nameplate. Enforce fixed attenuation and independent protection.
  One voice speaker is sufficient. The two 15 W RMS drivers total 30 W, below
  the owner's 100 W combined speaker/transducer rating cap.
- **`Neko Neko` is approved** as the revision-one wake phrase; `Hello Kitty` is
  retired. Current local software candidates remain openWakeWord, Silero VAD,
  Nemotron 3.5 streaming ASR through sherpa-onnx with whisper.cpp fallback, and
  Supertonic 3 with Piper fallback.
- Revision-one social perception is now two opposing outdoor Reolink Duo 3V
  PoE-model 180-degree cameras powered through their 12 V inputs, a Brainboxes
  SW-005 on the Jetson onboard Ethernet port, plus four DFRobot C4001 radar
  sectors at nominal 90-degree spacing. Cameras provide local person semantics;
  the bare radars provide anonymous, coarse presence/range hints and require
  weather pods and camera confirmation before spoken greetings. Disable camera
  recording/cloud/P2P/audio and isolate them on a wired network with no default
  route. Optical/RF faces go outside the cart's post/slat obstruction plane.
  Proactive greeting is parked-only, with a camera-confirmed approach/dwell in
  the C4001's approximate 4–10 ft useful annulus. A level 2D lidar at the roughly
  7 ft roof scans above 3.5–4.5 ft children, so lidar is deferred; an inverted
  hemispherical 3D lidar is the later geometry-valid experiment.
- The Canadian one-week BOM is provisionally **CAD 1,399.68–1,722.08 landed** at
  an assumed British Columbia 5% GST plus 7% PST, leaving **CAD
  277.92–600.32** of unquoted headroom below the owner's **CAD 2,000 landed** cap.
  Checkout-confirmed tax, shipping, stock, itemized integration hardware, and
  arrival within seven days are still gates. The conservative
  simultaneous supplied-interface allocation is **135 W**; the complete Jetson,
  perception, audio, and transducer build has a hard **200 W running** acceptance
  cap, verified by measurement rather than nameplate arithmetic.
- Start stories for ages 5–10 with a 30-work cat-only pilot: 16 works in a 5–7
  presentation lane, 14 in 8–10, and at least 18 centered on wild, extinct, or
  mythical cats. Use curated CC0/CC BY 4.0 Global Digital Library,
  StoryWeaver, approved African Storybook, and individually cleared public-domain
  items. Cats must be central, not incidental keyword hits. Original,
  deterministic substitutions, and bounded remix are separate child-selected
  modes; whole generated scenes are checked before TTS. Every story is at most
  five minutes and defaults to light, explicitly non-scary treatment.
  Age-appropriate conflict and reviewed folklore/religion are allowed; serious
  grief and extreme bathroom humour are excluded. Prototype French/Spanish
  review may use an LLM, but must be labelled lower-assurance; French is the
  second language priority and Spanish the third. Both retain deterministic
  checks plus an approved local fallback.
- The owner defines three available power interfaces for this recommendation:
  regulated **24 V up to 3 A**, regulated **19 V up to 3 A**, and **12–14 V up
  to 20 A** for accessories. Upstream battery, converter, fuse, grounding, and
  wiring design are owner-managed and are not prerequisites for recommending
  Neko hardware. Keep the existing 1–2 A lights as the only baseline load on the
  24 V interface; run the Jetson from 19 V; run new perception/audio loads from
  12–14 V. Add a RECOM `REC30K-2412SZ` for regulated nominal-12 V camera power
  and an `R-78B5.0-2.0` for the 5 V radar/aggregator domain. Its data sheet lists
  2 A typical inrush and 10 ms typical startup under stated nominal-input test
  conditions—not a maximum at 12–14 V—so cold-start testing remains mandatory.
  Powering both modules from 12–14 V avoids the limited 24 V lighting headroom.
  The SW-005 and Soberton also accept 12–14 V directly. The 4-by-8-ft solar roof
  and 0–40 C/no-salt/rain/dust/sun exposure
  still make ingress, condensation, UV, full-sun thermal soak, and non-panel
  structural mounts hard gates. The Jetson developer kit is rated only 0–35 C;
  the owner approves orderly worker shedding and shutdown at 35 C.
- Optional online enhancement is limited to an authenticated-adult, text-only
  session through separately billed API access. It does not authorize raw media,
  consumer-subscription credentials, or unattended child-cloud interaction;
  use a keyed or locked-compartment local control; remote activation needs an
  authenticated expiring admin channel, visible cart-side state and local revoke.
  Provider allowlisting, redaction and spend limits remain gates.
- Two initial Claude Code reviews hit HTTP 529 and a later broad review stalled at
  the configured provider. A fourth, smaller local-only safe-mode review completed.
  It identified CPU oversubscription, readiness, memory-bound, least-privilege, and
  local-API robustness gaps; the first three were addressed in the deployed unit,
  while dedicated-user and authenticated/supervisor-only access remain explicit
  hardening gates. A later read-only hardware-note audit also stalled and exposed
  a broken local `SessionEnd` hook path; it made no edits. Exact attempts and
  findings are in the setup log.

## Provisional architecture constraints

These are constraints, not yet final component choices:

1. Core interaction must remain available offline; network loss must not break the
   wake/command/audio pipeline.
2. A deterministic supervisor/state machine should own turn-taking, permissions,
   interruption, cooldowns, and actuator/sound actions. A generative model should
   not directly control safety-relevant cart motion.
3. Cloud use must be an explicit policy-routed enhancement with timeouts, privacy
   filtering, visible/loggable mode changes, and an immediate local fallback.
4. Audio capture/playback, proximity sensing, and model workers should be separable
   services so one crash or memory spike does not silence every behavior.
5. Boot readiness means more than a process being started: services need health
   checks, bounded restart behavior, model warm-up, device dependency ordering,
   structured logs, and a degraded local mode.
6. The 8 GB unified-memory limit makes concurrent residency the central design
   constraint. Candidate models must be benchmarked together with the real audio
   and perception pipeline.

## Open owner decisions

The electrical source boundary is resolved for recommendation purposes: use the
owner-provided 24 V/3 A, 19 V/3 A, and 12–14 V/20 A interfaces and do not require
battery or upstream wiring evidence. Before ordering, the project still needs
checkout-confirmed seven-day arrival to the owner-supplied BC destination and
final stock for every BOM line. Field use still needs complete empty/occupied
front/rear/side geometry, protected electronics space, storage/overnight exposure,
a simultaneous under-200 W power test at the supplied interfaces, and accepted
blind zones/cooldowns. Parked-only greeting, <=10-ft interaction, 0–40 C/no
salt/cloth cleaning, one speaker, and orderly shutdown at 35 C are decided. Story
questions are now limited to age-lane language mix, retention/owner controls, and
the final manifest. Online mode still needs the exact keyed/local and authenticated
remote implementation, separately billed provider/budget, redaction/indicator
design, and retention policy. The Canadian BOM carries the controlling checkout
and one-week acceptance gates; fuller specialist questions remain in the linked
audio, perception, story, and power/weather notes.

Headless mode is now persistent: `multi-user.target` is the default, display
manager units are inactive, and no Xorg/GNOME/Firefox process is present.
Graphical recovery remains possible by deliberately setting
`graphical.target`; do not re-enable it casually because the memory budget and
boot acceptance results assume headless operation.

## Required deployment record template

For every future model or service, add:

- Name, upstream URL, license/access conditions, exact revision/commit and checksum.
- Install command/tool, package/container versions, destination/cache paths, and
  disk usage.
- Build flags, patches, quantization/calibration method, and generated artifacts.
- systemd unit/config/environment paths, service user/groups, device permissions,
  network exposure, secrets mechanism, resource limits, and dependency ordering.
- Cold start, warm start, first response, steady-state latency/throughput, peak RAM,
  temperature/power, quality notes, and test inputs.
- Health-check and boot/reboot validation results.
- Upgrade, backup, and complete rollback instructions.

## Change log

- 2026-07-12: Began discovery. Verified the host/device baseline, recorded the empty
  repository state, installed the requested skill-discovery workflow, and began
  current-source research.
- 2026-07-12: Corrected the Claude Code inventory after the owner supplied its
  absolute path. Verified Claude Code 2.1.207 at `/home/neko/.local/bin/claude` and
  attempted a read-only independent review twice. Both attempts failed at the
  configured provider with HTTP 529; no Claude findings were used.
- 2026-07-12: Completed parallel primary-source research, resolved Gemma 4 E2B,
  rejected ZipDepth as a metric/safety sensor, and documented the online/offline
  architecture, model decision, sensor alternatives, test plan, and owner questions.
- 2026-07-12: Installed six official NVIDIA Jetson skills for Codex and Claude,
  ran structured diagnostic/memory baselines, and generated a filtered headless
  plan. Sudo blocked the actual target change; no privileged mutation occurred.
- 2026-07-12: Installed verified uv 0.11.28 and LiteRT-LM 0.14.0 in user space.
  Began a revision-pinned, checksummed download of only the generic Gemma 4 E2B
  LiteRT artifact. No model or Neko service is boot-enabled.
- 2026-07-13: Verified and imported Gemma 4 E2B. Text and audio-input CPU tests
  passed; the short CPU benchmark measured 37.30 prefill and 14.51 decode tok/s.
  The GPU path reproduced an upstream Jetson NVVM/Dawn/Vulkan crash and remains
  disabled. Terminated the isolated owner graphical login and NVIDIA panel scope;
  Firefox stayed gone and available RAM temporarily rose to 6,446,796 KiB. GDM
  later respawned its own Xorg/GNOME greeter; removing it and making headless boot
  persistent still need the documented sudo commands.
- 2026-07-13: Added and API-tested a fixed-model Gemma server that preloads the
  measured CPU/2,048-token configuration, plus a validated but uninstalled
  hardened systemd unit template. Pinned the official ZipDepth repository and
  verified both checkpoint sizes and hashes without executing its code.
- 2026-07-13: Added a minimal `CLAUDE.md` entry point that directs Claude Code
  to this shared `AGENTS.md` and its setup/research ledger.
- 2026-07-13: Downloaded the complete exact-revision Audex evaluation snapshot,
  verified its expected file count/content bytes and five major weight hashes,
  cleaned only stale failed-transfer parts, and executed none of its code.
- 2026-07-13: Recorded the owner's noncommercial, sequential-residency,
  local-first, manual-motion, media-privacy, language, persona, story, Git, and
  hardware constraints. Made headless boot persistent and verified the GUI absent.
- 2026-07-13: Installed the host-matched minimal CUDA 13.2 compiler/development
  closure and TensorRT 10.16.2, validated packages/Python/compiler/libraries, and
  retained more than 824 GiB free NVMe space.
- 2026-07-13: Installed/enabled the hardened bounded Gemma unit. It preloaded,
  returned the fixed model and `meow`, survived a stop/start cycle, and reported
  no restart loop. A real cold reboot acceptance check remains outstanding.
- 2026-07-13: Reproduced the LiteRT GPU exit-139 failure after CUDA installation,
  restored the CPU service, and posted non-sensitive R39.2/LiteRT-LM 0.14.0
  evidence to upstream issue 2570.
- 2026-07-13: Pinned and checksummed the official Gemma QAT Q4_0 GGUF and began a
  Jetson-specific llama.cpp alternative-profile evaluation. Added current costed
  audio/perception, story/cloud, owner-decision, and gated implementation notes.
- 2026-07-13: Passed the digest-pinned llama.cpp/CUDA GGUF benchmark at 18.63
  generated tokens/s with all layers offloaded. Documented and reproducibly fixed
  the current NVIDIA Orin image's missing shared-library loader path.
- 2026-07-13: Reduced the normal Gemma service to four threads, added explicit
  systemd readiness and cgroup/priority/capability bounds, and revalidated model
  listing plus an exact `meow` chat response with no restart.
- 2026-07-13: Installed a hash-locked CPU ZipDepth export environment, exported a
  faithful learned-context-preserving static ONNX, built local TensorRT FP32 and
  FP16 plans, and measured the FP16 plan at about 8.73 ms model-only. Exact
  deterministic PyTorch/FP32/FP16 numerical gates passed; real-camera and
  combined-workload evaluation remain pending.
- 2026-07-13: Incorporated the 48 V-class/four-battery LiFePO4 description,
  existing 24 V and 19 V converters, 4-by-8-ft solar roof, outdoor exposure,
  ages 5–10 audience, and all-cat story theme. Added full-pack/protection,
  graceful-shutdown, weather, geometry, 24 V accessory, sensor-ingress, and
  30-work pilot gates without changing software, wiring, or hardware.
- 2026-07-13: Confirmed the four traction batteries are in series and adopted the
  Canadian one-week revision-one BOM: two Reolink Duo 3V PoE cameras, four C4001
  radars, and locally stocked four-mic/audio parts. Recorded the CAD 1,144.60–
  1,364.60 planning range, 129 W allocation/200 W cap, five-minute light stories,
  approved `Neko Neko` wake phrase, provisional LLM French/Spanish review, and
  authenticated-adult text-only billed API policy. No part was ordered or installed.
- 2026-07-13: Superseded that preliminary power allowance after the owner
  identified both installed bucks as 4–38 V input modules. Recorded the immediate
  full-pack/midpoint prohibition, Canadian-stocked DDR-240C-24/RSD-60L-12/
  DDR-60L-12 replacement candidates, SW-005 direct-DC camera topology, revised
  CAD 1,625.13–1,947.53 total and 135 W allocation after a revised provisional
  safety allowance and conservative shipping tax. Inspected the occupied cart
  image transiently, deleted it without committing people or embedded precise-
  location metadata, and moved cameras/radars outside the slat plane. Also
  recorded the owner-supplied BC delivery region,
  parked-only <=10-ft greeting, 0–40 C/no-salt/cloth-cleaning environment, one
  speaker, French priority, story boundaries and keyed/remote adult-mode options.
  No wiring, package, service, order or model state changed.
- 2026-07-13: Corrected the recommendation boundary to the owner-provided
  regulated 24 V/3 A, regulated 19 V/3 A, and 12–14 V/20 A interfaces. Removed
  battery/wiring evidence and the three full-pack converters from active purchase
  gates; selected a RECOM `REC30K-2412SZ` for nominal-12 V camera power and an
  `R-78B5.0-2.0` for 5 V radar/control power. Kept the Jetson on 19 V, reserved
  24 V for the existing lights, and moved new accessory loads to 12–14 V.
  Recorded the owner-approved 35 C orderly shutdown, the 135 W total allocation
  across the supplied interfaces, and revised CAD 1,399.68–1,722.08 planning
  range. Historical
  electrical research remains labelled and preserved. No wiring, package,
  service, order, or model state changed.
- 2026-07-14: Added a privacy-preserving pre-hardware smoke-test harness for
  temporary V4L2 cameras, ALSA USB microphones/playback, synthetic media, and the
  bounded Gemma API. It records no media by default and makes audible playback
  explicit. Added unit coverage and a runbook separating reusable software
  contracts from production camera/radar/audio/power/weather acceptance.
- 2026-07-14: Paired, bonded, trusted, connected, and reconnect-tested an owner-
  supplied Ora GQ Bluetooth headset. The adapter was returned to non-pairable and
  non-discovering state. PipeWire exposed both playback and microphone endpoints
  under its mSBC headset profile; no package or service configuration changed.
- 2026-07-14: Refreshed current official voice/perception research and fixed the
  pre-hardware implementation sequence. Recorded a live 8 GB coexistence audit,
  retained CPU LiteRT Gemma, selected sherpa-onnx INT8 Nemotron 3.5 ASR and
  Supertonic 3 for first benchmarks, and chose Apache-2.0 RF-DETR Nano over an
  AGPL YOLO26 default for the private repository. Defined calibrated camera-only
  social proximity as an estimate, with radar confirmation still required later.
- 2026-07-14: Added an MIT root licence and third-party notice, removed the exact
  delivery postal code from the current worktree before public-release review,
  and implemented the typed deterministic wake/session/social-greeting core plus
  a fixed local Gemma client. Public release was authorized; the historical
  regional postal code remains in prior Git commits because history was not
  destructively rewritten.
- 2026-07-14: Installed hash-locked isolated sherpa-onnx/Nemotron streaming ASR
  and Supertonic 3 TTS profiles, verified model hashes, and passed French,
  Spanish, and three-language synthesis benchmarks. Added a memory-only C922 ASR
  tool and an opt-in-audio local conversation tool; no new service was enabled.
- 2026-07-14: Attempted two read-only Claude Code reviews through z.ai; both
  failed at the provider with HTTP 529 and reproduced the broken SessionEnd hook,
  so they produced no findings or edits.
- 2026-07-14: Benchmarked locally built RF-DETR Nano and YOLO26n FP16 TensorRT
  engines. Selected Apache-2.0 RF-DETR for the MIT runtime, added a hash-checked
  non-recording C922 detector/ephemeral tracker loop, and kept YOLO26 isolated as
  an AGPL licensing benchmark. A concurrent Gemma + RF-DETR + live Nemotron ASR
  run peaked at 3,618/7,486 MB RAM, 8.27 W input, and 48.72 C; all 63 tests passed.
- 2026-07-14: Merged the conversation/proximity work through public PR 2 and
  changed `liamhelmer/nekokitty` from private to public. GitHub and an
  unauthenticated API request both reported public visibility, `main` as the
  default branch, and MIT licence detection. No Git history rewrite was done;
  the regional delivery postal code remains visible in older commits as noted.
- 2026-07-16: Re-ran the C922/Ora hardware-in-the-loop bench. The privacy-safe
  combined smoke, positive 18-second RF-DETR track, Gemma response, and
  Supertonic Bluetooth playback passed. Fixed the live proximity serializer and
  added bounded in-memory PipeWire ASR capture plus signal telemetry. Ora input
  routing was verified, but captured trials lacked sustained speech, so live
  headset transcription remains pending. All 65 unit tests passed; no package,
  model, boot target, or service state changed.
- 2026-07-16: Pinned and safely auditioned MeowLLM as a text-only cat-character
  lab artifact. The restricted checkpoint load, 34-rule portable smoke test,
  three sub-half-second CPU generations, and transient Supertonic/Ora playback
  passed. Recorded that it is not TTS or an assistant, and left it unintegrated
  and disabled. No package or service was added.
- 2026-07-16: Installed a hash-locked, locally patched minimal KittenTTS 0.8.1
  CPU profile and pinned the 80M Mini model. Kiki at 1.2x passed two synthesis
  smokes and transient Ora playback; the first sample measured 1.34 real-time
  factor and 278.9 MiB peak RSS. Pinned the CC BY CatMeows 1.0.2 archive as an
  uncurated external source and documented the May 2026 gated Stable Audio 3
  Small SFX follow-up. No cat clip or KittenTTS service was integrated/enabled.
- 2026-07-16: After owner acceptance, pinned and ran Stable Audio 3 Small SFX's
  official ARM LiteRT backend. Dynamic-int8 generated faster than real time at
  about 2.11 GiB RSS; weight-only-int8 exceeded memory. Both dynamic-int8 owner
  auditions remained distressed/choppy, including guided prompts, so raw
  generation was rejected for revision one in favor of curated real recordings.
  Gemma was stopped only during trials, restored healthy, and no service was added.
- 2026-07-16: Inventoried the owner's 24-file/127 MiB curated Freesound library
  without playback or modification. Resolved every source and Creative Commons
  page, pinned source filenames and SHA-256 hashes in a repository manifest, and
  recorded the 15 CC0/3 CC BY/6 CC BY-NC license split plus provisional semantic
  tags. All entries remain disabled pending a recorded emotional/safety,
  background-noise, time-range, output-role, and gain review. No package,
  service, model, or audio file was added to the runtime or Git.
- 2026-07-16: Began the one-source-at-a-time owner listening pass. Fixed-volume
  playback was too quiet and sub-second audio was lost while Bluetooth woke, so
  measured all 24 originals with GStreamer ReplayGain and added a non-destructive
  peak-bounded player with a two-second silent pre-roll. Item 1 then passed as a
  slightly fuzzy but good plaintive/interrogatory/insistent keep candidate. No
  original, package, service, model, default sink, or boot state changed.
- 2026-07-16: Completed structured owner classification of all 24 curated cat
  recordings. Retained 19 primary/keep candidates, two secondary maybes and one
  manual-only novelty; rejected two for standalone runtime. Identified the
  10/10 general meow, primary trimmed transducer purr, and playful/snuffly purr,
  plus explicit excerpt/split/cleanup work. Item 22 was stopped once the owner
  had enough evidence to reject standalone use; the other 23 played in full.
  All audio remains disabled pending derived-asset mastering and hardware tests.
- 2026-07-16: Added all 20 `keep_*` Freesound originals unchanged to the public
  repository with an asset-level manifest and explicit Creative Commons boundary
  (11 CC0, three CC BY 4.0, two CC BY-NC 3.0, four CC BY-NC 4.0). Added the
  maintained 24-source Cat Sounds Master and separate processing/remix queue.
  The six NC sources remain personal/noncommercial and no source is runtime-
  enabled; derived assets still require mastering, attribution, and hardware
  tests. Asset integrity/licence tests and the complete 71-test suite pass.
