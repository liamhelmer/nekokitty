# Power, weather, and physical integration update — 2026-07-13

> **One-week scope update — 2026-07-13:** the active hardware and power budget is
> in
> [`2026-07-13-canadian-one-week-bom.md`](2026-07-13-canadian-one-week-bom.md).
> Earlier OAK/S2L/XVF3800 component allocations and open-ended accessory sizing in
> this note remain research references, but they do not override the current
> two-Reolink/four-radar/XVF3000 build or its scoped 200 W ceiling.

> **Immediate safety correction — 2026-07-13:** the owner has now identified both
> installed adjustable modules only by an advertised **4–38 V input, 1.25–36 V
> output, 5 A** specification. They are incompatible with a nominal 48 V series
> bank and are not approved full-pack converters. Do not operate either module
> across the complete string. A two-battery/midpoint input is also prohibited
> because it unbalances the string. Trace and isolate both inputs before further
> operation; the replacement architecture below supersedes every earlier “reuse
> the existing converter” statement in this note.

This note records the owner's latest physical constraints and converts them into
purchase and field-test gates. It is a design record, not a certification of the
cart's existing wiring. No electrical hardware was opened, measured, or changed
while preparing it.

## Owner-supplied facts

- The traction bank is LiFePO4 and described as 48 V, using four 270 Ah batteries
  **in series**. The owner has resolved the topology; the individual labels,
  series/BMS permission, physical wiring, configured limits, and protection have
  not yet been inspected.
- Two generic adjustable buck modules currently produce 24 V for lights and
  accessories and 19 V for the Jetson. Each is advertised as 4–38 V input,
  1.25–36 V output and 5 A. Their input wiring has not been traced, and no
  manufacturer data sheet, isolation rating, continuous thermal rating,
  protection certification or ingress rating is available.
- The owner reports approximately 1–2 A on the 24 V lighting output and
  approximately 1 A on the 19 V Jetson output. Those observations do not make a
  38 V-maximum converter safe on a 48 V-class pack and do not validate the
  marketplace 5 A claim as a continuous rating.
- New accessories should use 24 V where practical. A 12 V rail is acceptable
  only when a chosen device actually requires it.
- The roof is approximately 4 ft wide by 8 ft long and is covered by solar
  panels.
- Intended ambient operation is 0–40 C. There is no salt exposure. Moisture,
  rain, dirt/dust, vibration and direct sun are in scope, while key components
  will be protected from direct rain. Cleaning is by cloth, not hose or pressure
  washer.
- The primary child audience is ages 5–10.

The series topology is now an owner decision, not an open series/parallel
question. It still does not approve protection or establish actual nominal/full/
loaded voltage: record all four labels, manufacturer series/BMS rules, and the
physical wiring before connecting new loads. **No overall traction-pack energy,
cart-runtime, or endurance calculation is required or authorized for this
revision.**

## Current scoped power decision

The Jetson, NVMe/cooling, two Reolink Duo 3V cameras, four C4001 radars and wired
aggregator, microphone, local network/data electronics, limited amplifier,
15 W RMS voice driver, and 15 W RMS body transducer must draw **no more than
200 W while running**. The revised Canadian one-week plan allocates approximately
135 W simultaneously at the pack side, including 35 W for the limited audio
domain, three full-pack conversion paths, downstream sensor/audio regulation,
and conversion/thermal/measurement contingency. Those are design allocations,
not measurements.

Measure all three proposed full-pack converter inputs during the maximum approved
simultaneous story/purr, wake/ASR, Gemma, camera, radar, network, and sampled
ZipDepth workload. Keep lights and all non-Neko accessories positively off for
the scoped test; then repeat with lights operating as a separate
rail-sag/ripple/thermal/EMI coexistence test. Do not use a guessed baseline
subtraction. The Neko build fails if any post-start running mode or ordinary
workload transient exceeds 200 W at the pack side. A provisional 180 W software
load-shedding threshold creates warning margin, but it first needs a selected
isolated voltage/current measurement path. Neither it nor the 200 W scope cap
sizes conductors, fuses, converters, or disconnects; each circuit still uses its
audited worst-case electrical requirements.

Converter startup inrush is a separate electrical acceptance test. The published
typical input pulses are 30 A for the DDR-240C-24 and 20 A for each 60 W
candidate, so uncontrolled simultaneous application could briefly approach
70 A. This is not a continuous-load estimate. Sequence/precharge or limit the
inputs, measure the pulse with a suitable current probe, and coordinate BMS,
switch/contactor making duty, wiring, and fuse time-current curves. A slow
software watt meter cannot own that protection.

## Immediate electrical decision

Retire the generic modules from primary cart service. Keep **24 V as the
accessory distribution standard**, but generate it with a documented
full-pack-rated isolated converter. Power the Jetson and exterior camera/network
domain from separate documented 12 V converters. Twelve volts is selected only
where the actual devices require or officially accept it; it is not a new
general-purpose passenger-accessible rail.

The intended topology is:

```text
complete traction bank, BMS and main disconnect
  -> protected full-pack distribution
       -> DC-rated branch protection -> Mean Well DDR-240C-24 candidate
            -> fused 24 V accessory sub-distribution
                 -> lighting branch
                 -> fused regulated/protected audio sub-branch
                 -> fused regulated 5 V radar/aggregator branch
                 -> future low-power accessory branches
       -> DC-rated branch protection -> Mean Well RSD-60L-12 candidate
            -> local output protection -> Jetson 5.5 x 2.5 mm barrel input
       -> DC-rated branch protection -> Mean Well DDR-60L-12 candidate
            -> fused 12 V front-camera branch
            -> fused 12 V rear-camera branch
            -> fused Brainboxes SW-005 branch
```

Every converter input must be connected across the **complete pack output**,
after the pack's approved BMS/disconnect arrangement. A 12, 19 or 24 V load must
never be taken from the midpoint of a series battery string. Victron's current
[battery-bank wiring guidance](https://www.victronenergy.com/media/pg/The_Wiring_Unlimited_book/en/battery-bank-wiring.html)
warns that a midpoint load creates a large imbalance and says to use a DC/DC
converter instead. Its
[LiFePO4 installation guidance](https://www.victronenergy.com/media/pg/Lithium_Battery_Smart/en/installation.html)
is even stricter for its own series/parallel batteries: do not connect anything
at the midpoints. The
actual battery manufacturer's series/parallel and BMS rules take precedence.

This is still a conditional candidate design, not authorization to energize it.
The DDR-240C-24 accepts 33.6–67.2 V DC, the RSD-60L-12 accepts 18–72 V DC, and
the DDR-60L-12 accepts 18–75 V DC. Record the actual battery/charger maximum and
switching transients and preserve engineering margin below every selected upper
limit. A conventional four-by-12.8 V LiFePO4 example would be about 51.2 V
nominal and 58.4 V if each battery permits 14.6 V charging, but Neko's battery
labels—not that example—control the design.

### Boot and hard-switch behavior

Applying the verified 12 V supply automatically powers on the developer kit by
default, according to NVIDIA's current
[power-on guidance](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/howto.html).
That matches Neko's boot requirement; systemd owns model/application startup.

Normal “off/offline” operation should not abruptly remove NVMe power. Make the
user control request an orderly Linux shutdown, hold the converters on until the
measured shutdown-complete signal/state, and then let a small hardware supervisor
drop their remote-enable or supply. Monitor the pack/12 V Jetson branch early
enough to do the same before converter or BMS undervoltage cutoff. NVIDIA likewise
directs users to complete Ubuntu shutdown before disconnecting power. The required
hold-up time and supervisor circuit must be measured with this build; do not
invent a fixed delay and assume it is safe.

Provide a clearly distinguished, verified DC-rated service/emergency disconnect
that can remove power immediately when electrical safety requires it. If the
owner's current hard switch is an immediate main-battery cutoff with no auxiliary
contact/hold-up path, it is only a candidate for that role until a qualified
installer verifies its DC voltage/current/interrupt rating, topology, location,
and manufacturer-intended duty. Add a separate normal shutdown input. No
software interlock may prevent the verified immediate electrical disconnect.

### Why use a dedicated 12 V Jetson converter

NVIDIA's current [Orin Nano developer-kit guide](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/quick_start.html)
specifies the included 19 V supply. The official
[carrier-board specification](https://developer.nvidia.com/downloads/assets/embedded/secure/jetson/orin_nano/docs/jetson_orin_nano_devkit_carrier_board_specification_sp.pdf)
allows 9–20 V at the DC jack, specifies a 5.5 mm barrel accepting a 2.5 mm
center-positive pin, and limits the jack to 3.5 A. A documented 12 V supply is
therefore valid and avoids pretending the unsafe adjustable module must remain
at 19 V. Preserve that interface and connector limit. Do not place the amplifier,
lighting, cameras or other noisy/externally faultable loads on the Jetson output.

The candidate [Mean Well RSD-60L-12](https://www.meanwell.com/Upload/PDF/RSD-60/RSD-60-SPEC.PDF)
provides 12 V/5 A/60 W from 18–72 V input at 93% typical efficiency, with 4 kV
input/output isolation, railway vibration qualification, and full output through
55 C before derating. It has no assembled outdoor IP rating and no remote-enable
input, so keep it in the dry ventilated bay and use an externally supervised,
DC-rated delayed cutoff after Linux halts. The current 15 W Jetson mode leaves
margin below the 42 W barrel-interface limit at 12 V, but validate the complete
NVMe/USB load and use a strain-relieved center-positive lead.

The same NVIDIA specification gives the developer kit only a **0–35 C operating
range**. The owner wants 0–40 C ambient operation, but airflow cannot cool below
ambient. Instrument the protected bay and Jetson thermal zones; above the tested
35 C enclosure-ambient boundary, stop optional workers and perform an orderly
shutdown unless the developer kit is replaced by a validated industrial thermal
platform. Hot-sun shutdown/restart tests are hard gates.

### How to use the 24 V and camera branches

For the active one-week build, the 24 V domain supports the existing lights,
regulated 5 V for four C4001 modules and their wired aggregator, and the
separately limited audio branch. The candidate
[Mean Well DDR-240C-24](https://www.meanwell.com/Upload/PDF/DDR-240/DDR-240-SPEC.pdf)
provides 24 V/10 A/240 W with 91% typical efficiency, 4 kV DC isolation,
remote on/off and DC-OK, and a three-second 15 A peak. Its input is 33.6–67.2 V,
so battery-label/transient verification is mandatory. It is not IP-rated, and no
conformal-coating claim was found in the cited manufacturer documents. Its
installation manual requires vertical input-down mounting, specified clearances,
a dry Pollution Degree 2 environment, and FG connected to PE. The mobile PE/
chassis solution is unresolved and must be accepted by a qualified installer or
the candidate rejected.

Do **not** connect the 25 V-maximum Soberton directly based only on a nominal
24 V setpoint. The DDR-240 adjusts from 24–28 V with ±1% tolerance and its own
overvoltage trip begins at 28.8 V, too high to protect the amplifier. Use a
selected, separately fused lower-voltage regulator with adequate margin and
coordinated hardware OVP, or replace the amplifier. Measure startup/turn-off
overshoot and the maximum loaded rail before connection. The protected 24-to-5 V
radar/aggregator converter is also still to be selected and costed inside the
installation allowance.

The cameras instead use a dedicated
[Mean Well DDR-60L-12](https://www.meanwell.com/Upload/PDF/DDR-60/DDR-60-spec.pdf)
and a [Brainboxes SW-005](https://www.brainboxes.com/products/industrial-ethernet-switches/page/fast-ethernet).
The converter accepts 18–75 V and provides isolated 12 V/5 A/60 W at 91%
typical efficiency. The switch accepts 5–30 V, draws at most 1.1 W, operates
from -10 to 60 C, and needs no extra 5 V converter. Each Reolink gets an
individual fused 18 AWG tinned-copper 12 V run; do not use a barrel Y-splitter.
Give the switch its own protected branch. Set and tamper-mark the adjustable
converter at 12.0 V, then verify startup, loaded voltage and polarity at each
received camera before connection. The converter, switch, output fuse
distribution and DC joints stay in the protected bay because none is an
exposed-weather assembly.

The Jetson onboard Ethernet port connects to the switch, which connects to both
cameras. A crossover cable is unnecessary. Wi-Fi remains the optional Internet
uplink. This uses less published power and fewer conversion stages than active
PoE. If later cabling experience justifies PoE, use only active IEEE 802.3af/at;
never feed passive 24 V into these cameras.

The following table records compatibility work for the earlier component set;
where it names OAK/S2L/XVF3800/KAB hardware, it is not the current purchase list:

| Load | Proposed supply | Gate |
| --- | --- | --- |
| Dayton KAB-215v2 amplifier | Historical verified 24 V branch | The board's documented range ends at 24 V. This is not the selected amplifier; retain only the tolerance/startup/ripple lesson. |
| StarTech ST7300USBME industrial hub | Historical verified 24 V branch | Its manufacturer specifies a 7–48 V DC input, 0–70 C operation, and non-condensing humidity. It is not the active one-week network switch. |
| OAK/lidar/USB peripherals | Hub-regulated 5 V, not raw 24 V | Retain the S2L's documented 5 V startup headroom and USB current budget. |
| XVF3800 microphone array | USB 5 V | Bare/acoustically exposed hardware needs its own rain, wind, drainage, and condensation design. |
| 12 V-only future device | Dedicated small 24-to-12 V branch | Add only for a selected load, with its own protection and quiescent-current measurement. |

The 24 V lighting bus may be electrically noisy. Bench the audio and sensor
branches with lights switching, dimming, and traction power active. Use separate
branch protection, short returns, measured filtering, and—only if the test data
requires it—a dedicated isolated regulator. Do not describe a rail as “clean”
or “isolated” until its converter data sheet and oscilloscope tests establish it.

No replacement/isolated converter can be finally approved or ordered from “48 V
nominal” alone. As one documented example, the current Mean Well
[DDR-60L family](https://www.meanwell.com/Upload/PDF/DDR-60/DDR-60-spec.pdf)
accepts 18–75 V DC and provides 4 kV DC input/output withstand, while the G
family accepts only 9–36 V. That illustrates why the exact suffix and the pack's
maximum charged voltage matter. The selected `DDR-60L-12` camera candidate still
requires the pack audit despite its wider input range.

### Superseded preliminary 24 V sizing and shortlist

This earlier generic accessory envelope predates the revised one-week 135 W scoped
allocation and 200 W measured ceiling. Retain it for converter comparison only;
do not add it to the current allocation or use it for cart-runtime estimates.

The following is a conservative **design envelope**, not measured consumption:

| Group | Planning envelope |
| --- | ---: |
| Audio amp/speaker/shaker nameplate path | up to about 48 W input allowance; ordinary use should be much lower |
| Sensor/data domain | up to 35 W for either the powered-hub/attached-device path or the active-PoE plus local-5 V path; do not add both alternatives twice |
| Enclosure sensing/thermal control | about 5–15 W |
| Measured growth/startup reserve | about 15–25 W |

Expect roughly 60–90 W during representative accessory use after tuning, but
bench against approximately 110–130 W of simultaneous nameplate demand. Lights
are additional and still unknown. If a new clean electronics rail is necessary,
a hot-derated 200–300 W class converter provides useful startup and future
margin; this is not permission to make the amplifier or transducer louder.

Research candidates to evaluate only after the battery audit:

| Candidate | Relevant manufacturer facts | Blocking concern |
| --- | --- | --- |
| Existing generic 4–38 V modules | None acceptable | **Rejected** across the full pack and at a series midpoint. Do not mistake an observed output voltage/current for input compatibility or a continuous rating. |
| Historical shortlist candidate: Mean Well [DDR-240C-24](https://www.meanwell.com/Upload/PDF/DDR-240/DDR-240-SPEC.pdf) | 33.6–67.2 V input, 24 V/10 A/240 W, 91% typical efficiency, 4 kV isolation, remote on/off/DC-OK, railway vibration qualifications | Current controlling blockers also include FG-to-PE/Pollution Degree 2, combined startup inrush, downstream 5 V, and audio regulation/OVP; use the active BOM, not this row alone. |
| Weather-tolerant fallback: Victron [Orion-Tr 48/24-12 isolated](https://www.victronenergy.com/upload/documents/Datasheet-Orion-Tr-DC-DC-converters-isolated-100-250-400W-EN.pdf) | 32–70 V input, nominal 24.2 V/12 A/280 W at 40 C, 89% typical efficiency, remote on/off, isolated | IP43 only terminals-down, derates 3%/C above 40 C, and Canadian arrival is less certain. Its nominal output is also too close to the 25 V-maximum Soberton to waive downstream margin/OVP. |
| Mean Well [RSD-300C-24](https://www.meanwell.com/Upload/PDF/RSD-300/RSD-300-SPEC.PDF) | 33.6–62.4 V continuous input, 24 V/12.5 A/300 W, 4 kV input/output withstand, semi-potted | The 62.4 V continuous ceiling must exceed the real charger/transient maximum with margin; it has no assembled outdoor IP rating and needs a thermal/enclosure design. |

For a PoE OAK, use an **active standards-compliant 802.3af** converter/injector
from 24 V. Luxonis's current
[battery-power guidance](https://docs.luxonis.com/hardware/platform/deploy/powering-poe/)
lists tested 12/24 V options and warns that passive PoE can damage equipment.
For an exterior run, follow the same guidance's requirement for shielded outdoor
Ethernet, preserve the correctly mated M12/gland seal, and keep the injector and
any RJ45 transition inside the protected bay.
For 24 V USB distribution, the proposed StarTech hub accepts the rail directly;
for the S2L, use local regulated 5 V rated at least 3 A and validate voltage and
ripple at the device during cold start.

## Protection and wiring acceptance gate

LiFePO4 batteries can supply very high fault current. The current Victron
[DC-wiring reference](https://www.victronenergy.com/media/pg/The_Wiring_Unlimited_book/en/dc-wiring.html)
requires fuse voltage, current, speed, and interrupt ratings to match the system
and calls for at least one fuse whose interrupt rating meets the battery bank's
prospective short-circuit current. It also notes that common blade, MIDI, ANL,
and many MEGA fuses are only 32 V DC; a familiar automotive fuse is therefore
not automatically safe on the full-pack side of a nominal-48 V LiFePO4 bank.

Before connecting Neko hardware, record and photograph:

1. each battery label, data sheet, BMS, series/parallel permission, terminal
   torque, and the actual interconnect diagram;
2. pack voltage after full charge, at rest, and under representative traction
   load; manufacturer/configured BMS limits; and the higher controlled shutdown
   threshold for Neko. Observe an actual BMS cutoff only in a qualified battery
   test, never by casually deep-discharging the traction bank;
3. the make/model and full data sheet for each converter, including allowed
   input range, output tolerance, continuous/peak power, isolation, efficiency,
   derating, ingress rating, remote-enable behavior, and protection modes;
4. main and branch fuse type, DC voltage rating, interrupt rating, current
   rating, location, conductor gauge/temperature rating, and disconnect rating;
5. whether either current or proposed converter input, FG, output, or accessory
   return touches a battery midpoint, chassis, solar-controller return, or
   another grounded path;
6. 24 V, both 12 V, regulated sensor/audio, and inrush waveforms during key-on,
   key-off, charging, lights/dimmer
   switching, motor operation, regenerative events if any, and maximum allowed
   accessory load.

Protect every ungrounded conductor as required by the audited topology, with
devices correctly located and sized to the conductor and equipment. Switching
and disconnect hardware must be explicitly
DC-rated for the **maximum**, not nominal, pack voltage and fault/operating
current. Final conductor sizing depends on round-trip length, bundling,
temperature, connector rating, and acceptable voltage drop. In wet zones use
fine-strand tinned-copper cable and sealed, strain-relieved connectors; do not
leave screw terminals or fuse contacts exposed to passengers or spray.

A covered marine-style 32 V fuse block can be appropriate **after** the regulated
24 V converter, but its rating makes it unsuitable on the pack side. Do not
select a full-pack fuse by current alone: even a 58 V-rated part may be invalid
if the real charge voltage or transient can exceed 58 V. The final pack-side
fuse/holder must have adequate DC voltage and interrupt ratings for the bank's
prospective short-circuit current and should be selected by the qualified
installer after the battery data are known. Do not credit an electronic BMS as
current-limiting unless its manufacturer supplies an applicable SCCR or
current-limiting/coordination specification.

First determine whether traction negative is floating or chassis-bonded and how
the solar controller, converters, USB shields, and Ethernet shields reference it.
Do not add a pack-to-chassis or 24 V-to-chassis bond by intuition. Prefer isolated
conversion and have the qualified installer define accessible-metal bonding,
fault-clearing conductors/devices, and one documented reference/grounding scheme
that does not create return current through data-cable shields. Victron's current
[grounding guidance](https://www.victronenergy.com/media/pg/The_Wiring_Unlimited_book/en/ground%2C-earth-and-electrical-safety.html)
explains why converter isolation and interface references must be considered as
one system.

The DDR-240 manual explicitly requires FG connected to PE, and the metal-case
RSD-60 exposes an FG terminal. Do not silently rename the cart chassis “PE.” The
installer must reconcile those manufacturer interfaces with a mobile, possibly
floating battery system and document the protective/equipotential bond and fault
clearing path. If that cannot be done to the applicable instructions, select a
different converter architecture.

This audit should be performed by someone qualified for high-current mobile DC
systems. The assistant project must not modify the traction bank, BMS, solar
controller, or chassis bonding based only on a software-side drawing.

## Weather and solar-roof integration

Treat the cart as an outdoor mobile installation, not a sheltered hobby bench.
Use three physical zones:

| Zone | Examples | Minimum design treatment |
| --- | --- | --- |
| Exposed optical/range surfaces | Reolink cameras, C4001 pods; later 3D-lidar window | Buy or build the exact ingress-rated configuration; use specified mating cable/connectors, downward cable exits or drip loops, replaceable guards that do not enter the FOV/beam, and accessible cleaning paths. |
| Acoustically exposed | microphone ports, speaker front | Rain lip, hydrophobic/acoustic vent solution validated for response, drainage below electronics, UV-stable windscreen, gasketed front-rated speaker baffle, and no upward-facing water pocket. |
| Protected electronics bay | Jetson, amp, camera switch, converters, fuse distribution | UV-stable enclosure with an appropriate certified outdoor rating—start from IP66 and add a NEMA 4X/corrosion requirement where the exact exposure warrants it—plus protected cable glands/connectors, touch guards, condensation management, drainage outside the electrical volume, and a heat path proven in sun. |

An enclosure's IP label does not certify the assembled system. Every gland,
connector, fastener, optical window, speaker opening, service cover, and cable
entry must preserve the intended ingress level. “Waterproof” also does not mean
pressure-washer safe, permanently submerged, or condensation-free. Design for
the stated rain/moisture and 0–40 C ambient range; clean only by cloth and
explicitly prohibit hosing or pressure washing electronics/sensor apertures.

The following Luxonis/S2L paragraphs are retained for later alternatives and do
not describe the active one-week Reolink/C4001 order. Current Luxonis
documentation creates a procurement hold, not a blanket rating.
The [OAK-D W listing](https://shop.luxonis.com/products/oak-d-w) calls the current
unit IP66, while Luxonis's
[environmental page](https://docs.luxonis.com/hardware/platform/environmental-specifications/ip-rating)
first says current USB devices lack an IP rating and later says the screw-lock
waterproof cable provides IP66 for listed Series 2 cameras. Its linked certificate
does not clearly settle every OAK-D W/OV9782 SKU. Obtain written confirmation and
a certificate for the exact camera SKU, sensor option, connector, and cable before
relying on IP66; otherwise choose the clearly specified PoE enclosure or provide
an independently validated installation.
The product-specific OAK-D W documentation specifies -20–50 C ambient at full
VPU utilization. That limit, not a generic component estimate, controls; local
sealed-enclosure and sun-load tests may require a still narrower range.

The RPLIDAR S2L is advertised as IP65, but its current manufacturer data sheet
limits operation to -10–50 C, requires 5 V within 4.9–5.2 V, allows 150 mV
ripple, and calls for 1.5 A at startup. Its optical window must remain
unobstructed. IP65 is not permission to bury it behind an unverified clear
cover, point a pressure washer at its rotating seal, or operate it outside that
temperature range.

### Roof consequences

The 4-by-8-ft roof footprint is enough for packaging work but does not solve
coverage geometry. Because its top face is solar:

- do not shade cells, drill panel frames/backsheets, bond to panel glass, or trap
  heat beneath a panel without the exact panel manufacturer's approval;
- prefer brackets from structural roof members/posts and place sensors under the
  perimeter/eaves, with the microphone near the acoustic center only if a dry
  aperture and cable route are possible;
- route sensor and audio cabling away from solar-controller and traction-current
  wiring, crossing power conductors at right angles where separation is limited;
- preserve panel service/removal, rain runoff, passenger head clearance, and a
  downward drip loop before every enclosure entry;
- record roof height, post locations, cat-body occlusion, seated passenger
  envelopes, and panel/controller cable routes on the dimensioned survey.

The active value perception concept is one Reolink Duo 3V below the front roof
edge, one below the rear edge, and four sealed C4001 radar pods around the roof
quadrants. The roughly 7-ft roof geometry rejects a 2D lidar for this revision:
level rays pass above children, while tilting produces one sloped plane rather
than a downward surround cone. A later inverted hemispherical 3D lidar is
geometrically valid, but remains gated by stock, ingress, optical-window, power,
and landed cost.

## Thermal and environmental acceptance

The Jetson, converters, and camera switch should not sit in a sealed sun-heated box with no
measured heat path. Start with passive conduction to a shaded external heat
spreader or a sealed air-to-air approach; add a replaceable filtered/pressurized
air path only if testing shows passive cooling cannot hold margins. Exposed fins
must be cleanable and must not become touch or snag hazards.

Log enclosure ambient, Jetson thermal zones, every converter case temperature,
camera/radar health, the 24 V and both 12 V rails, and total branch current during:

- cold start and hot restart;
- midday sun with the solar system charging;
- ordinary and maximum-approved audio while lights switch;
- perception + wake/ASR + Gemma + TTS combined soak;
- wet-after-dry and dry-after-wet transitions for condensation;
- dust exposure followed by the documented cleaning method;
- vibration, bumps, connector tug, ten normal orderly-shutdown/cold-boot cycles,
  and a separately controlled recovery test after unavoidable immediate power
  loss.

Fail closed: an overtemperature, undervoltage, converter fault, water sensor, or
missing peripheral disables proactive interaction/heavy workers before it risks
hardware. Voice should fall back to a smaller local mode when safe; no software
fallback overrides an electrical or thermal shutdown.

## Remaining information needed

The following items still block final converter, fuse, enclosure, and mount
orders:

1. clear photos and make/model of all four battery labels, plus a simple wiring
   diagram verifying the owner-confirmed series links, BMS, shunt, main fuse/disconnect,
   charger and solar controller;
2. an urgent trace showing whether each incompatible generic converter input is
   across the full string, a two-battery midpoint, or another regulated source,
   plus current fuse/switch/wire information;
3. measured full/rest/loaded pack voltage and current output rails, manufacturer/
   configured BMS limits, and Neko's controlled low-voltage shutdown threshold;
4. storage temperature, overnight condensation/rain exposure, and whether
   orderly degraded shutdown between 35 and 40 C is acceptable; 0–40 C ambient,
   no salt, cloth cleaning and protection from direct rain are decided;
5. complete front/rear/both-side empty and occupied survey images or a drawing
   with dimensions. The first occupied side/rear image establishes the slat/post
   occlusion risk but not every camera seam or bracket dimension;
6. where a shaded, serviceable electronics bay can fit and its available outer
   dimensions;
7. solar-panel/controller make/model and approved structural attachment points;
8. full-pack source cable lengths/gauges and the battery/BMS prospective fault
   current needed to select >=80 V DC branch protection and interrupt ratings;
9. manufacturer-compliant DDR/RSD FG/PE/chassis treatment, startup-inrush
   sequencing/limiting, isolated runtime metering, the 24-to-5 V sensor stage,
   and the lower-voltage audio regulator/OVP or replacement amplifier.

These are evidence requests, not reasons to pause software and story work.
