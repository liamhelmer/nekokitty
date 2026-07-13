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
- The roof underside is about 7 ft high, slopes lightly from a higher front to a
  lower rear, and has open sides. Representative children are about 3.5–4.5 ft
  tall. A level roof-mounted 2D lidar therefore scans over them; an inverted
  hemispherical 3D lidar is geometrically viable.
- There is no purchased 3-D camera or final sensor parts list. All added parts
  must fit a **CAD 2,000 landed ceiling including tax and shipping**, excluding
  already-owned Jetson/storage/C922 hardware, and must be obtainable within one
  week. Hardware cost is the primary selection pressure.
- The camera/lidar/radar, microphones, speakers/transducer, and Jetson together
  must remain at or below **200 W running**. The current one-week design target
  is materially lower; nameplate arithmetic must be confirmed by a simultaneous
  measured load test.
- The current purchase recommendation is two opposing outdoor 180-degree cameras
  plus four inexpensive radar sectors, with no lidar in the one-week build. A
  roof-inverted Unitree-class 3D lidar remains the first later lidar experiment.
  No part has been ordered yet.
- ZipDepth remains required for evaluation but is not accepted as metric range
  or a safety sensor. Sensor selection will use a costed prototype/premium ladder
  and measured blind-zone, latency, power, weather, and compute results.
- The dated Canadian comparison, exact arithmetic, stock evidence, geometry and
  purchase gates are in
  [`docs/research/2026-07-13-canadian-one-week-bom.md`](../research/2026-07-13-canadian-one-week-bom.md).

## Power, roof, and operating environment

- The traction bank is LiFePO4, described as 48 V and made from four 270 Ah
  batteries connected **in series**. Exact battery labels, nominal/charge limits,
  BMS rules, interconnects and protection remain unverified. The project does not
  need an overall cart energy/runtime calculation; it still needs those facts for
  safe converter, fuse and shutdown design.
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
- Speakers and the body transducer together must be rated at **100 W or less**.
  The current one-speaker/one-puck recommendation totals 30 W RMS and is limited
  to about 27 W combined program output.

## Interaction, voice, and stories

- A response within a few seconds is acceptable.
- **`Neko Neko` is the approved activation phrase.** “Hello Kitty” is retired
  from the revision-one wake-word plan.
- English is required. French and Spanish are desirable and must be evaluated
  with local ASR/TTS, not silently delegated to cloud-only services.
- Neko's character is cute, motherly, slightly mischievous, and playful. The
  owner is willing to create consented source recordings for a local custom
  voice.
- No story library exists. Build one from public-domain, Creative Commons, or
  otherwise expressly licensed sources whose exact narration and remix rights
  are recorded per item. Child-directed remixing may change names, settings, and
  scenarios, subject to a deterministic age-appropriate policy layer.
- The first-release audience is ages 5–10. Provide separate approximately 5–7
  and 8–10 presentation lanes rather than treating that span as one reading
  level. The collection theme is cats of all kinds, including wild felids; a cat
  must be central to each enabled story rather than an incidental keyword hit.
- Every story is at most five minutes. The default tone is light and explicitly
  non-scary; suspense, threat and predation need conservative content flags and
  an approved fallback rather than surprise improvisation.
- For the prototype, the owner accepts LLM-based French and Spanish review rather
  than fluent-human review. This is a lower-assurance validation state and must
  be labelled as such in manifests and UI; it does not remove deterministic
  safety checks or the local approved-story fallback.

## Offline/online and privacy

- Features are offline-first. Every shipped feature needs a useful local mode;
  omit features that are inherently cloud-only. Online models may enhance, but
  never become prerequisites for, core interaction.
- Z.AI and Codex consumer subscriptions are available for development. They are
  not presumed to grant embedded runtime/API rights; use only separately
  documented supported APIs and credentials if online mode is later enabled.
- An authorized-adult, text-only session may use separately billed API access.
  This does not authorize raw audio/images, an embedded consumer-subscription
  credential, or unattended live child-cloud interaction. Adult authentication,
  visible state, redaction, provider and spend limits remain implementation gates.
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

- Exact battery models/BMS, full/rest/loaded voltage, configured BMS
  limits and controlled shutdown threshold, both
  converter models and input wiring, protection/grounding, measured rail noise,
  sustained power/thermal budget, and enclosure airflow.
- Exact minimum/maximum/storage temperature, rain/overnight exposure, washing
  method, salt exposure, and solar-panel/controller/mounting details.
- Delivery province/postal-code ETA for the one-week parts order and the exact
  24-to-12 V or active-PoE camera power/network topology.
- Exact social distance/cooldown behavior, operation while moving, and treatment
  of children, groups, pets, and partial occlusion.
- Checkout-confirmed camera/radar/microphone/speaker/amplifier/transducer stock,
  delivery, converter compatibility and final mounting.
- Story language mix, finer content boundaries within the fixed light/non-scary
  five-minute policy, owner controls, generated-history retention, and final
  cat-story manifest.
- Mic electrical kill, camera shutters, visible privacy indicators, raw-data log
  policy, administration/update/recovery policy, adult-authentication method,
  and cloud API budget/provider.
