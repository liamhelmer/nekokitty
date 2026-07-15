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
5. **TTS:** evaluate pinned Supertonic 3 first. Its official release is a 99M
   parameter, CPU/ONNX, 31-language model with English, French, and Spanish and a
   loopback HTTP server exposing native and OpenAI-compatible speech endpoints.
   Keep Piper as the smaller deterministic fallback. Generate/check a complete
   child-facing sentence before synthesis; do not speak unchecked token streams.
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

1. Add typed event schemas and a deterministic `neko-behavior` state machine,
   using synthetic speech/person events in unit tests.
2. Install sherpa-onnx and the single INT8 Nemotron 560 ms artifact in an
   isolated, hash-pinned environment; benchmark file and live microphone paths.
3. Install Supertonic 3 in a separate pinned environment; benchmark English,
   French, and Spanish to a non-recording sink, then Ora playback.
4. Add the Pipecat turn loop and existing Gemma adapter. Begin with manual
   trigger, then transcript-gated `Neko Neko`, then a trained wake model.
5. **Complete:** pin RF-DETR Nano source/weights, export ONNX off the normal
   service path, build TensorRT on this Jetson, and implement the C922 adapter.
6. **Part complete:** ephemeral tracking and tested social state are present.
   Physical calibration and multi-person field acceptance await installed cart
   cameras, so metric-gated spoken greetings remain disabled.
7. Run combined memory, CPU/GPU, latency, power, thermal, device-unplug, worker-
   crash, network-loss, and two-hour soak tests.
8. Only after those gates, install resource-bounded systemd units. Offline boot
   readiness must not depend on cameras, Bluetooth, network, or cloud APIs.

No new runtime should be enabled at boot until its standalone and combined gates
pass. Start ZipDepth only as a sampled experimental worker; it is not needed to
enable conversation or the first camera-proximity event loop.

## Current sources checked 2026-07-14

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
