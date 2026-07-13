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

Status on 2026-07-13: the host/model foundation is deployed and hardware/software
integration planning is current. The machine permanently targets headless
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

The project is now the top-level Git repository on branch `main`, with private
remote `https://github.com/liamhelmer/nekokitty.git`. An accidental empty nested
clone was preserved outside the worktree at
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
  microphone is ALSA capture card 0.
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
  incorporated owner decisions, runtime profiles, costed hardware gates,
  offline/online architecture, delivery phases, acceptance gates, and next inputs.
- [Owner decisions](docs/decisions/2026-07-13-owner-decisions.md) — durable
  answers for licensing, model residency, headless/Git authority, manual-motion
  scope, character/languages/stories, offline-first behavior, and media privacy.
- [Audio and voice](docs/research/2026-07-13-audio-voice.md) — current costed
  hardware path, placement/power, wake/ASR/TTS candidates, voice rights, privacy,
  and acceptance tests.
- [Social perception BOM](docs/research/2026-07-13-perception-bom.md) — value,
  radar fallback, and premium sensing tiers; geometry, power, privacy, and tests.
- [Stories and cloud](docs/research/2026-07-13-stories-cloud.md) — source inventory,
  per-item rights, secure ingestion, child remix policy, subscriptions/APIs, and
  staged cloud enhancement.
- [LiteRT upstream report](docs/research/2026-07-13-litert-upstream-report.md) —
  exact R39.2 reproduction comment and upstream URL.
- [Setup log](docs/operations/setup-log.md) — every installation/attempt, exact
  versions/paths/hashes, sudo/headless status, rollback, and current model table.
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
- No Audex runtime, Pipecat, ASR, TTS, or Neko application service is installed.

## Research standards and evidence ledger

Research for this system is time-sensitive. For model/runtime claims, prefer model
cards, official repositories, papers, vendor documentation, release notes, and
current upstream issues over blogs or copied benchmarks. Record the retrieval date,
hardware context, precision/quantization, input/output lengths, warm/cold state,
power mode, and software commit/version for every benchmark. Never present an x86
GPU result as a Jetson result.

Current-source research was refreshed through 2026-07-13 and is recorded in the
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
- The costed first audio path is XVF3800 hardware AEC/beamforming, a two-channel
  Class-D amp, weather-resistant voice speaker, and separately protected body
  shaker. Current local candidates are Neko Neko/openWakeWord, Silero VAD,
  Nemotron 3.5 streaming ASR through sherpa-onnx with whisper.cpp fallback, and
  Supertonic 3 with Piper fallback.
- The conditional value perception path is a front OAK-D W/OV9782, useful-height
  RPLIDAR S2L, and the existing rear C922. Recommended perception is about
  US$1,100–1,300 installed; with the US$280–445 audio path, the combined added
  system is about US$1,380–1,745 before tax/shipping. If no clear lidar plane exists,
  use distributed radar and camera confirmation rather than roof-height fiction.
- Start stories with curated CC0/CC BY 4.0 Global Digital Library, StoryWeaver,
  and approved African Storybook items. Original, deterministic substitutions,
  and bounded remix are separate child-selected modes; whole generated scenes
  are checked before TTS.
- Two initial Claude Code reviews hit HTTP 529 and a later broad review stalled at
  the configured provider. A fourth, smaller local-only safe-mode review completed.
  It identified CPU oversubscription, readiness, memory-bound, least-privilege, and
  local-API robustness gaps; the first three were addressed in the deployed unit,
  while dedicated-user and authenticated/supervisor-only access remain explicit
  hardening gates. Exact attempts and findings are in the setup log.

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

The initial blockers are resolved in the owner-decisions record. Before buying
hardware, the project still needs battery chemistry/nominal/full/minimum voltage
and existing rails; cart dimensions and an occupied lidar sightline; intended
weather/washing/temperature exposure; minimum child age/height and story age bands;
parked/slow/moving interaction rules; and whether side anonymous awareness is
enough. The roughly US$2,000 ceiling is treated as the combined added-system
budget. The complete next-input list is in the current implementation plan.

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
