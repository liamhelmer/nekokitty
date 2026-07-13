# Neko implementation plan — 2026-07-13

This plan incorporates the owner's decisions in
[`docs/decisions/2026-07-13-owner-decisions.md`](../decisions/2026-07-13-owner-decisions.md)
and the dated model, perception, audio, story, and operations research linked
from [`AGENTS.md`](../../AGENTS.md). Prices and product availability are a
2026-07-13 snapshot and must be checked again before ordering.

## Outcome and scope

Revision one is a local-first, child-conscious social assistant on a manually
driven, people-carrying cat-shaped golf cart. It talks, tells approved stories,
makes curated cat sounds, purrs through a body transducer, responds to bounded
commands, and reacts politely to nearby people. It starts without Internet and
continues in a useful degraded mode when any optional worker fails.

It does **not** steer, accelerate, brake, determine safe clearance, or claim to
be a vehicle safety system. Perception only informs social behavior. Any future
autonomous-motion revision starts a new safety project rather than extending an
LLM tool list.

## System shape

```text
roof mic + XVF3800 hardware AEC/beamforming
  -> local wake/VAD/streaming ASR
  -> deterministic intent, privacy, child-safety and turn-taking policy
       -> exact commands / approved story playback / sound actions
       -> loopback Gemma 4 E2B for bounded dialogue or scene generation
       -> redacted text-only cloud enhancement when explicitly allowed
  -> local TTS + audio scheduler/limiter
       -> full-range voice/effect speaker
       -> separately limited body purr transducer

front OAK metric person tracks + 360 range/presence + rear confirmation
  -> ephemeral metadata only
  -> deterministic dwell/approach/cooldown state machine
  -> one approved greeting event through the same interaction policy

hard electrical cart power switch
  -> whole system off

manual driver / future independent safety controller
  -> the assistant has no motion-control path in revision one
```

## Runtime and memory profiles

The 8 GB Orin uses shared DRAM. “Installed on NVMe” and “resident in memory” are
separate states.

| Profile | Resident components | Use |
| --- | --- | --- |
| Normal boot | audio I/O, wake/VAD, streaming ASR, deterministic policy, selected TTS, bounded Gemma, lightweight sensor workers | Default autonomous local experience |
| Degraded local | audio scheduler, canned commands/sounds, exact story playback; heavy worker(s) absent | Survives model/ASR/TTS/perception failure |
| Gemma GPU experiment | stop normal Gemma and optional heavy perception; load pinned GGUF/llama.cpp | Measured text-only performance/compatibility evaluation |
| ZipDepth experiment | one numerically accepted fixed-shape FP16 engine processes selected frames sequentially after camera/soak acceptance | Auxiliary relative-depth research only; not boot-enabled |
| Audex laboratory | stop Gemma, ASR, TTS, and optional depth workers before loading the selected Audex subset | Noncommercial evaluation; never a normal boot dependency |

The deployed default is currently the LiteRT-LM CPU service: four threads,
2,048-token cache, one fixed model, loopback only, and `Type=notify` readiness
after model preload. systemd bounds it with `MemoryHigh=2G`, `MemoryMax=2300M`,
no swap, `CPUWeight=40`, `Nice=5`, and `TasksMax=128`. Its roughly 1.4–1.5 GB
observed ready/peak memory leaves substantially more coexistence margin than an
unmeasured full GPU profile. Warm restart/API checks pass; actual cold-reboot
acceptance and the complete wake + ASR + TTS + perception soak remain required.

## Hardware recommendation and gates

### Audio

Provisional installed range: **US$280–445** before Canadian tax/shipping.

- Seeed reSpeaker Flex XVF3800 Circular-4 at the roof center for USB duplex,
  hardware AEC, beamforming, VAD, direction, gain, and noise processing.
- Dayton KAB-215v2 two-channel Class-D amplifier with Bluetooth disabled.
- Visaton FR 10 WP 4-ohm weather-resistant full-range speaker in a correctly
  sealed/gasketed baffle.
- Dayton TT25-8 body shaker on a lightweight body panel, not the passenger seat
  or chassis, with the SMRK-2 mount.
- Mean Well DDR-60G-12 or DDR-60L-12 only after measuring the cart pack; omit it
  if a clean, isolated, fused 12 V rail has enough capacity.
- DC fuse/disconnect, locking/shielded USB, rain/wind protection, strain relief,
  ferrites, and a fail-silent output path.

Do not buy the DC/DC converter until nominal, fully charged, and minimum battery
voltages are known. The transducer channel needs a limiter, band-pass/low-pass,
maximum duration/duty cycle, gentle fades, and a watchdog. Measure a child-safe
SPL and vibration limit; amplifier maximum is never the user volume maximum.

### Social perception

Conditional value tier: **US$1,100–1,300 installed**.

- Front OAK-D W with OV9782 wide/global-shutter color sensor: on-device person
  detection/tracking plus metric stereo XYZ.
- RPLIDAR S2L: anonymous 360-degree range clusters and approach/dwell, only if a
  substantially clear, level 0.9–1.2 m scan plane exists.
- Existing C922 at the rear: low-rate or event-triggered person confirmation in
  a suitable enclosure.
- Industrial powered USB hub, separately fused regulated sensor power, secured
  cabling, mounts, guards, and weather protection.

Combined with audio, the expected pre-tax additional hardware range is about
**US$1,380–1,730**, leaving pre-tax contingency below the owner's approximate
US$2,000 combined added-system ceiling.

The lidar decision is a geometry gate. If riders, posts, or bodywork block most
of a useful-height plane, substitute three exterior DFRobot C4001 24 GHz sectors
plus a wired microcontroller aggregator. That radar tier is cheaper but coarser,
normally lacks robust bearing/multi-person output, and has a documented 1.2 m
ranging floor. It may trigger a soft generic meow; spoken person-specific
greetings still require camera confirmation.

Three new perimeter OAK-D W cameras are technically cleaner semantic surround
coverage but cost approximately US$1.7–1.9k before audio. Keep that as a later
premium option. Three cameras clustered at the front do not provide 360 degrees
because they cannot see through the roof, shell, posts, driver, or passengers.

See [`docs/research/2026-07-13-audio-voice.md`](../research/2026-07-13-audio-voice.md)
and [`docs/research/2026-07-13-perception-bom.md`](../research/2026-07-13-perception-bom.md)
for exact parts, prices, power assumptions, placement, alternatives, and tests.

## Offline software choices

### Voice path

Benchmark the following in this order; do not install every candidate into the
normal profile at once.

1. XVF3800 hardware processing and 48 kHz duplex USB; resample capture once to
   the ASR rate and TTS once to the playback rate.
2. `openWakeWord` custom **Neko Neko** model, with sherpa-onnx keyword spotting
   as the active-maintenance comparison. Avoid “Hello Kitty” as the public wake
   phrase because of Sanrio branding risk.
3. Silero VAD 6.2.1 for endpointing, gated by the XVF speech-energy signal.
4. sherpa-onnx's INT8 export of Nemotron 3.5 ASR Streaming 0.6B, 560 ms profile,
   for current EN/FR/ES streaming evaluation. Compare against multilingual
   `whisper.cpp` base and small as the low-dependency recovery path.
5. Supertonic 3 as the first expressive EN/FR/ES local TTS candidate. Compare
   Pocket TTS and retain Piper as the small deterministic fallback after checking
   each selected voice's license.
6. Curated original meow/chirp/trill/purr assets. A local acknowledgement sound
   within 250 ms makes a multi-second generated reply feel deliberate.

Commands such as stop speech, mute, volume, exact story selection, repeat, help,
and cancel bypass the LLM. The physical cart emergency stop, if present, remains
separate; a voice “stop” is never represented as a vehicle e-stop.

### Dialogue and orchestration

- Keep the loopback OpenAI-compatible Gemma worker replaceable.
- Use a deterministic behavior service for typed intents, permissions, social
  state, cooldowns, audio actions, and degraded behavior.
- Use Pipecat for streaming turn orchestration only where it reduces custom
  plumbing; keep policy/state in Neko-owned typed code rather than framework or
  prompt state.
- The model may propose text or an allowlisted action request. It cannot execute
  shell commands, access vehicle control, change privacy policy, or grant itself
  permissions.
- Store model/profile selection in one supervisor. Starting Audex first stops
  incompatible heavy workers and checks available memory; a failed switch returns
  to the proven Gemma profile.

### Stories

Start with 60–100 human-reviewed CC0 or CC BY 4.0 short stories across English,
French, and Spanish. Use Global Digital Library as the primary API source, then
curated StoryWeaver and approved African Storybook titles. Store corpus data
outside Git; commit provenance/rights manifests and tooling only.

Every story exposes a child-visible choice:

1. original approved text;
2. deterministic curator-defined substitutions;
3. a surprise-safe bounded remix, only when the item permits adaptation.

Generate 100–200-word scenes from reviewed story cards, finish and safety-check
the whole scene before TTS, and never stream unchecked child-facing tokens.
Prefer existing human French/Spanish translations. Keep names/session choices in
volatile memory unless an adult explicitly saves a placeholder-based favorite.

Reject or quarantine ambiguous licenses, ND remixes, NC material, and SA material
until its obligations are implemented. Traditional, Indigenous, sacred, or
culturally sensitive material defaults to exact-only unless appropriate human
review supports adaptation. See
[`docs/research/2026-07-13-stories-cloud.md`](../research/2026-07-13-stories-cloud.md).

### ZipDepth

The pinned source/checkpoints, isolated CPU export environment, faithful static
`384x672` ONNX, and board-built diagnostic FP32 and candidate FP16 TensorRT
engines are provisioned. The exact deterministic PyTorch-to-FP32-to-FP16
numerical gates pass, but the
engines are not boot-enabled. Complete final camera-transform, scene-quality,
end-to-end power, and combined-soak validation before integration. ZipDepth
outputs affine-invariant relative inverse depth, not metres. It may rank
foreground/background or decorate
a camera-confirmed track; it never owns a greeting range, approach speed,
braking, or safe-clearance decision.

## Online enhancement and privacy

Offline readiness never waits for NetworkManager, DNS, a cloud API, an image
pull, or a model download.

The online router may send only locally produced, redacted text to a separately
funded and documented API. Replace child names, school/contact data, and precise
locations with opaque placeholders and reinsert them locally. Use a provider and
destination allowlist, small request budgets, short timeouts, a circuit breaker,
local output safety checks, and immediate local fallback.

Z.AI Coding Plan and ChatGPT/Codex subscriptions are development entitlements,
not embedded application API funding. Do not place their session credentials on
the cart or automate consumer coding clients as the runtime assistant.

Raw audio, images, video, and full source books do not leave during normal use.
Any future media upload requires contemporaneous human confirmation, a visible
indicator, a single bounded artifact, and an explicit destination. Around
children, adult confirmation is the default. A spoken “yes” alone is not a
strong media-export control.

Keep only a volatile 10–15 second audio ring buffer; disable raw recording and
transcript logging by default. Use ephemeral track IDs; no face recognition,
voice identity, demographic inference, or relationship memory in revision one.
Recommend a hardware microphone mute, camera shutters/service covers, and
indicators even though the owner does not require a separate radio/offline switch.

## Service boundaries and boot behavior

Provisional services, implemented only as their hardware/runtime is ready:

| Service | Minimum responsibility | Failure behavior |
| --- | --- | --- |
| `neko-audio` | duplex device, mixer, limiter, purr protection, fail-silent watchdog | outputs go silent; local status cue after recovery |
| `neko-wake` | wake, local mute/cancel, VAD | button/manual fallback remains |
| `neko-asr` | streaming local transcription | exact button/canned paths remain |
| `neko-gemma` | four-thread bounded fixed local model, preload readiness, loopback health | deterministic commands/stories/sounds remain |
| `neko-tts` | local streaming synthesis | canned voice/earcon fallback |
| `neko-sensors` | OAK/lidar/radar/C922 health and metadata | no proactive greeting; voice remains |
| `neko-behavior` | policy, typed intents, social state, child/privacy rules | fail closed on cloud/actions; audio watchdog remains |
| `neko-assistant` | turn pipeline and session coordination | supervisor restarts with bounded backoff |
| `neko-cloud` | text redaction/provider/circuit breaker | disabled/offline; never blocks local readiness |

Use loopback or Unix sockets, a dedicated least-privilege identity where useful,
read-only assets, bounded queues, explicit writable state paths, `Restart=on-failure`,
restart-rate limits, health/readiness endpoints, and journald logs without raw
user text. A service is “boot validated” only after an actual reboot, warm-up,
dependency-loss tests, and a combined soak—not merely `systemctl enable`.

## Delivery sequence and exit gates

### 0. Host/model foundation — provisioned, acceptance incomplete

- Permanent headless target configured and no GUI processes currently present;
  actual cold-boot verification remains pending.
- Host-matched CUDA/TensorRT compiler/runtime.
- Gemma LiteRT artifact and four-thread, readiness-notifying, resource-bounded
  loopback unit enabled and warm-tested.
- Audex exact-revision assets on NVMe; no runtime.
- ZipDepth exact-revision assets, isolated export environment, faithful ONNX,
  and board-built FP32/FP16 engines; numerical/runtime acceptance remains.
- Complete the GGUF/llama.cpp GPU decision and actual reboot readiness check.

Exit: package integrity, checksums, service health/restart, memory audit, and
operations rollback are recorded.

### 1. Geometry, power, privacy, and interaction survey

- Dimensioned cart sketch/photos with every seat occupied; candidate camera,
  microphone, speaker, shaker, hub, and lidar/radar mounts.
- Battery chemistry, nominal/full/minimum voltage, accessory rails, connectors,
  fusing, continuous/peak budget, cable routes, and ignition behavior.
- Operating weather/light/temperature, speed/noise, minimum child height, parked
  vs moving conversation policy, interaction radius, and acceptable blind zones.
- Final child age bands/content boundaries and privacy indicators/mutes.

Exit: lidar geometry passes or radar fallback is selected; DC/DC parts and
enclosure class can be chosen without guessing.

### 2. Bench audio minimum

- Install the XVF array, speaker, amp, and low-level body shaker on a protected
  bench supply.
- Pin firmware and ALSA identities; tune echo delay and barge-in.
- Build/evaluate Neko Neko, VAD, EN/FR/ES ASR, TTS voices, canned sounds, limiter,
  and fail-silent behavior.

Exit: wake targets, false wakes, word error, first-audio latency, interruption,
SPL/vibration, RAM/power/temperature, restart, and eight-azimuth tests pass.

### 3. Offline assistant minimum

- Implement deterministic commands/persona/state and the local turn pipeline.
- Integrate the existing bounded Gemma service, immediate acknowledgement,
  cancel/barge-in, structured logs, and degraded paths.
- Run network-loss and worker-crash tests from cold boot.

Exit: without Internet, a person can wake Neko, converse briefly, stop it, hear
a canned sound, and recover from a killed model worker within the agreed few
seconds.

### 4. Curated stories

- Implement the rights/provenance schema and hostile-archive ingestion gate.
- Human-curate the first exact/deterministic set before adding generation.
- Add bounded English scene remix and deterministic child-safety checks; add
  French/Spanish only after fluent review.

Exit: every visible item has a source/license/hash/content review; offline exact
and deterministic modes survive Gemma failure; generated scenes are fully checked
before speech.

### 5. Social perception

- Bench OAK plus the geometry-selected presence layer; reuse rear C922.
- Emit metadata only and implement deterministic dwell/approach/cooldown.
- Mount and field-map 360 degrees with occupants, children/adults, groups,
  occlusion, sun/night, vibration, motor noise, and intended weather.

Exit: range/coverage map and blind zones are explicit; no repeated solicitation;
camera confirmation gates spoken greetings; unplugged/blocked sensors degrade
without harming voice.

### 6. Combined cart soak and launch hardening

- Run perception + wake/ASR + Gemma + TTS for at least two hours, then longer
  representative duty cycles.
- Measure P50/P95 interaction latency, DRAM/NvMap, dropped audio/frames/events,
  total input power, minimum-battery behavior, temperature/throttling, and logs.
- Test ten cold boots, USB reorder/unplug, network loss, storage-full behavior,
  process crashes, corrupt/missing assets, mute/privacy state, and fail-silent
  amplifier behavior.

Exit: the offline minimum consistently starts and the total system remains below
measured power/thermal/memory limits with documented recovery.

### 7. Optional text-only cloud mode

- Obtain a separate supported API account/budget; implement redaction,
  allowlists, timeouts, circuit breaker, local safety checks, and visible state.
- Start with owner-approved pre-generation or current-information requests, not
  open-ended live child/cloud companionship.

Exit: packet capture proves only permitted redacted text leaves; every provider
failure immediately falls back locally; no subscription/session credential is
embedded.

## Next owner inputs

The next purchase cannot be finalized without:

1. battery chemistry, nominal/full/minimum voltage and existing fused rails;
2. dry-weather vs rain/overnight/wash requirement;
3. cart dimensions and a candidate 0.9–1.2 m unobstructed lidar scan plane;
4. minimum child age/height, story age bands, and parked/slow/moving interaction;
5. whether near-360 anonymous awareness with front/rear visual confirmation is
   enough, or every side person must be visually classified;
6. exact boundaries for scares, grief, religion/folklore, conflict, bathroom
   humor, memory/retention, and who will review French/Spanish;
7. whether version one cloud use should be owner pre-generation only.
