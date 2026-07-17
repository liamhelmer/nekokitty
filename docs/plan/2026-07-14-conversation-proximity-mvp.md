# Local conversation and camera proximity MVP — 2026-07-14

This plan turns the already-running Gemma service, C922 camera/microphone, and
Ora Bluetooth headset into a pre-production conversational and social-perception
bench. It preserves the production interfaces: the C922 becomes Reolink RTSP,
Bluetooth playback becomes reSpeaker/Soberton audio, and camera-only proximity
is later confirmed by C4001 radar. No component in this plan controls cart motion
or provides a vehicle-safety function.

## Decision summary

Build two independent event loops joined only by the deterministic behavior
service:

```text
C922/reSpeaker audio -> VAD/wake -> streaming ASR -> typed behavior policy
  -> loopback Gemma -> complete checked text -> local TTS -> bounded audio queue

C922/Reolink frames -> person detector -> ephemeral tracker -> calibrated
  ground-plane proximity/approach -> dwell/cooldown policy -> greeting request
  -> same behavior/audio path
```

Keep the deployed CPU LiteRT Gemma service for the first combined build. A live
audit found 6,065,396 KiB available of 7,665,220 KiB total with no swap; Gemma
was the leading process at 1,669,854 KiB PSS. The generic Jetson memory tuner
selects llama.cpp Q4 as the absolute lowest-memory new-server choice, but this
project's LiteRT service is already locally measured, bounded, boot-ready, and
keeps the GPU free for vision. Reconsider the measured llama.cpp profile only if
the complete pipeline violates memory or latency gates.

## Conversation path

### Components

1. **Audio transport:** PipeWire targets by stable node name, initially C922
   microphone plus Ora playback. The headset is presently in mSBC HSP/HFP mode;
   it is adequate for functional testing but not a final audio-quality or latency
   result. Production swaps to the reSpeaker USB capture/playback interface.
2. **VAD and ASR:** pin sherpa-onnx and its pre-exported June 11, 2026
   `nemotron-3.5-asr-streaming-0.6b-560ms-int8` model first. The published bundle
   has roughly 627 MB encoder, 14 MB decoder, 9.1 MB joiner, and supports
   per-stream language selection/automatic language detection. NVIDIA describes
   the source 600M model as cache-aware streaming ASR for 40 locales, including
   English, Canadian/France French, and Spanish. Benchmark 160 ms against 560 ms
   only after the 560 ms quality baseline passes.
3. **Wake:** start the first integration with push-to-talk or an explicit local
   test trigger, then temporarily accept a recognized `Neko Neko` transcript as
   the session opener. Train and validate a dedicated `Neko Neko` keyword model
   before continuous passenger use. openWakeWord has a custom-training utility,
   but its easy Colab path explicitly warns that deployment performance may be
   low; sherpa-onnx keyword spotting remains the active-maintenance comparison.
4. **Dialogue:** call the existing fixed `gemma-4-e2b-it` loopback endpoint.
   The behavior service supplies the persona, turn state, child policy, and
   bounded request. It owns `stop`, `cancel`, `mute`, volume, exact stories, and
   sound actions without asking the model.
5. **TTS:** use the owner-selected KittenTTS Micro/Kiki 1.2x resident worker for
   English; keep pinned Supertonic 3 for French and Spanish. The English worker
   accepts only a complete checked string over a private Unix socket, then emits
   sentence-sized PCM frames. Keep Piper as the smaller deterministic fallback.
   Do not speak unchecked model tokens.
6. **Orchestration:** use Pipecat's frame pipeline for audio/STT/LLM/TTS flow,
   with thin local adapters for sherpa-onnx, the fixed Gemma endpoint, and
   Supertonic. Keep Neko's policy/state in typed project code, not in Pipecat or
   prompt history.

### First conversational acceptance gate

- Entirely offline after artifacts are pinned.
- C922 microphone to local transcript in English; then French; then Spanish.
- Local Gemma produces one short, child-appropriate Neko reply.
- First acknowledgement sound within 250 ms and first generated speech within
  the owner's few-second tolerance.
- `stop`/`cancel` interrupts playback without an LLM round trip.
- Missing ASR, Gemma, or TTS produces a canned local response and does not wedge
  the audio device.
- No raw audio or transcript log; only timing, health, selected language, and
  error codes.

## Camera proximity path

### Detector choice

Use **RF-DETR Nano** as the revision-one detector. The exact 1.8.3 release was
exported at 384x384 and built locally as a batch-1 FP16 TensorRT 10.16.2 engine.
It measured 9.48 ms model-only and 9.63 ms with synthetic host transfers (about
105 inferences/s). A live C922 PyTorch reference run detected a person at 0.898
confidence without retaining the frame. The new TensorRT loop runs at a bounded
5 Hz, retains no frames, and publishes only ephemeral box/track metadata.

Ultralytics YOLO26n was built only as an isolated comparison. Its local FP16
engine measured 3.19 ms model-only and 3.37 ms with transfers, but its current
AGPL-3.0/Enterprise terms are incompatible with representing an integrated
dependency as part of this MIT project. Making Neko public does not relicense
YOLO. RF-DETR is fast enough by a wide margin, has Apache-2.0 code/model terms,
and preserves the intended MIT distribution, so it wins the whole-project
decision despite YOLO26's smaller/faster engine. Do not import Ultralytics into
the Neko runtime or distribute its weights with this repository.

### Proximity algorithm

1. Decode the C922 to a bounded 5–10 fps worker; retain no frames by default.
2. Emit only person confidence and bounding boxes from the detector.
3. Feed detections to the included metadata-only centroid tracker for the parked,
   low-rate first revision. Replace it with ByteTrack only if multi-person field
   tests show that the simpler association is insufficient; do not add face
   recognition, identity, or persistent trajectories.
4. Calibrate the parked camera against marked ground positions at 4, 6, 8, and
   10 ft. Use the bottom-centre of each person box and a fitted ground-plane
   homography/look-up curve to estimate social-zone distance. This works only for
   the calibrated camera pose and approximately planar ground; label it
   `estimated`, not metric truth.
5. Estimate approach from a filtered decrease in ground-plane distance, with
   bounding-box growth as a secondary consistency signal. ZipDepth may add a
   foreground/background consistency score but cannot supply metres.
6. Drive `absent -> candidate -> nearby -> engaged -> cooldown -> absent` with
   minimum confidence, stable-track count, approach/dwell, parked-state, quiet
   mode, conversation ownership, and global/per-track cooldowns.
7. Initially generate an event/log and a quiet chirp. Enable a spoken greeting
   only after false-trigger review. When production radar arrives, require radar
   range consistency plus camera confirmation for spoken greetings.

### First camera acceptance gate

- One person at each 4/6/8/10-ft mark is detected across centre and edge zones.
- Two people receive ephemeral tracks without repeated greeting events.
- Sitting, partial occlusion, empty scene, photo/poster, pet, and cart reflection
  tests have documented false positives/negatives.
- No frame/image/video persists and no media leaves the host.
- Camera removal disables proactive greeting while voice conversation continues.
- Camera-only estimates are never logged or exposed as safety distance.

## Service and implementation sequence

1. **Complete:** add typed event schemas and a deterministic `neko-behavior` state machine,
   using synthetic speech/person events in unit tests.
2. **Complete for the bench:** install sherpa-onnx and the single INT8 Nemotron 560 ms artifact in an
   isolated, hash-pinned environment; benchmark file and live microphone paths.
   File benchmarks and memory-only ALSA/PipeWire transport pass; an intelligible
   owner-spoken Bluetooth sample is still an acceptance item, not an install gate.
3. **Complete for the bench:** install Supertonic 3 in a separate pinned environment; benchmark English,
   French, and Spanish to a non-recording sink, then Ora playback.
4. **Part complete:** the deterministic session/wake core, Gemma adapter, manual
   text trigger, transcript-gated `Neko Neko`, and opt-in TTS playback exist.
   A unified live audio turn loop, interruption-capable playback queue, VAD, and
   trained wake model remain. Pipecat is still optional rather than installed.
5. **Complete:** pin RF-DETR Nano source/weights, export ONNX off the normal
   service path, build TensorRT on this Jetson, and implement the C922 adapter.
6. **Part complete:** ephemeral tracking and tested social state are present.
   Physical calibration and multi-person field acceptance await installed cart
   cameras, so metric-gated spoken greetings remain disabled.
7. **Part complete:** short Gemma + RF-DETR + live ASR coexistence and the
   C922/Ora hardware-in-the-loop paths pass. Run the remaining latency,
   production-device, device-unplug, worker-crash, network-loss, thermal/power,
   and two-hour soak tests.
8. Only after those gates, install resource-bounded systemd units. Offline boot
   readiness must not depend on cameras, Bluetooth, network, or cloud APIs.

No new runtime should be enabled at boot until its standalone and combined gates
pass. Start ZipDepth only as a sampled experimental worker; it is not needed to
enable conversation or the first camera-proximity event loop.

### Bench update — 2026-07-16

- The non-retaining combined suite passed 90 C922 frames at 25.79 wall fps,
  webcam-microphone activity, and a 2.739-second Gemma response.
- The first positive TensorRT loop exposed and then regression-tested a missing
  `bottom_y_normalized` observation field. After the fix, one anonymous track
  remained stable for 18 seconds at 0.926–0.969 confidence. The box touched the
  lower image boundary, so this pose is unsuitable for ground-plane calibration;
  distance and approach correctly remained disabled.
- Ora mSBC playback and capture routes work. Supertonic F1 playback completed.
  Bounded PipeWire-to-ASR capture now works without retaining media and reports
  only RMS/peak levels, but the attempted samples contained no sustained speech.
  Repeat with an owner-timed phrase before checking the live-transcript gate.
- Keep all Neko application units disabled until the remaining step 7 gates pass.

### Optional MeowLLM experiment — 2026-07-16

MeowLLM was requested as a possible TTS sample, but upstream defines it as a
3.45M-parameter English text model, not a speech model. A safe, isolated
audition passed: its text was synthesized by the existing Supertonic worker and
played over Ora. Do not place MeowLLM on the assistant, story, translation, or
safety path; upstream explicitly excludes those uses. If retained, evaluate it
only as a bounded, non-factual cat-quip generator after Neko's complete-text
policy check. It remains an on-demand lab artifact with no service or integration
decision.

### KittenTTS Kiki and cat-sound palette — 2026-07-16

KittenTTS Micro 0.8/Kiki at 1.2x is now the selected English voice. The owner
heard virtually no quality difference from Mini in a back-to-back Ora comparison
while Micro cut synthesis time roughly in half. The enabled resident worker
verifies pinned artifacts, preserves punctuation, warms at start, and emits the
first sentence over a private Unix socket in about 1.1 seconds for the accepted
informal three-sentence audition. Supertonic remains the French/Spanish path.
The production speaker, cancellation/audio arbitration, cold boot, and combined
workload soak are still required; do not use mutable Hub downloads.

Build nonverbal cat audio as a deterministic soundboard before attempting live
generation:

1. **Completed 2026-07-16:** human-review all 24 owner-curated Freesound sources.
   The structured ledger records 19 keep/priority candidates, two secondary
   maybes, one manual-only novelty, and two sources not selected for standalone
   use. All files have non-destructive ReplayGain measurements. Twenty-three
   played in full; item 22 was stopped once the owner had enough evidence to
   reject standalone use. The manifest still disables every item because review
   approval is not delivery mastering or hardware acceptance.
2. Use CatMeows brushing and food recordings only to fill remaining meow gaps;
   exclude isolation calls by default. Add individually cleared Wikimedia clips
   only for missing trills/chirps. Preserve per-file provenance in the manifest.
3. **Bench build completed 2026-07-16:** made the first derived palette from the
   strongest reviewed sources.
   The 20 `keep_*` originals are now versioned under
   `assets/cat-sounds/originals` with per-file Creative Commons provenance. Keep
   annotations current in `docs/cat-sounds/CAT_SOUNDS_MASTER.md` and track all
   transformations in `docs/cat-sounds/PROCESSING_AND_REMIX_QUEUE.md`.
   Start with items 10, 14, and split item 21 for meows; items 17, 24, 23, and 18
   for purrs. The result is 25 hash-pinned mono 48 kHz/24-bit PCM bench
   candidates with exact recipes, TASL/change notices, a -23 LUFS-I/-2 dBTP
   policy, and integrity/mastering tests. Then add items 1, 3, 4, 6, 7, 9, 13,
   15, 5, 11, and 16 only where
   they fill a distinct emotional/action slot. Preserve lossless originals;
   trim the documented tails/impacts/noise, measure integrated loudness and
   oversampled true peak, and emit attribution alongside every derived asset.
4. **Part complete:** a fail-closed deterministic semantic allowlist, bounded
   gain/cooldown/duration, and separate provisional speaker/transducer candidates
   exist. Every action remains disabled until derived listening and production
   hardware acceptance. An LLM may
   request `friendly_trill` or `playful_purr`, but the supervisor chooses the
   exact approved asset and safe gain. Keep item 8 manual-only.
5. Stable Audio 3 Small SFX was benchmarked with other model workers stopped.
   Although the fast ARM profile beat real time, both owner auditions failed for
   distress/choppiness and the higher-quality profile exceeded memory. Raw
   generation is closed for revision one. Concentrate on the curated palette and
   bounded DSP variants; no generated audio enters unattended playback.

Exact artifacts, benchmark evidence, licenses, and acceptance gates are in
`docs/research/2026-07-16-kittentts-cat-audio.md`.

## Current sources checked through 2026-07-16

- NVIDIA Nemotron 3.5 ASR model card:
  <https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b>
- sherpa-onnx Nemotron streaming exports and microphone example:
  <https://k2-fsa.github.io/sherpa/onnx/nemo/nemotron-streaming.html>
- Supertonic 3 official repository/server documentation:
  <https://github.com/supertone-inc/supertonic>
- Pipecat frame-pipeline documentation:
  <https://docs.pipecat.ai/pipecat/learn/pipeline>
- openWakeWord custom training notes:
  <https://github.com/dscripka/openWakeWord>
- RF-DETR official repository and model/license table:
  <https://github.com/roboflow/rf-detr>
- RF-DETR ONNX export documentation:
  <https://rfdetr.roboflow.com/latest/learn/export/>
- Ultralytics TensorRT export documentation and current license guidance:
  <https://docs.ultralytics.com/integrations/tensorrt>
  and <https://www.ultralytics.com/license>
- KittenTTS 0.8.1 repository and evaluated model cards:
  <https://github.com/KittenML/KittenTTS>
  plus <https://huggingface.co/KittenML/kitten-tts-mini-0.8>,
  <https://huggingface.co/KittenML/kitten-tts-micro-0.8>, and
  <https://huggingface.co/KittenML/kitten-tts-nano-0.8-int8>
- CatMeows version 1.0.2 record:
  <https://doi.org/10.5281/zenodo.4008297>
- Stable Audio 3 Small SFX repository and model card:
  <https://github.com/Stability-AI/stable-audio-3>
  and <https://huggingface.co/stabilityai/stable-audio-3-small-sfx>
