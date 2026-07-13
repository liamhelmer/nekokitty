# Neko assistant architecture — research cut 2026-07-12

## Current-status note — 2026-07-13

This document preserves the original architecture research. The
[owner decisions](../decisions/2026-07-13-owner-decisions.md) and
[current implementation plan](../plan/2026-07-13-implementation-plan.md) are
authoritative where status or scope has changed. Revision one is manually driven,
has no cart-control interface, and omits the proposed safety bridge; any independent
motion-safety controller belongs to a separately authorized future revision. The
owner does not require a separate radio/offline switch: the existing hard
electrical switch turns the whole system off, while software policy and visible
state still gate optional cloud egress whenever Neko is powered.

## Recommended shape

Build a cascaded, event-driven assistant with deterministic policy and safety
boundaries. Gemma 4 can consume audio directly, and Audex can span audio tasks,
but neither should be the only way to hear `stop`, mute microphones, select an
exact story, or manage an actuator.

```text
far-field mic + hardware DSP/AEC
  -> local wake word
  -> VAD + end-of-turn
  -> streaming ASR
  -> deterministic intent/policy router
       -> local commands / exact stories / privacy controls
       -> Gemma 4 local dialogue + bounded story remix
       -> cloud model only when policy permits and health is good
  -> local streaming TTS
  -> audio scheduler
       -> full-band speaker: speech, meows, trills, music
       -> protected transducer bus: band-limited purrs

RGB + stereo/ToF/radar
  -> person detection + anonymous stable tracks + metric XYZ
  -> social state machine
  -> approved greeting event -> same router

future independent safety controller/MCU (not present in revision one)
  -> e-stop, bumpers, braking/obstacle chain, watchdog
  -> no direct LLM control
```

The orchestration service should be replaceable independently of model servers
and sensors. A worker crash must not remove every voice command or leave an audio
transducer latched on.

## Reuse instead of rebuilding

### Voice orchestration

Preferred: [Pipecat](https://github.com/pipecat-ai/pipecat).

- Active upstream with about 13.4k stars at research time.
- Version 1.5.0 was released 2026-07-04:
  <https://github.com/pipecat-ai/pipecat/releases/tag/v1.5.0>.
- Pipecat Flows supplies structured dialogue/state:
  <https://docs.pipecat.ai/api-reference/pipecat-flows/overview>.
- `LLMSwitcher` supports local/cloud switching without immediately adding an
  extra LLM proxy:
  <https://docs.pipecat.ai/api-reference/server/utilities/service-switchers/llm-switcher>.
- Current service failover and time-to-first-audio metrics match this use case.

Main alternative: [LiveKit Agents](https://docs.livekit.io/agents/models/pipelines/)
if remote WebRTC clients, teleoperation, distributed rooms, or browser endpoints
become a core product requirement. A single embedded cart does not need that
operational surface initially.

Do not add LiteLLM for the first implementation. Pipecat can switch providers,
and LiteLLM had a credential-stealing supply-chain compromise in March 2026 plus
a later SQL-injection advisory. If it becomes necessary, use a patched,
hash-pinned release and review:

- <https://github.com/BerriAI/litellm/issues/24518>
- <https://github.com/BerriAI/litellm/security/advisories/GHSA-r75f-5x8p-qvmc>

### Acoustic front end

The existing Logitech C922 microphone is suitable for a quiet bench prototype,
not the final cart. Motor noise, fans, wind, structural vibration, speaker echo,
and the purr transducer will dominate speech quality.

Use a far-field array/DSP with hardware acoustic echo cancellation, beamforming,
noise suppression, and automatic gain control. A ReSpeaker/XMOS XU316 device is
one reference, not an automatic choice:
<https://wiki.seeedstudio.com/reSpeaker_usb_v3/>. Bench-test the actual array,
speaker placement, enclosure, and full-duplex behavior on the cart.

The audio subsystem needs:

- one named ALSA/PipeWire capture endpoint;
- separate logical speech/full-band and transducer buses;
- echo-reference routing into the AEC;
- priority/ducking and immediate barge-in cancellation;
- output limiter, high/low-pass filters as appropriate, maximum purr duration,
  duty-cycle and amplifier/transducer thermal protection;
- watchdog behavior that always silences outputs after process failure.

### Wake word, VAD, and turn completion

Keep wake detection local and continuously available.

- Low-power/custom option: [microWakeWord](https://github.com/OHF-Voice/micro-wake-word).
  It is still described as early and custom training needs a real dataset.
- Linux/portable option: [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx).
- Prototype-only option: [openWakeWord](https://github.com/dscripka/openWakeWord).
  Its bundled-model dataset terms and old release cadence require review.
- VAD baseline: [Silero VAD](https://github.com/snakers4/silero-vad), observed at
  v6.2.1 during research.
- Semantic end-of-turn candidate:
  [Smart Turn v3](https://github.com/pipecat-ai/smart-turn). Use only if it
  materially reduces cut-offs without increasing latency in cart noise.

Wake word training/evaluation must include Neko's own output, wind, motor, fan,
music/stories, nearby conversation, children, and likely accents. Measure false
wakes per hour and misses, not just clean-set accuracy.

### Streaming ASR

First candidate for NVIDIA evaluation:
[Nemotron 3.5 ASR Streaming 0.6B](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b),
released 2026-06-04. It advertises cache-aware streaming, punctuation/case,
language detection, and 40 locale targets.

Portable fallbacks:

- sherpa-onnx streaming Zipformer/Qwen-family ASR;
- Pipecat's Faster-Whisper integration:
  <https://docs.pipecat.ai/api-reference/server/services/stt/whisper>.

Do not assume current NVIDIA Riva embedded models support this Orin. Riva 2.26
release notes were updated 2026-06-30 and current embedded Nemotron/Magpie paths
focus on Jetson Thor:
<https://docs.nvidia.com/deeplearning/riva/user-guide/docs/public/release-notes.html>.
An old pinned Orin Riva stack would create a maintenance island. Direct/sherpa
deployment should be evaluated first.

Gemma 4 audio input can be evaluated as a slower second-pass transcription or
audio-understanding path. It accepts up to 30-second audio chunks and is not a
documented low-latency streaming ASR replacement.

### Dialogue model and tools

- Default local model: Gemma 4 E2B LiteRT-LM, short context, non-thinking mode
  for ordinary turns.
- Use thinking selectively for explicit complex requests; it costs latency and
  energy.
- Commands go through typed schemas and an allowlisted policy layer.
- The model may choose phrasing or fill safe text fields; it does not grant its
  own tool permissions.
- Hardware actions should become bounded requests to a deterministic behavior
  service, not shell/ROS access exposed directly to the LLM.
- Audex lives behind an experimental route and is never required for core
  offline commands.

### Local TTS and the cat voice

Fast/portable baselines:

- [Piper](https://github.com/OHF-Voice/piper1-gpl): fast and current, GPL-3.0,
  with upstream seeking maintainers.
- Pipecat [Kokoro](https://docs.pipecat.ai/api-reference/server/services/tts/kokoro)
  adapter: small model and easy integration.

Higher-character-quality candidate:

- [Pocket TTS](https://github.com/kyutai-labs/pocket-tts): current 100M MIT
  streaming CPU model with voice-cloning support. Its published performance is
  not an ARM/Jetson result, so benchmark it locally.

More expressive but heavier candidates:

- [Qwen3-TTS 0.6B CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice)
  for natural-language style/emotion controls.
- [NVIDIA Magpie 357M](https://huggingface.co/nvidia/magpie_tts_multilingual_357m)
  if a compatible runtime and combined memory budget are demonstrated.

The voice should be recognizably Neko through wording, timing, breathiness,
prosody, and occasional short cat sounds. Heavy pitch shifting hurts
intelligibility. Use an original/consented voice, never clone an identifiable
person without permission. Decide whether the target is cute childlike,
mischievous adult, robotic-cat, natural, or another concrete direction before
choosing TTS.

### Meows, trills, and purrs

Use a curated, licensed, reviewed soundbank rather than generating every sound
at inference time. Tag assets by function, affect, intensity, duration, and
allowed output bus: greeting chirp, question meow, acknowledgement trill,
contented purr, concern cue, sleepy sound, and so on.

Purrs should be seamless loops designed for the body transducer and protected
by a limiter/duty cycle. Speech/meows belong primarily on the full-band speaker.
The deterministic audio scheduler owns mixing, ducking, interruption, fade,
maximum duration, and fail-silent behavior. Audex general-audio generation is
too nondeterministic and expensive for routine feedback.

### Stories

[Audiobookshelf](https://github.com/advplyr/audiobookshelf) is a maintained
existing solution if the library includes prerecorded audiobooks, chapters,
progress, and metadata. A small text-only library needs only files plus SQLite
FTS5.

Define three explicit modes:

1. Exact recording playback.
2. Exact source text narrated by local TTS.
3. Remix only for owner-created, appropriately licensed, or verified
   public-domain works.

For remix, first produce a structured plan: characters, setting, required beats,
allowed transformations, exclusions, length, and age rating. Generate a bounded
section at a time and preserve a rolling summary/fact ledger. Never mutate the
canonical source. Store the variant with model revision, prompt/policy version,
source/provenance, and timestamp.

Use Project Gutenberg's robot feeds rather than scraping pages:
<https://dev.gutenberg.org/policy/robot_access.html>. Public-domain status there
is US-specific; Canada/other jurisdictions require their own check:
<https://www.gutenberg.org/policy/permission>.

### Person perception and social behavior

Use metric person tracks from stereo/ToF/radar as described in the ZipDepth
research note. A deterministic social state machine should be roughly:

```text
absent -> candidate -> nearby -> engaged -> cooldown -> absent
```

Initiate a greeting only when:

- a track has been stable for the configured dwell period;
- the person is approaching or lingering in a metric social zone;
- the cart is stationary or in an explicitly approved motion state;
- quiet/privacy mode is off;
- Neko is not already speaking/listening to someone;
- per-track/global cooldown has expired.

Greet once, then wait for reciprocal speech or a clear engagement event. Track
IDs are ephemeral by default; do not add face/voice identification. ZipDepth may
decorate/rank a track, not authorize a greeting distance.

## Online/offline routing

Offline must always retain wake/VAD/ASR, mute/privacy/stop commands, local
stories, basic dialogue, TTS, meows/purrs, and proximity greetings.

Router order:

1. Emergency-adjacent, stop, mute, privacy, volume, and deterministic commands:
   local handler. Voice stop is convenient but is not the physical e-stop.
2. Story, persona, social, and ordinary private requests: local Gemma.
3. Current-information or complex requests: cloud only if the owner policy,
   software cloud mode, privacy classification, connectivity, budget, and
   provider circuit breaker all permit it.
4. Timeout/rate limit/provider/network failure: cancel promptly and return a
   local graceful answer.

By default send locally produced text to the cloud, not continuous microphone
audio, images, video, raw sensor data, or stable identifiers. When powered, a
software egress policy must prevent unapproved cloud traffic and expose an
unmistakable cloud/microphone state. The owner will use the cart's hard electrical
switch when a physical strict-off state is required; no separate radio switch is
in revision-one scope.

Cloud providers must use the same typed, allowlisted tool layer as local models.
Provider credentials belong in a root-readable credential mechanism or hardware
keyring, never in source, unit files, process arguments, or logs.

## Service boundaries and boot order

Proposed system services (names are provisional):

| Unit | Responsibility | Starts without network? |
| --- | --- | --- |
| `neko-safety-bridge` (future only) | read-only state/events from a future independent controller | yes |
| `neko-audio` | device routing, AEC interface, mixer/limiter/watchdog | yes |
| `neko-wake` | wake word and local privacy/mute commands | yes |
| `neko-sensors` | metric depth/radar ingestion and health | yes |
| `neko-perception` | person detector/tracker; optional ZipDepth sidecar | yes |
| `neko-asr` | streaming local ASR | yes |
| `neko-tts` | local streaming speech | yes |
| `neko-llm` | selected local model profile and health endpoint | yes |
| `neko-behavior` | deterministic intents, social state, typed actions | yes |
| `neko-assistant` | Pipecat pipeline/session orchestration | yes |
| `neko-cloud` | connectivity/provider adapters and circuit breaker | no/core does not wait |

Boot sequence:

1. Audio fail-silent controller and wake/privacy path. Add a safety bridge only
   in a separately authorized future motion revision.
2. Metric sensors and perception.
3. ASR, TTS, and selected local model; preload and warm.
4. Behavior and Pipecat only report `ready` when minimum offline dependencies
   pass health checks. Otherwise expose `degraded` with commands/sounds intact.
5. Cloud adapter starts independently after connectivity; offline readiness must
   not depend on `network-online.target`, DNS, image pulls, or model downloads.

Use `Restart=on-failure`, bounded exponential restart/backoff, startup and
runtime watchdogs, explicit memory/CPU limits where safe, structured journald
logs, and device dependencies. Pre-download checkpoints and pre-build TensorRT
engines. Pin container images by digest if containers are used.

The current user lacks access to `/var/run/docker.sock` and is not in the Docker
group. Prefer native LiteRT for Gemma. Any container path needs an explicit
root/admin decision; never expose an unauthenticated model server on all network
interfaces. Bind local services to loopback or a Unix socket unless remote access
is deliberately enabled and authenticated.

## Safety and privacy floor

If the cart moves or carries people, the assistant is outside the safety loop.
Use an independent safety controller, hardwired e-stop, watchdog, obstacle and
braking chain, and fail-safe stop. ISO 13482 currently covers relevant classes,
but a second edition was in final approval during research; check the final text
before design freeze:

- Current standard page: <https://www.iso.org/standard/53820.html>
- Edition-2 project page: <https://www.iso.org/standard/83498.html>

Default privacy posture:

- physical microphone power/capture kill plus obvious indicator;
- camera shutter/indicator;
- RAM-only rolling buffers and no recording by default;
- short, opt-in, auto-expiring diagnostic clips;
- no face or voice recognition by default;
- ephemeral per-session person IDs;
- explicit online/offline indicator and egress control;
- encrypted secret storage and signed updates with rollback;
- pinned model/code/container digests and an SBOM;
- treat books, pages, transcripts, and retrieved content as untrusted data.

If ROS 2 is introduced, use per-node security enclaves and DDS authentication,
encryption, and access control:
<https://docs.ros.org/en/rolling/Tutorials/Advanced/Security/Introducing-ros2-security.html>.
Use ROS at the sensor/action boundary; do not force the entire voice pipeline
into ROS nodes. BehaviorTree.CPP is a good deterministic behavior candidate:
<https://github.com/BehaviorTree/BehaviorTree.CPP>.

## Measurement plan and provisional targets

Targets must be confirmed by the owner. Suggested prototype goals:

| Measure | Provisional target |
| --- | --- |
| Offline boot to basic wake/commands | <= 15 s after OS userspace |
| Boot to warm local dialogue | <= 45 s |
| End-of-turn to first audible response | P50 <= 1.2 s; P95 <= 2.5 s for non-thinking local turns |
| Barge-in stop of playback | <= 250 ms after detected speech/wake |
| False wake rate | < 1 per 8 operating hours in representative cart noise |
| Proactive greeting repeat | one per stable track/cooldown; near-zero repeat annoyance in scenario tests |
| Offline recovery | core interaction survives network removal/provider failure |
| Soak | 2 h prototype, then full duty-cycle run without OOM/throttling/restart loop |

Record P50/P95/P99 first-audio, ASR WER/intent accuracy, false wakes/hour, turn
cut-offs, memory, temperature, power, GPU/CPU utilization, audio underruns, sensor
dropouts, greeting false positives, and restart recovery. Benchmark all resident
workers together.

## Phased delivery

### Phase 0 — decisions and host baseline status

- **Completed:** record the first owner decisions, licensing posture, model
  residency profiles, Git remote, and model/cache locations.
- **Configured and warm-tested:** headless target and bounded Gemma service;
  actual cold-reboot acceptance is still pending.
- **Still open:** measure the final cart power/thermal environment and finalize
  audio and metric social-perception hardware.

### Phase 1 — reproducible model/perception labs

- **Provisioned:** pinned Gemma LiteRT import and bounded CPU service. Continue the
  combined benchmark/acceptance matrix.
- **Provisioned and deterministically numerically accepted:** pinned ZipDepth
  source/checkpoints, isolated export environment, faithful static ONNX, and
  board-built diagnostic FP32/production-candidate FP16 TensorRT engines. Camera
  geometry/scene quality, end-to-end performance, and combined-soak validation remain.
- **Staged only:** Audex is downloaded under the confirmed noncommercial use but
  has no runtime; attempt only isolated short-context components that can fit.
- Produce one command per profile plus checksums and complete rollback.

### Phase 2 — offline voice minimum

- Final audio device + AEC, wake word, VAD/turn detector, streaming ASR.
- Deterministic commands, Gemma dialogue, local TTS, curated meow/purr soundbank.
- Physical privacy controls and degraded mode.
- Pipecat integration and end-to-end latency/noise tests.

### Phase 3 — stories and persona

- Licensed story ingestion, exact/remix modes, provenance/fact ledger.
- Cat persona and TTS evaluation with owner listening tests.
- Audio/transducer limiter and long-duration thermal/duty-cycle tests.

### Phase 4 — proximity/social behavior

- Metric sensor/person tracks, hysteresis/dwell/cooldown state machine.
- Optional ZipDepth decoration/fallback.
- Public-space and bystander privacy tests; no motion integration until an
  independent safety design exists.

### Phase 5 — online extension and hardening

- Text-first cloud provider adapter, strict offline switch, budgets/timeouts.
- Security review, prompt-injection/tool-policy tests, signed update/rollback,
  observability and recovery drills.
- Reboot, power-loss, network-loss, sensor-loss, thermal, and full duty-cycle
  acceptance runs.
