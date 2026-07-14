# Neko implementation plan — 2026-07-13

This plan incorporates the owner's decisions in
[`docs/decisions/2026-07-13-owner-decisions.md`](../decisions/2026-07-13-owner-decisions.md)
and the dated model, perception, audio, story, and operations research linked
from [`AGENTS.md`](../../AGENTS.md). Prices and product availability are a
2026-07-13 snapshot and must be checked again before ordering.

For the one-week hardware revision, the Canadian purchase decision in
[`docs/research/2026-07-13-canadian-one-week-bom.md`](../research/2026-07-13-canadian-one-week-bom.md)
supersedes the earlier US-dollar OAK/S2L and overseas-audio purchase paths
where they conflict. Those earlier notes remain useful research and
acceptance-test records, not the current shopping list.

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
roof mic + locally stocked four-mic XVF3000 hardware AEC
  -> local wake/VAD/streaming ASR
  -> deterministic intent, privacy, child-safety and turn-taking policy
       -> exact commands / approved story playback / sound actions
       -> loopback Gemma 4 E2B for bounded dialogue or scene generation
       -> adult-authenticated, redacted text-only billed API when allowed
  -> local TTS + audio scheduler/limiter
       -> limited Visaton FR 8 WP voice/effect speaker
       -> separately limited body purr transducer

opposing front/rear Reolink Duo 3V panoramas on local 12 V + private Ethernet
  with no default route
  + four exterior C4001 radar sectors at 0/90/180/270 degrees
  -> ephemeral metadata only
  -> deterministic dwell/approach/cooldown state machine
  -> one approved greeting event through the same interaction policy

normal off/offline control
  -> orderly Linux shutdown -> hardware-supervised delayed converter cutoff

DC-rated service/emergency disconnect
  -> immediate whole-system electrical isolation when safety requires it

full 48 V-class LiFePO4 bank output (four batteries in series; labels/BMS pending audit)
  -> protected Mean Well DDR-240C-24 candidate -> fused 24 V accessories
  -> protected Mean Well RSD-60L-12 candidate -> dedicated 12 V Jetson
  -> protected Mean Well DDR-60L-12 candidate -> cameras + SW-005 switch

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

The one-week schedule baseline uses parts observed in Canadian stock:

- Seeed reSpeaker USB four-mic array with the older XVF3000 processor for USB
  duplex and hardware AEC. Its discontinued silicon is a lifecycle compromise,
  so pin its working firmware and retain a spare/rollback plan.
- Soberton XPCB-12BT, a 10–25 V, 2 x 25 W amplifier. Use wired AUX, disable
  Bluetooth, and verify after every cold boot that it did not re-enable.
- One Visaton FR 8 WP, 8-ohm, 15 W RMS weather-resistant voice speaker in a
  correctly gasketed and drained baffle.
- One Dayton TT25-8, 8-ohm, 15 W RMS body shaker with the SMRK-2 ring on a
  lightweight body panel, not a passenger seat or structural chassis member.
- A sealed downstream fuse holder, fixed hardware gain/attenuation, DC branch
  protection, shielded USB/audio cable, wind treatment, strain relief, ferrites,
  and a fail-silent watchdog.

The two drivers total **30 W RMS**, below the owner's 100 W driver-rating cap.
Limit the voice channel to about 12–15 W RMS and the purr channel to about
10–12 W RMS so the 2 x 25 W amplifier cannot overdrive either 15 W device. The
combined planning allocation for amplifier and audio output is approximately
**35 W electrical**, not a promise to deliver amplifier nameplate power.

The reSpeaker Flex XVF3800 Circular-4 remains the preferred long-term microphone
because its current AEC/AGC/beamforming/noise-processing platform avoids the
XVF3000 lifecycle issue. It is not a one-week dependency until a Canadian
checkout can guarantee delivery. The locally stocked two-mic XU316/reSpeaker
Lite is a schedule fallback only if the four-mic board is unavailable or proves
unnecessary in an open-cart pickup test.

Feed the amplifier from a separately fused, regulated downstream branch of the
proposed documented 24 V accessory output, or select a different amplifier with
adequate input margin. Do not connect the 25 V-maximum Soberton directly merely
because the rail is nominally 24 V: the DDR-240 adjusts to 28 V and its own
overvoltage trip is too high to protect that amplifier. Select and bench the
downstream regulator/overvoltage protection, including startup and turn-off
overshoot, before connection. The present generic 4–38 V module is rejected on
both the full nominal-48 V string and a battery midpoint.

The four LiFePO4 batteries are in series. Every converter input must span the
complete series string; a battery midpoint is never an accessory supply. Keep
the Jetson alone on the proposed isolated 12 V RSD branch. The transducer channel
still needs a limiter, band-pass/low-pass, maximum duration/duty cycle, gentle
fades, and a watchdog. Measure a child-safe SPL and vibration limit; amplifier
maximum is never the user-volume maximum.

### Social perception

The one-week build uses camera semantics plus inexpensive sector presence:

- Two opposing Reolink Duo 3V PoE-model panoramas powered through their 12 V
  inputs, one below the front roof edge and
  one below the rear edge. Each provides a nominal 180-degree horizontal by
  53-degree vertical view, local person events, RTSP/ONVIF, IP67 ingress, and an
  IK10 housing. Start at roughly 25–30 degrees downward pitch, then map the real
  seams and occlusions with every seat occupied.
- Four DFRobot C4001/SEN0609 24 GHz modules at nominal yaws 0, 90, 180, and 270
  degrees. Four 100-degree nominal horizontal sectors provide about 10 degrees
  of neighbor overlap; three modules would leave nominal gaps before beam
  roll-off. Start around 20–25 degrees down and constrain the social range to
  approximately 1.2–3.05 m (4–10 ft).
- A wired four-UART aggregator, regulated 5 V, RF-tested weather pods, protected
  cabling, a Brainboxes SW-005 on the Jetson's onboard Ethernet port, dedicated
  DDR-60L-12 camera power with two individually fused runs, structural brackets,
  glands, drip loops, and strain relief.

The C4001 is a bare PCB and coarse dominant-presence/range source, not an
IP-rated multi-person tracker or reliable bearing sensor. Require dwell/approach
consistency and camera confirmation before a spoken greeting. A radar-only side
event may at most trigger a restrained generic sound. Proactive greetings are
parked-only in revision one because cart ego-motion corrupts approach cues;
wake-word conversation can remain available under the driver's policy. Gate
greetings on a camera-confirmed approach/dwell in the radar's approximate
4–10 ft useful annulus. Inside its documented roughly 4-ft ranging floor,
suppress repeated solicitation and retain wake/camera behavior. Disable camera
microphones, speakers, sirens, spotlights, recording, P2P, UPnP, cloud, email,
and FTP. Give the camera network no default route or DNS and verify isolation by
packet capture.
Use low-rate H.264 substreams and bounded local person detection rather than
continuously decoding both 16 MP streams.

The occupied-cart photograph establishes that posts/slats and passengers will
occlude any camera or radar mounted inside the passenger envelope. Put panorama
optical faces below and just outside the front/rear post plane and radar faces
outside the slats, all on structural roof-frame brackets rather than solar-panel
or LED-strip hardware. The source image contained people and embedded location
metadata, was inspected transiently, deleted, and not committed. Obtain complete
empty/occupied front/rear/side survey geometry before drilling.

There is **no lidar in the one-week build**. A level two-dimensional S2/S2L at
the approximately 7-ft roof scans roughly 2.5–3.5 ft above the 3.5–4.5-ft child
audience. Tilting a plane lowers only one azimuth while raising the opposite
side; it does not create a downward surround cone. A vulnerable useful-height
mount among the body, posts, driver, and passengers does not beat the camera/
radar path on this schedule.

An inverted roof-mounted hemispherical 3D lidar, provisionally Unitree L2, is
the preferred later lidar experiment because inversion places its hemisphere
below the roof. It remains deferred until Canadian stock/ETA, external water
protection, optical-window treatment, 12 V power, landed cost, and combined
tests pass. OAK-D W, RPLIDAR S2, and the existing C922 remain research or
diagnostic alternatives rather than revision-one purchase dependencies.

The roughly 4-by-8-ft roof is solar-panel surface, not free mounting area. Put
cameras and radar pods below structural perimeter/eave mounts without clipping
their fields; do not shade, drill, or bond to panels without manufacturer
approval. All exposed assemblies must pass rain/splash, dust/mud, dirty-window,
UV, condensation, vibration, cable-tug, cold/hot restart, and parked-in-sun
thermal tests. Pressure washing remains prohibited until the exact assembled
system has an applicable rating.

### Canadian cost and total-power envelope

The provisional added-system planning range is **CAD 1,625.13–1,947.53 landed**,
leaving **CAD 52.47–374.87** under the owner's fixed CAD 2,000 landed ceiling.
This uses an assumed British Columbia 5% GST plus 7% PST and includes planning
allowances for power, network, weather protection, cabling, and mechanics. It is
not a checkout quote: confirm arrival to the supplied BC postal code V9G 1L8
within seven days, taxes, shipping, stock, cable lengths, converters, and mounts
before buying.
Do not consume the reserve until those items are known.

The deliberately conservative simultaneous allocation is:

| Domain | Planning allocation |
| --- | ---: |
| Jetson, NVMe, and cooling load allowance | 30 W |
| Two Reolink cameras plus SW-005 load allowance | 26 W |
| Four radars and wired aggregator | 5 W |
| Microphone array and remaining low-voltage data electronics | 5 W |
| Limited amplifier, 15 W speaker, and 15 W transducer | 35 W |
| All conversion loss, thermal/measurement controls, and unallocated contingency | 34 W |
| **Simultaneous pack-side planning total** | **135 W** |

The first five rows are conservative load-domain allowances; the 34 W reserve
contains the full-pack and downstream conversion losses needed to express the
135 W total at the pack, plus controls and unallocated measurement contingency.
It is not a measured result.

Acceptance is a hard **measured maximum of 200 W running** for the scoped Neko
loads during the worst approved combined workload. Measure all three proposed
full-pack converter inputs with lights/non-Neko accessories isolated. Lights are
outside this cap; test their simultaneous operation separately for rail/thermal
interference rather than subtracting a guessed baseline. Use approximately
**180 W as a soft software load-shedding threshold**, while sizing every fuse
and conductor from its audited circuit rather than a software limit. The
runtime threshold also needs a selected isolated pack-side voltage/current
measurement path; if that path includes the lights, it may shed Neko early but
must never under-report total input.

Startup inrush is a separate electrical acceptance test, not an exception hidden
inside “running.” The three candidates publish typical input inrush of 30 A,
20 A, and 20 A. Prevent simultaneous uncontrolled application with a qualified
sequencing/precharge or inrush-limiting design, and coordinate the BMS, contactor,
wiring, and fuse time-current curves. No traction-pack runtime calculation is
required or authorized; battery labels, BMS rules, converter input/output
behavior, and protection remain audit gates despite the known four-in-series
topology.

The candidate component data sheets include 40 C operation under their stated
orientation, enclosure, ventilation, and derating rules; assembled solar-bay
margin remains unproven. The Jetson Orin Nano Developer Kit itself is rated only
0–35 C. Instrument enclosure ambient and thermal zones; unless the hardware
platform changes, 35–40 C requires optional-worker shedding followed by orderly
shutdown, not a claim of continuous operation. Owner acceptance of that degraded
boundary remains open.

See [`docs/research/2026-07-13-audio-voice.md`](../research/2026-07-13-audio-voice.md)
and [`docs/research/2026-07-13-perception-bom.md`](../research/2026-07-13-perception-bom.md)
for the longer component research and tests, and
[`docs/research/2026-07-13-canadian-one-week-bom.md`](../research/2026-07-13-canadian-one-week-bom.md)
for the superseding purchase list, Canadian prices, availability, and arithmetic.

## Offline software choices

### Voice path

Benchmark the following in this order; do not install every candidate into the
normal profile at once.

1. Locally stocked four-mic XVF3000 hardware AEC and duplex USB for the one-week
   build; pin its working firmware and ALSA identity. Evaluate XVF3800 as the
   long-term replacement once its Canadian delivery is dependable. Resample
   capture once to the ASR rate and TTS once to the playback rate.
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

Start with a 30-work human-reviewed cat-only pilot: 16 works in the ages 5–7
presentation lane, 14 in ages 8–10, and at least 18 centered on wild, extinct,
or mythical cats. Expand toward 60–100 only after the rights, ingestion,
narration, and safety workflow passes. Every enabled title must center a cat:
domestic cats, wild felids, or a clearly reviewed fictional feline all fit;
incidental keyword matches do not. Use Global Digital Library as the primary API
source, then curated StoryWeaver, approved African Storybook, and individually
dual-jurisdiction-cleared public-domain titles. Store corpus data outside Git;
commit provenance/rights manifests and tooling only.

Every complete story must fit within **five minutes**. Default to a light,
explicitly non-scary tone. Age-appropriate conflict and reviewed
folklore/religion are allowed. Serious grief and extreme bathroom humour are
excluded. Suspense, threat and predation need conservative content flags plus an
approved fallback; they must never appear as an unreviewed surprise improvisation.

Every story exposes a child-visible choice:

1. original approved text;
2. deterministic curator-defined substitutions;
3. a surprise-safe bounded remix, only when the item permits adaptation.

Generate 100–200-word scenes from reviewed story cards, finish and safety-check
the whole scene before TTS, and never stream unchecked child-facing tokens.
Prefer existing human translations, prioritizing French before Spanish. For this
prototype, the owner accepts LLM-based French and Spanish review when fluent-human review is not
available. Mark that output **lower assurance** in its manifest and maintenance
UI, retain deterministic language/content checks, and always keep an approved
local fallback. This prototype allowance is not equivalent to fluent-human
validation. Keep names/session choices in volatile memory unless an adult
explicitly saves a placeholder-based favorite.

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

An authorized adult may start a text-only session against a separately billed,
documented API. That route requires adult authentication, visible online state,
provider/destination and spend limits, and an explicit end-session control. It
does not authorize unattended live child/cloud companionship. The router may
send only locally produced, redacted text: replace names, school/contact data,
and precise locations with opaque placeholders and reinsert them locally. Use
small request budgets, short timeouts, a circuit breaker, local output safety
checks, and immediate local fallback.

The default local adult-mode authority is a keyed switch or a control inside a
locked compartment; an exposed button by itself is not authentication. Remote
activation is acceptable only through an authenticated administration channel
with automatic expiry, a visible cart-side indicator and immediate local revoke.

Z.AI Coding Plan and ChatGPT/Codex subscriptions are development entitlements,
not embedded application API funding. Do not place their session credentials on
the cart or automate consumer coding clients as the runtime assistant.

Raw audio, images, video, and full source books stay local unless a human gives
contemporaneous consent for one bounded artifact, provider, and purpose through
an explicit visible control. Around children, require an adult. A blanket toggle
or spoken “yes” alone is not an adequate media-export control.

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
| `neko-sensors` | front/rear Reolink and four-sector C4001 health plus ephemeral metadata | no proactive greeting; voice remains |
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
  and board-built FP32/FP16 engines; deterministic numerical gates and model-only
  timing pass, while real-camera and combined-workload acceptance remains.
- Keep the measured 18.63-token/s GGUF/llama.cpp GPU path as an on-demand
  alternate; complete actual reboot readiness and full-stack coexistence checks.

Exit: package integrity, checksums, service health/restart, memory audit, and
operations rollback are recorded.

### 1. Geometry, power, privacy, and interaction survey

- Complete empty and occupied front/rear/both-side dimensioned cart survey;
  front/rear panorama,
  four radar-pod, microphone, speaker, shaker, network, and electronics-bay
  mounts. Confirm the known approximately 7-ft roof underside and 3.5–4.5-ft
  child target band at the actual mounting locations.
- Record all four series-connected battery labels, BMS/solar/charger/disconnect,
  full/rest/loaded voltage, configured BMS limits, controlled shutdown threshold,
  the two generic converter input connections, accessory rails, grounding,
  connectors, protection, continuous/peak budget, cable routes, and ignition
  behavior. Isolate the generic modules; do not operate them across the full
  bank or a midpoint. Confirm every proposed converter range with margin.
- Resolve the DDR-240 installation manual's required vertical/input-down,
  dry Pollution Degree 2, and FG-to-PE conditions. A cart chassis is not
  automatically PE; have a qualified mobile-DC installer define or reject the
  manufacturer-compliant bonding scheme, including the RSD chassis FG.
- Select the protected 24-to-5 V radar/aggregator stage, the regulated audio
  stage or wider-margin amplifier, and an isolated full-pack measurement path
  for the runtime 180 W policy. Account for each in the final BOM and loss budget.
- Design staged startup/precharge or inrush limiting for the candidates' typical
  30 A + 20 A + 20 A input pulses and coordinate it with the BMS, switches,
  conductors, and fuse time-current curves.
- Determine whether the present hard switch has an auxiliary/remote-enable path;
  design normal orderly shutdown with measured hold-up while retaining an
  immediate, qualified-and-verified DC-rated service/emergency disconnect.
- Record solar-panel/controller models and structural attachment points; roof
  height/posts/overhang, occupied sightlines, and shaded electronics-bay space.
- Record storage/overnight exposure, speed/noise, cooldowns and acceptable blind
  zones. Ambient 0–40 C, no salt, cloth cleaning, one speaker, parked-only
  proactive greeting and <=10-ft interaction radius are decided.
- Finalize privacy indicators/mutes and owner/history controls. The story policy
  allows reviewed conflict and folklore/religion, excludes serious grief and
  extreme bathroom humour, and prioritizes French before Spanish.
- At checkout, confirm arrival to BC V9G 1L8 within seven
  days, taxes/shipping, and stock for every camera, radar, audio, power, network,
  and enclosure line. Dispatch time alone is not sufficient.

Exit: the opposing-camera/four-radar layout has an occupied coverage sketch;
the 2D roof-lidar path is explicitly deferred; DC/DC, network, cable, and
enclosure parts can be selected without guessing; the complete checkout stays
at or below CAD 2,000 landed and every critical part meets the one-week ETA.

### 2. Bench audio minimum

- Install the locally stocked four-mic XVF3000 array, Soberton XPCB-12BT,
  Visaton FR 8 WP, and low-level TT25-8 body shaker on a protected bench supply.
- Pin firmware and ALSA identities; tune echo delay and barge-in.
- Build/evaluate Neko Neko, VAD, EN/FR/ES ASR, TTS voices, canned sounds, limiter,
  Bluetooth-disabled AUX behavior, and fail-silent behavior. Keep XVF3800 as a
  later lifecycle upgrade rather than a schedule dependency.

Exit: wake targets, false wakes, word error, first-audio latency, interruption,
SPL/vibration, fixed driver-safe limits, RAM/power/temperature, restart, and
eight-azimuth tests pass within the 35 W audio allocation.

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
  French first and Spanish afterward, with existing human translations where
  possible, otherwise the
  owner-accepted, explicitly labelled lower-assurance LLM prototype review.
- Enforce the five-minute maximum and light/non-scary default. Allow reviewed
  age-appropriate conflict and folklore/religion; exclude serious grief and
  extreme bathroom humour; keep conservative fallbacks for suspense, threat and
  predation.

Exit: every visible item has a source/license/hash/content review; offline exact
and deterministic modes survive Gemma failure; generated scenes are fully checked
before speech; language assurance is visible; no story exceeds five minutes.

### 5. Social perception

- Bench one Reolink Duo 3V PoE panorama and one C4001 before drilling. Prove
  local RTSP/ONVIF, H.264 substream decode, local person events, camera feature
  disablement, isolated networking, and no media egress.
- Add the opposing panorama and all four radar sectors through the wired
  aggregator; keep the camera network without a default route or DNS.
- Emit metadata only and implement deterministic dwell/approach/cooldown.
- Mount and field-map 360 degrees with occupants, children/adults, groups,
  seams/occlusion, sun/night, rain, dirt, vibration, radar interference, cart
  reflections, motor noise, and intended weather.

Exit: range/coverage map and blind zones are explicit; no repeated solicitation;
camera confirmation gates spoken greetings; unplugged/blocked sensors degrade
without harming voice. Lidar remains absent from the revision-one dependency
graph; an inverted 3D unit is a separately gated later experiment.

### 6. Combined cart soak and launch hardening

- Run perception + wake/ASR + Gemma + TTS for at least two hours, then longer
  representative duty cycles.
- Measure P50/P95 interaction latency, DRAM/NvMap, dropped audio/frames/events,
  scoped Neko input power, separate lights-on coexistence behavior,
  minimum-battery behavior, temperature/throttling, and logs.
- Test ten cold boots, USB reorder/unplug, network loss, storage-full behavior,
  process crashes, corrupt/missing assets, mute/privacy state, and fail-silent
  amplifier behavior.
- Test normal switch-off through confirmed OS halt and delayed converter cutoff,
  low-pack pre-shutdown, and separately the recovery path after unavoidable
  immediate power loss.
- Measure each converter's startup pulse with an appropriate current probe. Test
  the designed sequencing/precharge or inrush limiter against BMS behavior,
  contactor/switch making duty, conductor limits, and fuse time-current curves;
  do not use the running watt meter to characterize a millisecond-scale pulse.
- Exercise the worst approved simultaneous workload: five-minute story audio,
  purr, wake/ASR, Gemma, both camera verification paths, four radar sectors, and
  selected ZipDepth sampling. Measure all three proposed full-pack converter
  inputs with non-Neko loads isolated, trigger staged software shedding near
  180 W, and reject any post-start running mode or ordinary workload transient
  above 200 W. Repeat with lights enabled as a separate shared-rail interference
  test.

Exit: the offline minimum consistently starts and the scoped Neko system remains below
measured power/thermal/memory limits with documented recovery. Do not infer
traction runtime from this accessory-power test.

### 7. Adult-authenticated text-only cloud mode

- Obtain a separately billed supported API account/budget; implement adult
  authentication, redaction, provider/destination and spend allowlists, timeouts,
  circuit breaker, local safety checks, visible state, and explicit session end.
- Use a keyed switch or a control inside a locked compartment for local adult
  enablement. Remote enablement must use an authenticated administration channel,
  expire automatically, show a cart-side indicator and remain locally revocable;
  a plain exposed button is not authentication.
- Start with adult-operated pre-generation, current-information requests, or
  adult-authenticated text sessions, not unattended live child/cloud companionship.
- Keep raw camera, audio, and source-book media local absent contemporaneous
  per-artifact human consent; require an adult when children are involved.

Exit: packet capture proves only permitted redacted text leaves; every provider
failure immediately falls back locally; no consumer subscription/session
credential is embedded; raw media cannot egress through the text route.

## Next owner inputs

The next purchase cannot be finalized without:

1. photos/make/model of all four battery labels and a wiring diagram showing
   the known series topology, BMS, shunt, main fuse/disconnect, charger/solar
   controller, full/rest/loaded voltage, configured limits, controlled shutdown
   threshold and prospective fault current;
2. an urgent trace showing whether each incompatible generic 4–38 V converter
   input is across the full string, a two-battery midpoint, or another regulated
   rail, plus present fuse/wire details; whether the hard switch immediately cuts
   the pack or exposes a remote/auxiliary contact; and its make/model/DC ratings;
3. checkout-confirmed arrival within seven days to the supplied BC V9G 1L8
   destination for the Reolink pair, four radars, XVF3000, amplifier, speaker,
   transducer, converters, switch, enclosures and fabrication dependencies;
4. qualified full-pack fuse/holder/interrupt ratings, FG/PE and chassis-bonding
   disposition, startup-inrush sequencing/limiting, shutdown controller/relay,
   isolated runtime power measurement, protected 24-to-5 V sensor conversion,
   regulated audio supply/OVP, and final cable lengths/conductor sizing. The
   direct-12 V/SW-005 camera topology is selected provisionally;
5. complete empty/occupied front/rear/both-side photos or sketch showing the
   approximately 7-ft roof, posts, overhang, bodywork, panel/controller models,
   outboard structural camera mounts, four outboard radar pods, shaded
   electronics bay and panorama seams;
6. storage temperature, overnight exposure and acceptance of orderly degraded
   shutdown from 35–40 C because the Jetson developer kit is rated only to 35 C;
7. greeting cooldowns and acceptable remaining seams/blind zones for children,
   adults, groups, pets and partially occluded people; parked-only proactive
   greeting and <=10-ft radius are decided;
8. preferred 5–7 versus 8–10 English/French mix, memory/retention and generated-
   history retention; French-before-Spanish and the story content boundaries are
   decided;
9. exact keyed/locked local adult control, remote-admin mechanism, supported
   billed API provider/project, spend ceiling, normally-present-adult assumption,
   and visible cloud/privacy controls;
10. target maximum SPL at 1 m, quiet hours, microphone electrical kill, camera
   service covers/shutters, and the schedule, consent, release, and retention
   terms for the prospective recording under the owner-approved source-voice
   plan; one voice speaker is decided;
11. who may save a favorite story variant, whether spoken attribution is
    acceptable, and whether traditional/Indigenous/sacred stories must remain
    original-only without explicit source and cultural-review approval.

The budget decision is no longer open: the ceiling is CAD 2,000 landed for added
hardware, with the current provisional planning range at CAD
1,625.13–1,947.53 under an assumed 12% BC tax rate. Checkout price, delivery, and
mechanically dependent allowances remain gates. The four-series-battery
statement is also recorded, but
it does not substitute for label/BMS/converter inspection and is not authority
to calculate or promise traction runtime.

See the detailed electrical/environmental checklist in
[`docs/research/2026-07-13-power-weather.md`](../research/2026-07-13-power-weather.md),
the audio questions in
[`docs/research/2026-07-13-audio-voice.md`](../research/2026-07-13-audio-voice.md),
and the complete story-policy questions in
[`docs/research/2026-07-13-stories-cloud.md`](../research/2026-07-13-stories-cloud.md).
