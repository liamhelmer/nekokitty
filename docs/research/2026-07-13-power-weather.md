# Power, weather, and physical integration update — 2026-07-13

This note records the owner's latest physical constraints and converts them into
purchase and field-test gates. It is a design record, not a certification of the
cart's existing wiring. No electrical hardware was opened, measured, or changed
while preparing it.

## Owner-supplied facts

- The traction bank is LiFePO4 and described as 48 V, using four batteries rated
  270 Ah each.
- Two DC/DC branches already come from that array: one regulated to 24 V for
  lights and accessories and one regulated to 19 V for the Jetson.
- New accessories should use 24 V where practical. A 12 V rail is acceptable
  only when a chosen device actually requires it.
- The roof is approximately 4 ft wide by 8 ft long and is covered by solar
  panels.
- Rain, dirt/dust, temperature exposure, and direct sun are all in scope.
- The primary child audience is ages 5–10.

“Four batteries, 48 V” is not enough to calculate energy or approve protection.
It could mean four nominal-12.8 V units in series, multiple complete 48 V packs,
or another manufacturer-approved arrangement. Amp-hours add in parallel but not
in series. Record the exact label/model and wiring diagram before publishing a
pack-energy or runtime estimate.

## Immediate electrical decision

Keep the existing **19 V Jetson branch** and make **24 V the accessory
distribution standard**. Do not add a general 12 V rail now.

The intended topology is:

```text
complete traction bank, BMS and main disconnect
  -> protected full-pack distribution
       -> DC-rated branch protection -> verified 48-to-19 V converter
            -> local protection/disconnect -> Jetson barrel input
       -> DC-rated branch protection -> verified 48-to-24 V converter
            -> fused 24 V accessory sub-distribution
                 -> lighting branch
                 -> audio branch
                 -> sensor/industrial-USB branch
                 -> future low-power accessory branches
```

Both converter inputs must be connected across the **complete pack output**,
after the pack's approved BMS/disconnect arrangement. A 24 V load must never be
taken from the midpoint of a series battery string. Victron's current
[battery-bank wiring guidance](https://www.victronenergy.com/media/pg/The_Wiring_Unlimited_book/en/battery-bank-wiring.html)
warns that a midpoint load creates a large imbalance and says to use a DC/DC
converter instead. Its
[LiFePO4 installation guidance](https://www.victronenergy.com/media/pg/Lithium_Battery_Smart/en/installation.html)
is even stricter for its own series/parallel batteries: do not connect anything
at the midpoints. The
actual battery manufacturer's series/parallel and BMS rules take precedence.

### Boot and hard-switch behavior

Applying the verified 19 V supply automatically powers on the developer kit by
default, according to NVIDIA's current
[power-on guidance](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/howto.html).
That matches Neko's boot requirement; systemd owns model/application startup.

Normal “off/offline” operation should not abruptly remove NVMe power. Make the
user control request an orderly Linux shutdown, hold the converters on until the
measured shutdown-complete signal/state, and then let a small hardware supervisor
drop their remote-enable or supply. Monitor the pack/19 V branch early enough to
do the same before converter or BMS undervoltage cutoff. NVIDIA likewise directs
users to complete Ubuntu shutdown before disconnecting power. The required
hold-up time and supervisor circuit must be measured with this build; do not
invent a fixed delay and assume it is safe.

Provide a clearly distinguished, verified DC-rated service/emergency disconnect
that can remove power immediately when electrical safety requires it. If the
owner's current hard switch is an immediate main-battery cutoff with no auxiliary
contact/hold-up path, it is only a candidate for that role until a qualified
installer verifies its DC voltage/current/interrupt rating, topology, location,
and manufacturer-intended duty. Add a separate normal shutdown input. No
software interlock may prevent the verified immediate electrical disconnect.

### Why retain 19 V for the Jetson

NVIDIA's current [Orin Nano developer-kit guide](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/quick_start.html)
specifies the included 19 V supply. The official
[carrier-board specification](https://developer.nvidia.com/downloads/assets/embedded/secure/jetson/orin_nano/docs/jetson_orin_nano_devkit_carrier_board_specification_sp.pdf)
allows 9–20 V at the DC jack, specifies a 5.5 mm barrel accepting a 2.5 mm
center-positive pin, and limits the jack to 3.5 A. Preserve that interface and
respect the connector limit even though a separate internal allocation table is
higher. Do not place the amplifier, lighting, or other noisy/peaky loads on the
Jetson converter output. Verify the existing converter, cable, connector, and
fuse even though the current software profile uses a 15 W module power mode.
The same specification gives the developer kit only a 0–35 C operating range,
making the shaded enclosure and hot-sun shutdown tests hard gates.

### How to use the 24 V branch

| Load | Proposed supply | Gate |
| --- | --- | --- |
| Dayton KAB-215v2 amplifier | Existing 24 V branch | The board's documented range ends at 24 V. Measure regulator tolerance, startup/turn-off behavior, ripple, and load-dump behavior at the amplifier terminals. If it can exceed the amplifier limit, use a dedicated lower regulated output instead. |
| StarTech ST7300USBME industrial hub | Existing 24 V branch | Its manufacturer specifies a 7–48 V DC input, 0–70 C operation, and non-condensing humidity. It still belongs inside the protected electronics bay; the hub itself has no stated outdoor ingress rating. |
| OAK/lidar/USB peripherals | Hub-regulated 5 V, not raw 24 V | Retain the S2L's documented 5 V startup headroom and USB current budget. |
| XVF3800 microphone array | USB 5 V | Bare/acoustically exposed hardware needs its own rain, wind, drainage, and condensation design. |
| 12 V-only future device | Dedicated small 24-to-12 V branch | Add only for a selected load, with its own protection and quiescent-current measurement. |

The 24 V lighting bus may be electrically noisy. Bench the audio and sensor
branches with lights switching, dimming, and traction power active. Use separate
branch protection, short returns, measured filtering, and—only if the test data
requires it—a dedicated isolated regulator. Do not describe a rail as “clean”
or “isolated” until its converter data sheet and oscilloscope tests establish it.

An optional replacement/isolated converter cannot be selected from “48 V
nominal” alone. As one documented example, the current Mean Well
[DDR-60L family](https://www.meanwell.com/Upload/PDF/DDR-60/DDR-60-spec.pdf)
accepts 18–75 V DC and provides 4 kV DC input/output withstand, while the G
family accepts only 9–36 V. That illustrates why the exact suffix and the pack's
maximum charged voltage matter; it is not a recommendation to order that part.

### Preliminary 24 V sizing and shortlist

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
| Reuse existing 24 V converter | Lowest cost and complexity | Must prove full-pack input, adequate maximum input voltage, isolation/grounding, at least the measured hot-load capacity, protection, and acceptable sag/ripple/EMI with lights and traction active. |
| Victron [Orion-Tr 48/24-12 isolated](https://www.victronenergy.com/upload/documents/Datasheet-Orion-Tr-DC-DC-converters-isolated-100-250-400W-EN.pdf) | 32–70 V input, nominal 24.2 V/12 A/280 W at 40 C, remote on/off, isolated | IP43 only in the specified terminals-down orientation, derates above 40 C, and 24.2 V is above the KAB amplifier's nominal 24 V upper endpoint; use local regulation or a different audio supply unless Dayton approves/tests it. |
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
5. whether either converter input or accessory return touches a battery
   midpoint, chassis, solar-controller return, or another grounded path;
6. 24 V and 19 V waveforms during key-on, key-off, charging, lights/dimmer
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

This audit should be performed by someone qualified for high-current mobile DC
systems. The assistant project must not modify the traction bank, BMS, solar
controller, or chassis bonding based only on a software-side drawing.

## Weather and solar-roof integration

Treat the cart as an outdoor mobile installation, not a sheltered hobby bench.
Use three physical zones:

| Zone | Examples | Minimum design treatment |
| --- | --- | --- |
| Exposed optical/range surfaces | OAK camera, lidar window | Buy the exact ingress-rated configuration; use its specified mating cable/connector, downward cable exit or drip loop, replaceable sacrificial guard that does not enter the FOV, and accessible cleaning path. |
| Acoustically exposed | microphone ports, speaker front | Rain lip, hydrophobic/acoustic vent solution validated for response, drainage below electronics, UV-stable windscreen, gasketed front-rated speaker baffle, and no upward-facing water pocket. |
| Protected electronics bay | Jetson, amp, hub, converters, fuse distribution | UV-stable enclosure with an appropriate certified outdoor rating—start from IP66 and add a NEMA 4X/corrosion requirement where the exact exposure warrants it—plus protected cable glands/connectors, touch guards, condensation management, drainage outside the electrical volume, and a heat path proven in sun. |

An enclosure's IP label does not certify the assembled system. Every gland,
connector, fastener, optical window, speaker opening, service cover, and cable
entry must preserve the intended ingress level. “Waterproof” also does not mean
pressure-washer safe, permanently submerged, or condensation-free. Until the
washing method and temperature range are known, design for rain and road spray
but explicitly prohibit pressure washing the electronics/sensor apertures.

Current Luxonis documentation creates a procurement hold, not a blanket rating.
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

The current value perception concept remains one front OAK-D W, a rear camera,
and a useful-height 360-degree range layer. The lidar still needs a clear,
approximately 0.9–1.2 m level scan plane; the solar roof is not a reason to put
it overhead where it scans above children. If bodywork, riders, or roof posts
make that plane impractical, use distributed sealed radar/presence sectors and
camera confirmation instead.

## Thermal and environmental acceptance

The Jetson, converter, and hub should not sit in a sealed sun-heated box with no
measured heat path. Start with passive conduction to a shaded external heat
spreader or a sealed air-to-air approach; add a replaceable filtered/pressurized
air path only if testing shows passive cooling cannot hold margins. Exposed fins
must be cleanable and must not become touch or snag hazards.

Log enclosure ambient, Jetson thermal zones, converter case temperature, OAK
telemetry, 24/19 V rails, and total branch current during:

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
   diagram showing series/parallel links, BMS, shunt, main fuse/disconnect,
   charger, solar controller, and both converter inputs;
2. make/model, settings, wiring, and fuse information for both DC/DC converters;
3. measured full/rest/loaded pack voltage and both output rails, manufacturer/
   configured BMS limits, and Neko's controlled low-voltage shutdown threshold;
4. lowest/highest ambient, storage temperature, coastal/salt exposure, rain
   while parked, and whether cleaning means a damp cloth, garden hose, or
   pressure washer;
5. roof height and structural-member/post/body/seat geometry, not just roof
   footprint;
6. where a shaded, serviceable electronics bay can fit and its available outer
   dimensions;
7. solar-panel/controller make/model and approved structural attachment points.

These are evidence requests, not reasons to pause software and story work.
