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
- Using the owner-provided power interfaces and the low-power camera switch, the
  revised **provisional** planning range is **CAD 1,399.68–1,722.08 landed**,
  leaving **CAD 277.92–600.32** under the fixed ceiling. This remains an
  unitemized planning range until weather, mounting, cabling, protection, and
  fabrication lines are quoted. The simultaneous supplied-interface design
  allocation is **135 W**, still subject to the required, to-be-measured 200 W
  Neko-only acceptance cap.
- Proactive greetings are **parked-only** in revision one. The desired social
  interaction radius is no more than 10 ft (3.05 m). Because the selected C4001
  radar does not provide documented ranging below about 1.2 m (3.9 ft), its
  initial spoken-greeting gate is an approach/dwell in the approximate 4–10 ft
  annulus plus camera person confirmation; very-close interaction relies on the
  wake phrase and camera policy rather than invented radar precision.
- An owner-provided occupied-cart photograph confirms that roof posts/slats,
  passengers, and bodywork can block views from inside the passenger envelope.
  Put the two panorama optical faces below and just outside the front/rear post
  plane on structural roof-frame brackets, and put radar pods outside rather
  than behind the slats. The raw photograph was inspected transiently, contained
  identifiable people and embedded location metadata, and was not retained or
  committed. Empty and occupied front/rear/side survey photographs are still
  required before drilling.
- ZipDepth remains required for evaluation but is not accepted as metric range
  or a safety sensor. Sensor selection will use a costed prototype/premium ladder
  and measured blind-zone, latency, power, weather, and compute results.
- The dated Canadian comparison, exact arithmetic, stock evidence, geometry and
  purchase gates are in
  [`docs/research/2026-07-13-canadian-one-week-bom.md`](../research/2026-07-13-canadian-one-week-bom.md).

## Power, roof, and operating environment

- For hardware recommendation purposes, the owner supplies three black-box power
  interfaces: regulated **24 V up to 3 A**, regulated **19 V up to 3 A**, and
  **12–14 V up to 20 A** for accessories. The owner is responsible for upstream
  battery, conversion, grounding, protection, and wiring. Battery labels, a
  wiring diagram, BMS/charger details, and inspection of the existing converters
  are explicitly not prerequisites for this project's hardware recommendations.
- Existing lights draw 1–2 A from the 24 V interface. The Jetson currently draws
  about 1 A from 19 V. Treat the stated interface limits as controlling and
  verify the completed Neko load at those interfaces.
- Leave all new hardware off the already-loaded 24 V interface. Keep the Jetson
  and its USB microphone/data load on 19 V. Use 12–14 V for cameras/network,
  radar/control conversion, audio, cooling, and controls.
- The cameras are specified at 12.0 V, not a 12–14 V range. The Mean Well RSD
  pair was considered but rejected as the primary path because its published
  startup inrush is poorly matched to the supplied interfaces. The active camera
  recommendation is a RECOM `REC30K-2412SZ`: 9–36 V input, nominal 12 V/2.5 A,
  30 W, and 20–50 ms documented startup. That startup value is not an explicit
  capacitive-inrush guarantee, so cold-start testing remains required. A RECOM
  `R-78B5.0-2.0` supplies the 5 V radar/aggregator domain from 12–14 V. Its data
  sheet lists 2 A typical inrush and 10 ms typical startup under nominal-input
  test conditions, not maximum values at 12–14 V, so test it too. The
  Brainboxes `SW-005` and 10–25 V Soberton amplifier can use 12–14 V directly.
  The 24 V full-pack converter, dedicated replacement Jetson converter, and
  full-pack camera converter previously researched are no longer purchase items.
- The roof is approximately 4 ft wide by 8 ft long and its upper surface is
  solar panels. Mounts and cable routes must not shade, drill, bond to, obstruct,
  or trap heat against the panels without the panel manufacturer's approval.
- Operation is intended from 0–40 C, with no salt exposure. Moisture, rain,
  dust/dirt, sun and vibration remain normal; key electronics will be sheltered
  from direct rain and cleaning is by cloth rather than hose or pressure washer.
  Exposed parts, connectors, apertures, enclosures, drainage, condensation, UV,
  cleaning, and hot-sun soak still require explicit acceptance tests. The Jetson
  Orin Nano Developer Kit itself is manufacturer-rated only for 0–35 C, so the
  current developer-kit build must monitor enclosure temperature and degrade or
  shut down above its validated range; airflow cannot make a 40 C ambient meet a
  35 C rating. The owner approves orderly optional-worker shedding and shutdown
  at 35 C.
- The full electrical and weather integration decision, evidence requirements,
  and manufacturer-source ledger are in
  [`docs/research/2026-07-13-power-weather.md`](../research/2026-07-13-power-weather.md).
- Speakers and the body transducer together must be rated at **100 W or less**.
  The current one-speaker/one-puck recommendation totals 30 W RMS. Initially
  target about 14 W combined clean output at 12 V; treat 16–20 W combined as a
  14 V bench target, not a guaranteed output.
- One voice speaker is sufficient for revision one.

## Interaction, voice, and stories

- A response within a few seconds is acceptable.
- **`Neko Neko` is the approved activation phrase.** “Hello Kitty” is retired
  from the revision-one wake-word plan.
- English is required. French is the second priority and Spanish the third; all
  must be evaluated with local ASR/TTS rather than silently delegated to a
  cloud-only service.
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
  non-scary. Age-appropriate conflict and reviewed folklore/religion are allowed;
  serious grief and extreme bathroom humour are excluded. Suspense, threat and
  predation still need conservative content flags and an approved fallback
  rather than surprise improvisation.
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
- Adult mode may be enabled locally by a physical control or remotely while
  online. The recommended local authority is a keyed switch or a control inside
  a locked compartment; an exposed momentary button alone is not authentication.
  Remote enablement must use an authenticated administration channel, expire
  automatically, show a visible cart-side indicator, and remain locally
  revocable.
- Transcript text may leave the cart under policy. Images and audio may leave
  only after explicit human-in-the-loop consent. Default operation must keep raw
  camera/audio data local and avoid storing it.
- There is no separate requested radio/offline switch. The owner intends the
  hard electrical system switch to make Neko fully offline by removing power,
  while ordinary software operation should request a clean Linux shutdown where
  practical. Upstream switch and wiring design are owner-managed. This does not
  remove the need for visible microphone/cloud state and recommended hardware
  microphone mute/camera shutters for bystander privacy.

## Authorized upstream action

- Reporting the reproducible LiteRT-LM Jetson GPU crash upstream is approved.
  The report must contain only non-sensitive hardware/software facts and minimal
  reproduction details.

## Still open before hardware purchase or field use

- Measured rail noise, sustained power/thermal budget, and enclosure airflow at
  the three owner-provided interfaces. Upstream battery and wiring information is
  outside this recommendation scope.
- Storage temperature, overnight exposure, and solar-panel/structural mounting
  details. Orderly shutdown at 35 C is approved.
- Checkout-confirmed arrival to the owner-supplied British Columbia destination and the
  exact camera 12 V converter, sensor 5 V converter, switch, downstream
  protection, weather, mount, and cable BOM.
- Exact cooldown behavior and treatment of groups, pets, and partial occlusion;
  parked-only greeting and the <=10-ft interaction radius are decided.
- Checkout-confirmed camera/radar/microphone/speaker/amplifier/transducer stock,
  delivery, converter compatibility and final mounting.
- The preferred 5–7 versus 8–10 French/English mix, owner controls,
  generated-history retention, and final cat-story manifest.
- Mic electrical kill, camera shutters, visible privacy indicators, raw-data log
  policy, administration/update/recovery policy, exact keyed/local and remote
  adult-control implementation, and cloud API budget/provider.
