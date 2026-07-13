# Owner decisions — 2026-07-13

These answers supersede the corresponding open questions in
[`docs/questions.md`](../questions.md). They are durable deployment constraints,
not assumptions. Revisit them explicitly if Neko's use or hardware changes.

## Deployment and licensing

- Neko is strictly personal and noncommercial. The current Audex noncommercial
  license is acceptable for this revision. Recheck every model, checkpoint,
  story, recording, and voice license before any public, promotional, paid, or
  commercial use.
- Both Gemma 4 E2B and Nemotron-Labs-Audex-2B must remain installed on the NVMe,
  but they do not need to be resident in DRAM simultaneously. Gemma is the normal
  boot profile; Audex is a stopped/selectable experiment until a measured
  quantized configuration fits.
- No separate 24–32+ GB NVIDIA host is available for the full Audex path.
- Permanent headless boot is approved. SSH/console are the administration paths;
  graphical mode is rollback-only.
- Installing the CUDA compiler/toolkit components, TensorRT, and required system
  dependencies is approved.
- The project is a Git repository and may be published to the private GitHub
  repository <https://github.com/liamhelmer/nekokitty>. Never commit model
  weights, caches, credentials, private media, recordings, or transcripts.
- The root NVMe is the durable model/cache store. Large artifacts stay outside
  this repository and are addressed by exact revision and checksum.

## Vehicle and safety boundary

- The cat-shaped golf cart carries people and is manually driven in this
  revision. It will not move autonomously. Autonomous motion is explicitly a
  possible future revision, not current scope.
- No cart control/interface is currently in use. Perception is for social
  behavior only and must not command, inhibit, or claim to provide safe motion.
  Any future motion integration needs an independent safety architecture,
  controller, emergency stop, hazard analysis, and separate authorization.

## Perception

- Near-360-degree social perception is desired. The initial idea was three
  wide-angle cameras near the front under the roof, but the owner is open to a
  more effective arrangement and to depth/radar alternatives.
- There is no purchased 3-D camera or final sensor parts list. Short schedule,
  low power, and an approximate USD 2,000 ceiling for the added system are hard
  design pressures. Complexity or power that prevents shipping is unacceptable.
- ZipDepth remains required for evaluation but is not accepted as metric range
  or a safety sensor. Sensor selection will use a costed prototype/premium ladder
  and measured blind-zone, latency, power, weather, and compute results.

## Interaction, voice, and stories

- A response within a few seconds is acceptable.
- Candidate wake phrases are “Neko Neko” and “Hello Kitty.” Trademark and false
  activation considerations must be reviewed before shipping the latter;
  “Neko Neko” is the default custom wake-word prototype.
- English is required. French and Spanish are desirable and must be evaluated
  with local ASR/TTS, not silently delegated to cloud-only services.
- Neko's character is cute, motherly, slightly mischievous, and playful. The
  owner has no source recordings yet but can create consented recordings for a
  local custom voice.
- No story library exists. Build one from public-domain, Creative Commons, or
  otherwise expressly licensed sources whose exact narration and remix rights
  are recorded per item. Child-directed remixing may change names, settings, and
  scenarios, subject to a deterministic age-appropriate policy layer.

## Offline/online and privacy

- Features are offline-first. Every shipped feature needs a useful local mode;
  omit features that are inherently cloud-only. Online models may enhance, but
  never become prerequisites for, core interaction.
- Z.AI and Codex consumer subscriptions are available for development. They are
  not presumed to grant embedded runtime/API rights; use only separately
  documented supported APIs and credentials if online mode is later enabled.
- Transcript text may leave the cart under policy. Images and audio may leave
  only after explicit human-in-the-loop consent. Default operation must keep raw
  camera/audio data local and avoid storing it.
- There is no separate requested physical offline switch. The hard electrical
  system power switch is the owner's offline control. This does not remove the
  need for visible microphone/cloud state and recommended hardware microphone
  mute/camera shutters for bystander privacy.

## Authorized upstream action

- Reporting the reproducible LiteRT-LM Jetson GPU crash upstream is approved.
  The report must contain only non-sensitive hardware/software facts and minimal
  reproduction details.

## Still open before hardware purchase or field use

- Exact cart environment, weather exposure, speed/load, available DC rails,
  sustained battery/thermal budget, and enclosure airflow.
- Exact social distance/cooldown behavior, operation while moving, and treatment
  of children, groups, pets, and partial occlusion.
- Final camera/radar/microphone/speaker/amplifier/transducer selection and mounting.
- Story audience/age modes, owner controls, generated-history retention, and the
  final content manifest.
- Mic electrical kill, camera shutters, visible privacy indicators, raw-data log
  policy, administration/update/recovery policy, and cloud API budget/provider.
