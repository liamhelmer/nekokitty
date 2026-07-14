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
- With documented replacement power and the low-power camera switch included,
  the safety-revised **provisional** planning range is **CAD
  1,625.13–1,947.53 landed**, leaving only **CAD 52.47–374.87** under the fixed
  ceiling. This is not an evidence-backed upper bound until unselected protection,
  grounding, inrush, metering, regulation, and fabrication lines are quoted. The
  simultaneous pack-side design allocation is **135 W**, still subject to a
  measured 200 W Neko-only acceptance cap.
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

- The traction bank is LiFePO4, described as 48 V and made from four 270 Ah
  batteries connected **in series**. Exact battery labels, nominal/charge limits,
  BMS rules, interconnects and protection remain unverified. The project does not
  need an overall cart energy/runtime calculation; it still needs those facts for
  safe converter, fuse and shutdown design.
- Two generic adjustable DC/DC modules currently produce 24 V for lights and
  19 V for the Jetson. The owner identifies each only by a marketplace title
  advertising **4–38 V input, 1.25–36 V output and 5 A**. A nominal 48 V bank is
  already outside that input range, so neither module is approved on the full
  series string. Do not reconnect or operate either one across the complete
  pack. If either input uses a two-battery midpoint, shut that accessory path
  down too: midpoint loading is not an acceptable workaround because it
  unbalances the series bank. Their exact present input wiring remains an urgent
  inspection item.
- The current loads reported by the owner are approximately 1–2 A on the 24 V
  lighting output and approximately 1 A on the 19 V Jetson output. These are
  observations, not converter qualifications; the advertised 5 A is not accepted
  as continuous capability without a real data sheet and thermal test.
- The 200 W requirement is a **running-load** cap. The three conditional
  full-pack converters publish typical startup inrush values of 30 A, 20 A, and
  20 A; simultaneous input application could briefly approach 70 A. That
  separate electrical transient requires measured sequencing/precharge or
  inrush limiting plus BMS, contactor, wiring, and fuse time-current
  coordination. It is not evidence of a 70 A continuous load and is not governed
  by a slow software watt limit.
- Preserve 24 V as the preferred accessory distribution voltage, but create it
  with a properly protected, full-pack-rated converter whose complete input
  range exceeds the measured battery/charger range. Give the Jetson its own
  independently protected full-pack-rated supply. Camera 12 V may be a dedicated
  downstream branch because the selected cameras explicitly require 12 V or
  standards-compliant active PoE. The recorded converter candidates may not be
  finally approved, ordered, or energized until battery labels, maximum charge/
  transient voltage, grounding, and protection are known.
- The provisional lowest-power camera topology is a dedicated isolated
  full-pack-to-12 V converter feeding two individually fused camera power runs
  and a low-power non-PoE switch. The Jetson onboard Ethernet port connects to
  that switch and Wi-Fi remains the optional online uplink. A crossover cable,
  USB Ethernet adapter and PoE boost stage are unnecessary in the primary path.
- Final electrical approval still needs a manufacturer-compliant DDR-240/RSD FG
  and mobile PE/chassis-bonding disposition, protected 24-to-5 V sensor
  regulation, an isolated runtime power-measurement path, and either a regulated
  lower-voltage audio branch with coordinated OVP or a wider-margin amplifier.
  A nominal 24 V rail is too close to the selected Soberton's 25 V maximum to be
  treated as a complete protection design.
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
  35 C rating.
- The full electrical and weather integration decision, evidence requirements,
  and manufacturer-source ledger are in
  [`docs/research/2026-07-13-power-weather.md`](../research/2026-07-13-power-weather.md).
- Speakers and the body transducer together must be rated at **100 W or less**.
  The current one-speaker/one-puck recommendation totals 30 W RMS and is limited
  to about 27 W combined program output.
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

- Exact battery models/BMS, full/rest/loaded voltage, configured limits and
  controlled shutdown threshold; whether each incompatible generic converter is
  presently connected across the full bank, a midpoint, or another rail;
  protection/grounding, measured rail noise, sustained power/thermal budget, and
  enclosure airflow.
- Storage temperature, overnight exposure, solar-panel/controller/mounting
  details, and whether safe shutdown/degraded operation from 35–40 C is acceptable.
- Checkout-confirmed arrival to British Columbia postal code **V9G 1L8** and the
  exact full-pack converter, downstream 12 V, switch, protection and cable BOM.
- Exact cooldown behavior and treatment of groups, pets, and partial occlusion;
  parked-only greeting and the <=10-ft interaction radius are decided.
- Checkout-confirmed camera/radar/microphone/speaker/amplifier/transducer stock,
  delivery, converter compatibility and final mounting.
- The preferred 5–7 versus 8–10 French/English mix, owner controls,
  generated-history retention, and final cat-story manifest.
- Mic electrical kill, camera shutters, visible privacy indicators, raw-data log
  policy, administration/update/recovery policy, exact keyed/local and remote
  adult-control implementation, and cloud API budget/provider.
