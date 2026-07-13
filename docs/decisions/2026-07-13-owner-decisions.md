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

## Power, roof, and operating environment

- The traction bank is LiFePO4, described as 48 V and four 270 Ah batteries.
  This wording does not yet establish whether the units are nominal-12.8 V
  batteries in series, complete 48 V packs, or another arrangement; no total
  energy/runtime calculation or protection choice may assume the topology.
- Two DC/DC circuits already exist from the array: a 24 V output for lights and
  accessories and a 19 V output for the Jetson. Both must be confirmed as
  full-pack-fed converter outputs, never loads from a series-string midpoint.
- Prefer 24 V distribution for new accessories. Add a 12 V branch only for an
  identified 12 V-only device. Keep the Jetson on its separate regulated 19 V
  branch and do not share that output with lighting or audio loads.
- The roof is approximately 4 ft wide by 8 ft long and its upper surface is
  solar panels. Mounts and cable routes must not shade, drill, bond to, obstruct,
  or trap heat against the panels without the panel manufacturer's approval.
- Rain, dust/dirt, temperature, and direct sun are all normal design conditions.
  Exposed parts, connectors, apertures, enclosures, drainage, condensation, UV,
  cleaning, and hot-sun soak therefore require explicit acceptance tests.
- The full electrical and weather integration decision, evidence requirements,
  and manufacturer-source ledger are in
  [`docs/research/2026-07-13-power-weather.md`](../research/2026-07-13-power-weather.md).

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
- The first-release audience is ages 5–10. Provide separate approximately 5–7
  and 8–10 presentation lanes rather than treating that span as one reading
  level. The collection theme is cats of all kinds, including wild felids; a cat
  must be central to each enabled story rather than an incidental keyword hit.

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
- There is no separate requested radio/offline switch. The owner intends the
  hard electrical system switch to make Neko fully offline by removing power,
  but its contacts and timing have not been inspected. If it immediately cuts
  the traction supply, it is only a candidate service/emergency disconnect until
  a qualified installer verifies its DC voltage/current/interrupt rating,
  topology, location, and intended duty. Add a separate normal control that
  requests Linux shutdown before hardware-delayed converter cutoff. This does
  not remove the need for visible microphone/cloud state and recommended
  hardware microphone mute/camera shutters for bystander privacy.

## Authorized upstream action

- Reporting the reproducible LiteRT-LM Jetson GPU crash upstream is approved.
  The report must contain only non-sensitive hardware/software facts and minimal
  reproduction details.

## Still open before hardware purchase or field use

- Exact battery models/topology/BMS, full/rest/loaded voltage, configured BMS
  limits and controlled shutdown threshold, both
  converter models and input wiring, protection/grounding, measured rail noise,
  sustained power/thermal budget, and enclosure airflow.
- Exact minimum/maximum/storage temperature, rain/overnight exposure, washing
  method, salt exposure, and solar-panel/controller/mounting details.
- Exact social distance/cooldown behavior, operation while moving, and treatment
  of children, groups, pets, and partial occlusion.
- Final camera/radar/microphone/speaker/amplifier/transducer selection and mounting.
- Story duration/language mix and content boundaries within the fixed 5–10
  audience, owner controls, generated-history retention, and final cat-story
  manifest.
- Whether the approximate US$2,000 added-system ceiling includes tax, shipping,
  duty, and fabrication; the weather-preferred PoE camera path nearly consumes
  that full pre-tax hardware allowance.
- Mic electrical kill, camera shutters, visible privacy indicators, raw-data log
  policy, administration/update/recovery policy, and cloud API budget/provider.
