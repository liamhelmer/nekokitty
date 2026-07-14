# Canadian one-week hardware decision — 2026-07-13

This note supersedes the earlier US-dollar purchase recommendation in
[`2026-07-13-perception-bom.md`](2026-07-13-perception-bom.md) and the overseas
audio purchase path in
[`2026-07-13-audio-voice.md`](2026-07-13-audio-voice.md) wherever they conflict.
Those longer notes remain the component and acceptance-test research record.

No part was ordered, installed, wired, or configured while preparing this
update. Prices and stock were observed on 2026-07-13 and must be checked at the
actual checkout. The arithmetic below uses the British Columbia planning rate of
5% GST plus 7% PST. The owner supplied British Columbia destination **V9G 1L8**;
the exact checkout arrival date remains a purchase gate.

## Fixed owner constraints

- Added hardware must total no more than **CAD 2,000 landed**, including tax and
  shipping. Existing Jetson, NVMe/storage, and Logitech C922 are excluded.
- All cameras, lidar/radar, microphones, audio output, and the Jetson together
  must draw **less than or equal to 200 W while running**. Overall cart energy
  and runtime are explicitly out of scope.
- Speaker and body-transducer ratings must total **100 W or less**.
- All required parts must be obtainable within one week.
- Roof underside is about 7 ft (2.13 m) high, lightly sloped, and open at the
  sides. Children are about 3.5–4.5 ft (1.07–1.37 m) tall.
- Intended ambient operation is 0–40 C, with no salt exposure. Moisture,
  rain, dust/dirt, sun and vibration are normal; key electronics will be
  sheltered from direct rain and cleaned by cloth only.
- Perception is for social behavior on a manually driven cart, never vehicle
  control or a safety-rated protective function.

## Decision

For revision one, buy **camera semantics plus inexpensive radar presence** and
defer lidar:

1. two opposing Reolink Duo 3V PoE 180-degree outdoor cameras, one under the
   front roof edge and one under the rear roof edge;
2. four DFRobot C4001 24 GHz radar sectors at nominal yaws 0, 90, 180, and 270
   degrees for low-cost anonymous presence/range hints;
3. a locally stocked four-microphone/AEC board, two-channel amplifier, one
   weather-resistant voice speaker, and one protected body transducer;
4. documented isolated full-pack conversion for 24 V accessories, dedicated
   12 V Jetson power, and dedicated 12 V camera/network power; and
5. the Jetson onboard Ethernet port feeding one low-power industrial switch for
   both cameras, with Wi-Fi retained as the optional online uplink.

This is the lowest-risk path found that is weather-capable, nominally covers the
full azimuth, recognizes people, **can** fit the one-week procurement window if
every checkout gate below passes, and stays well below 200 W in the design
allocation. It can remain under the hardware cap on paper, but the conservative
high case leaves only CAD 52.47. It is not a claim of perfect 360-degree coverage:
panorama seams, roof posts, occupants, bodywork, dirty lenses, and very close
targets still need a measured blind-zone map.

An **inverted hemispherical 3D lidar is geometrically valid on the roof** and is
the preferred later lidar experiment. It is deferred only because current
Canadian stock, weather integration, and landed cost do not beat the camera/radar
build inside this one-week revision.

The two currently installed generic modules advertise only 4–38 V input. They
are rejected on the nominal-48 V series string and at any battery midpoint;
present input wiring must be traced and isolated before this purchase becomes an
installation. Output settings of 19 or 24 V and currently modest load do not fix
an input overvoltage or series-balance problem.

## Why a roof-mounted 2D lidar does not work

A conventional RPLIDAR S2 is a single-plane scanner. Level at 7 ft, every useful
ray stays at about 7 ft and passes 2.5–3.5 ft above the children's heads. Open
sides remove wall occlusion but do not change the scan height.

Tilting the scanner does not turn the plane into a downward cone. With sensor
height `h`, horizontal range `r`, tilt `a`, and azimuth `p` measured from the
downward tilt direction, the scan height is approximately:

```text
z = h - r * cos(p) * tan(a)
```

To lower a ray from 7 ft to roughly 4 ft at 6 ft range requires about a 26.6
degree tilt. That ray reaches the child-height band only in front; the side rays
remain at 7 ft and the rear ray rises to roughly 10 ft. Mounting the 2D scanner
vertically instead gives one vertical slice, not a full surround volume.

A 2D lidar can still be useful around 3–4 ft above ground if it has a clear
perimeter horizon. On this people-carrying cart it would be vulnerable to
occlusion by the cat body, roof posts, driver and passengers, and to child impact
or tampering. It also supplies anonymous range clusters, not person semantics.

## Why a roof-mounted 3D lidar can work

The Unitree L2 manual describes a 360 by 90-degree hemisphere on one side of the
sensor, permits installation in any direction, and includes an upside-down water
protection drawing. Inverting it under the roof turns its upward hemisphere into
a downward one. At 3–10 ft horizontal range, rays from a 7-ft sensor to the
3.5–4.5-ft child-height band are roughly 14–49 degrees below horizontal, inside
that hemisphere.

The same manual requires an external water-protection structure, warns that even
transparent glass over the optical window degrades performance, specifies 12 V
at 1 A, and gives 10 W nominal/roughly 13 W maximum when its heater is active.
Therefore inversion solves geometry, not ingress, optical-window, power-converter,
or delivery problems.

## Cost and capability comparison

| Option | Current price evidence | Approximate BC cost | Power | What it buys | One-week result |
| --- | ---: | ---: | ---: | --- | --- |
| Two [Reolink Duo 3V PoE](https://www.bestbuy.ca/en-ca/product/reolink-duo-3v-poe-2-pack-16mp-uhd-ik10-dual-lens-poe-camera-with-motion-track-180-panorama-color-night-vision/18929224) cameras | CAD 419.99, online, free shipping; marketplace seller normally dispatches within two business days | CAD 470.39 before power/mounts | Less than 24 W pair | Nominal 360-degree RGB, local person events, RTSP/ONVIF, IP67 | **Recommended**, only if checkout promises arrival inside seven days |
| One [OAK-D W](https://www.mouser.ca/ProductDetail/Luxonis/OAK-D-W?qs=Znm5pLBrcAJZNHOtEkFjzA%3D%3D) base camera | CAD 753.36; 32 shown able to ship immediately at the final refresh | CAD 843.76 | About 2.5–5 W | Excellent front stereo metric depth and on-device AI, but only one front sector | Fast but poor value for surround v1 |
| [RPLIDAR S2 S2M1-R](https://ca.robotshop.com/fr/products/scanner-laser-360-rplidar-s2-30-m), 2D | CAD 570; 10 in stock; USB adapter listed separately at CAD 28.57 | CAD 638.40 scanner-only, about CAD 670.40 with adapter | More than 2 W; exact startup budget still required | Accurate anonymous 360-degree range in one plane, IP65 | Stock is plausible, but roof geometry fails and a camera is still needed |
| [Unitree 4D LiDAR L2](https://ca.robotshop.com/products/unitree-4d-lidar-l2), 3D | CAD 628.50 | CAD 703.92 before 12 V/weather integration | About 10 W, up to roughly 13 W with heating | Valid inverted roof geometry; the listing says 360 by 96 degrees and 64k effective points/s | Canadian page says restocking with no ETA; official store also says backordered |
| [RoboSense Airy](https://store.robosense.ai/products/airy), 3D | USD 999 before Canadian costs | More than roughly CAD 1,500 landed at current planning exchange/tax, before some accessories | Less than 8 W | 360 by 90 degrees and stronger outdoor ingress | Consumes most of the entire budget; delivery is not dependable enough |
| Commodity UVC cameras | Roughly CAD 30–130 each | Often CAD 300–650 after four pods, long USB, powered hub and mounts | Usually low | Lowest sensor price | Weatherproofing, cabling and host inference erase much of the saving in one week |

Camera and lidar answer different questions. RGB answers “is that a person and
what social cue is visible?” but is light-, occlusion-, and privacy-sensitive.
Lidar answers “where is a reflecting surface?” reliably in metric geometry but
does not by itself identify a person. Three-dimensional lidar is the technically
cleanest anonymous surround geometry; cameras are the better first purchase for
a social assistant. Cheap radar fills the presence/range gap without consuming
the lidar budget.

One OAK-D W does not solve surround perception. Three are the practical minimum
for nominal wide-angle coverage around the cart and would cost about **CAD
2,531.29 after assumed BC tax before audio, mounts, power, or weather
protection**, already over the complete hardware ceiling.

## Recommended landed bill of materials

### Exact observed retail lines

| Item | Qty | Pre-tax CAD | Planned taxed/landed CAD | Availability evidence and gate |
| --- | ---: | ---: | ---: | --- |
| [Reolink Duo 3V PoE two-pack](https://www.bestbuy.ca/en-ca/product/reolink-duo-3v-poe-2-pack-16mp-uhd-ik10-dual-lens-poe-camera-with-motion-track-180-panorama-color-night-vision/18929224) | 1 | 419.99 | 470.39 | Online only, free shipping, sale shown through 2026-07-19; dispatch is not delivery, so verify postal-code ETA |
| [DFRobot C4001/SEN0609](https://www.digikey.ca/en/products/detail/dfrobot/SEN0609/23028638) | 4 | 83.40 | 93.41 | CAD 20.85 each and 290 in stock observed |
| [Seeed reSpeaker USB four-mic array/XVF3000](https://www.digikey.ca/en/products/detail/seeed-technology-co-ltd/107990053/8558384) | 1 | 102.36 | 114.64 | 555 in stock; locally obtainable but uses discontinued XVF3000 silicon |
| [Soberton XPCB-12BT](https://www.digikey.ca/en/products/detail/soberton-inc/XPCB-12BT/10638209) 10–25 V, 2 x 25 W amplifier | 1 | 36.35 | 40.71 | 357 in stock; AUX must disable Bluetooth and be verified at every boot |
| [Visaton FR 8 WP, 8 ohm](https://www.digikey.ca/en/products/detail/visaton-gmbh-co-kg/FR-8-WP-8-OHM-BLACK/9842335) | 1 | 43.95 | 49.22 | 708 in stock; 15 W RMS, weather-resistant only when correctly mounted |
| [Opaque Hammond 1554E2GY IP68/NEMA 4X enclosure example](https://www.digikey.ca/en/products/detail/hammond-manufacturing/1554E2GY/2359929) | 1 | 35.11 | 39.32 | 1,490 in stock; size/thermal layout must be checked before treating this exact box as final |
| [Littelfuse FHAS100 sealed fuse holder](https://www.digikey.ca/en/products/detail/littelfuse-commercial-vehicle-products/FHAS100/15775916) plus in-stock [0287003.H 3 A fuse](https://www.digikey.ca/en/products/detail/littelfuse-inc/0287003-H/3104042) | 1 | 27.23 | 30.50 | 32 V-rated downstream 24 V audio branch example only; never use on the 48 V pack side, and finalize only after rail/wire/device audit |
| [Dayton TT25-8 Puck](https://solen.ca/en/products/dayton-audio-tt25-8-puck-tactile-transducer-mini-bass-shaker-8-ohm) plus SMRK-2 ring | 1 | 32.50 | CAD 58.80–81.20 including conservative tax on CAD 20–40 estimated expedited shipping | Eight individual pucks reported in stock; telephone/checkout confirmation required |

The DigiKey lines, including all four radars, total CAD 328.40 pre-tax and
approximately CAD 367.81 after BC tax. That clears DigiKey's CAD 100 Canadian
free-shipping threshold. The exact distributor promise and cut-off time still
control the order.

### Exact power and camera-network candidates

These parts replace—not supplement—the two unsafe 4–38 V modules. Selection is
conditional on battery labels, measured charger/transient maximum, BMS rules and
qualified full-pack protection.

| Item | Qty | Pre-tax CAD | Planned taxed CAD | Current evidence and role |
| --- | ---: | ---: | ---: | --- |
| [Mean Well DDR-240C-24](https://www.mouser.ca/ProductDetail/MEAN-WELL/DDR-240C-24?qs=w%2Fv1CP2dgqouKa%252BL5o5nyg%3D%3D) | 1 | 145.01 | 162.41 | 130 shown able to ship immediately; 33.6–67.2 V input, isolated 24 V/10 A/240 W accessory rail, 91% typical efficiency, remote on/off and DC-OK |
| [Mean Well RSD-60L-12](https://www.mouser.ca/ProductDetail/MEAN-WELL/RSD-60L-12?qs=Mv7BduZupUihW4A7NyykSQ%3D%3D) | 1 | 61.34 | 68.70 | 906 shown able to ship immediately; 18–72 V input, isolated 12 V/5 A/60 W, 93% typical efficiency, dedicated Jetson supply |
| [Mean Well DDR-60L-12](https://www.digikey.ca/en/products/detail/mean-well-usa-inc/DDR-60L-12/8681217) | 1 | 49.96 | 55.96 | 662 shown stocked; 18–75 V input, isolated 12 V/5 A/60 W, 91% typical efficiency, dedicated cameras/network |
| [Brainboxes SW-005](https://www.digikey.ca/en/products/detail/brainboxes/SW-005/10707220) | 1 | 81.31 | 91.07 | 616 shown stocked; five 10/100 ports, 5–30 V input, 1.1 W maximum, -10–60 C, IP30 protected-bay switch |

The two Mouser lines total CAD 206.35 pre-tax/CAD 231.11 after assumed BC tax.
The two DigiKey lines total CAD 131.27 pre-tax/CAD 147.02 after tax. Each order
clears that distributor's stated Canadian free-shipping threshold, but checkout
controls. Core conversion and camera networking therefore total **CAD 337.62
pre-tax / CAD 378.13 after assumed tax**.

Order totals apply 12% tax to unrounded pre-tax subtotals. Individually displayed
taxed line items are rounded to cents, so adding their displayed values can differ
from the controlling order subtotal by one cent.

These are still conditional integration candidates. The DDR-240 installation
manual requires vertical input-down mounting, a dry Pollution Degree 2 setting,
and FG connected to PE. The RSD-60 also exposes an FG terminal. A vehicle chassis
is not automatically a valid PE or return; a qualified mobile-DC installer must
resolve manufacturer-compliant bonding with the battery, solar, data shields,
and accessible metal, or reject the candidate.

Published typical input inrush is 30 A for the DDR-240C-24 and 20 A for each 60 W
candidate. Simultaneous input application could therefore briefly approach
70 A. This is not a continuous-load estimate and is separate from the 200 W
running cap. Add measured sequencing/precharge or inrush limiting and coordinate
BMS, contactor/switch making duty, conductors, and fuse time-current curves before
energizing all three.

The selected Reolink cameras each accept 12 V DC as well as active PoE and draw
less than 12 W. The direct-DC path avoids a PoE boost stage: at the cameras'
combined 24 W nameplate plus the switch's 1.1 W maximum and the DDR's 91%
typical efficiency, the pack-side estimate is about **27.6 W** before wiring
loss. Allocate 30 W and measure with IR/spotlight worst case even though
spotlights, audio, siren and recording are disabled in service.

Use the Jetson onboard Ethernet interface, then the SW-005, then both cameras.
The cameras are 100 Mb/s devices and their two bounded H.264 streams fit this
switch. A crossover cable is unnecessary. A second USB Ethernet adapter is a
valid cost fallback, but vibration at its non-locking USB connection, device
ordering and two separately configured subnets make it a poorer cart install.

Use two separately fused power runs rather than a barrel Y-splitter. Reolink's
current guidance identifies a 5.5 x 2.1 x 10 mm center-positive camera plug;
verify the received hardware revision and polarity before fabricating the leads.
Set and tamper-mark the adjustable DDR-60L-12 at 12.0 V, then verify startup,
loaded voltage and polarity at each received camera before connection. Give the
SW-005 its own protected output branch rather than sharing either camera fuse.

The active-PoE fallback is a Canadian-stocked Teltonika `TSW101000000` fed by a
dedicated `DDR-60L-24`: four active 802.3af/at ports, 9–30 V input, 2.31 W switch
maximum, -40–75 C, approximately CAD 179.51 pre-tax/CAD 201.05 after assumed
tax for converter plus switch. It is about CAD 54 taxed more and roughly 1 W
higher at the pack than direct camera DC. It is technically sound if single-cable
exterior runs become more valuable than cost; passive PoE is never an option.

The USB-adapter fallback uses the onboard NIC for one camera and a mechanically
retained Linux-compatible USB NIC for the other. It can save roughly CAD 45–50
before tax versus the industrial switch, but consumes a Jetson USB port and adds
hotplug/autosuspend/device-ordering failure modes. If schedule forces it, verify
the `r8152` driver, disable device-specific autosuspend, and run vibration/reconnect
soaks. Ordinary patch cables work with Auto-MDI/MDIX; no crossover is needed.

Network deployment policy:

- dedicate the onboard Ethernet interface to a static private camera subnet;
- assign static Jetson/camera addresses but no camera gateway or DNS, and set
  NetworkManager `ipv4.never-default yes`;
- do not connect the camera switch to a router; Wi-Fi is the only optional uplink;
- disable IP forwarding and use `nftables` to block forwarding between camera
  Ethernet and Wi-Fi;
- have the Jetson initiate only required local HTTPS/RTSP/ONVIF traffic; disable
  P2P/UID, UPnP, DDNS, cloud, email, FTP, recording, camera audio, siren and
  spotlights; and
- prove no media egress by packet capture before field use.

Allow a further **CAD 350–650 landed** for the still mechanically/electrically
dependent installation items:

- full-pack-rated branch fuses/holders with adequate DC interrupt rating, source
  distribution, wire, a normal shutdown controller/relay, DIN rail, touch
  guards, startup-inrush control, isolated runtime power measurement, and the
  protected ventilated power bay;
- a wired four-UART aggregator or adapters, a selected protected 24-to-5 V
  regulator, radar radomes/pods, and protected cabling;
- a regulated audio sub-supply/overvoltage solution for the 25 V-maximum
  Soberton, or a replacement amplifier with adequate 24 V-rail margin;
- two individually fused 18 AWG tinned-copper camera power runs, Ethernet, USB
  and audio cable, glands, gaskets, wind treatment, structural brackets,
  drip loops, strain relief, baffle, fasteners and fabrication.

Planning total:

```text
Reolink pair after assumed BC tax                         CAD 470.39
DigiKey combined radar/audio/protection batch            CAD 367.81
Solen transducer/ring after tax and taxed shipping       CAD  58.80..81.20
exact core power conversion and camera networking        CAD 378.13
remaining protection/weather/mechanics                    CAD 350.00..650.00
--------------------------------------------------------------------------
provisional estimated landed addition                    CAD 1,625.13..1,947.53
headroom under CAD 2,000                                 CAD    52.47..374.87
```

This is an unitemized planning range, not an evidence-backed upper bound or a
checkout quote. The high case leaves only CAD 52.47, so budget compliance remains
unresolved until every line is selected and quoted. Do not spend the reserve
until the protection, grounding, inrush, metering, downstream regulation, mounts,
cable lengths, delivery date, battery limits, shutdown controller, and thermal
layout are known.

### Microphone schedule alternatives

The current [reSpeaker Flex XVF3800 Circular-4](https://www.seeedstudio.com/reSpeaker-Flex-XVF3800-Circular-4-p-6737.html)
is the preferred long-term array: it was USD 54.90 and in stock at Seeed's China
warehouse, with current AEC/AGC/DoA/beamforming/noise-suppression firmware. It is
not the one-week dependency because Canadian delivery is unproven.

The locally stocked four-mic XVF3000 is the schedule-first choice despite its
older/discontinued processor. The locally stocked
[reSpeaker Lite/XU316 two-mic board](https://www.digikey.ca/en/products/detail/seeed-technology-co-ltd/107990273/24814468)
costs CAD 37.36 and saves about CAD 72.80 after assumed tax; use it only if the
four-mic board is unavailable or a bench test proves its approximately 3 m
two-mic pickup adequate around the open cart.

## Placement and field geometry

### Cameras

- Put one panorama camera below the front roof edge and one below the rear edge,
  with their 180-degree arcs facing outward. Start around 25–30 degrees downward
  pitch and adjust after an occupied-cart survey.
- The owner-provided occupied side/rear photograph shows closely spaced roof
  posts/slats and passenger bodies inside the roof perimeter. Put each optical
  face a few centimetres below and just outside that obstruction plane on a
  short bracket attached to the structural roof frame—not a solar panel, panel
  frame or LED strip. An inside-the-slat mount is rejected. Keep the camera body
  high enough to avoid passenger contact and test both empty and fully occupied.
- The exact Duo 3V specifications are 180 degrees horizontal by 53 degrees
  vertical. From 2.13 m, a 1.07–1.37 m child head at 2 m horizontal range is
  about 21–28 degrees below the camera, inside that starting view. Very close
  feet can still clip.
- Arrange a small side overlap if the mounts permit it, and place the two
  panorama seams where posts/bodywork already create the least harmful blind
  sectors. The advertised 180-degree edge is not an acceptance result.
- Disable built-in microphones, speakers, sirens, spotlights, recording, P2P,
  UPnP, cloud, email and FTP. Put both cameras on a wired, no-default-route
  network with no DNS or Internet gateway. Verify with packet capture.
- Use local camera person events only as a cheap trigger until their exact local
  event API is tested. Validate on H.264 substreams at roughly 4–10 FPS with a
  local TensorRT person detector; do not continuously decode both 16 MP streams.
  Store only short-lived track metadata in ordinary operation.

### Radar

- Use **four**, not three, modules. Four 100-degree horizontal beams on 90-degree
  centers give about 10 degrees nominal neighbor overlap; three beams would cover
  only 300 degrees before real-world roll-off.
- Start under the four roof quadrants, around 20–25 degrees downward pitch. Each
  vertical beam is nominally 40 degrees. Configure only the desired social range,
  initially about **1.2–3.05 m (4–10 ft)**, rather than the advertised maximum.
- Put all four RF faces outside the post/slat plane in RF-transparent,
  weather-tested pods. Behind-wood placement is not assumed transparent.
- C4001 is a bare PCB with UART, not an IP-rated multi-target tracking radar. A
  sector reports a coarse dominant presence/range hint, not a reliable bearing or
  proof that the object is a person. Require dwell/approach consistency and
  camera confirmation before a spoken greeting.
- Cart motion creates apparent approach in fixed radar/camera coordinates. Until
  a verified parked/moving signal and moving-cart validation exist, enable
  proactive spoken greetings only while parked; wake-word conversation may remain
  available while moving under the driver's interaction policy.
- Validate RF-transparent pod material, mutual interference, cart reflections,
  passengers, fan/traction motion, wet surfaces and swaying vegetation.

### Proximity fusion

Use the radar sector/range as the anonymous wake-up signal. Associate it with a
camera person box in the same sector and time window. A fixed-camera ground-plane
calibration can provide an additional approximate range when feet are visible.
ZipDepth may rank foreground/background inside a confirmed track, but remains
non-metric and cannot own the social distance gate.

The C4001's documented ranging floor is about 1.2 m, so its initial proactive
spoken-greeting gate is an approach/dwell in the approximate 4–10 ft annulus
plus camera person confirmation. Inside about 4 ft, treat the person as already
close and suppress repeat solicitation; the `Neko Neko` wake path and camera
policy remain available. Proactive greetings are parked-only in revision one.

The raw owner photograph was inspected transiently only. It contained
identifiable people and embedded location metadata, was deleted after the
geometry review, and was not copied into this repository. Before drilling,
obtain front/rear/both-side empty and occupied survey images or a dimensioned
drawing that can be stored under an explicit privacy decision.

## Power acceptance

The following is a deliberately conservative design allocation, not a measured
result:

| Domain | Allocation |
| --- | ---: |
| Jetson, NVMe and cooling through the dedicated RSD supply at the current 15 W module profile | 30 W |
| Two Reolink cameras plus SW-005 downstream load | 26 W |
| Four radars and wired aggregator | 5 W |
| Microphone array and remaining low-voltage data electronics | 5 W |
| Limited amplifier, one 15 W RMS speaker and one 15 W RMS transducer | 35 W |
| All conversion loss, thermal/measurement controls and unallocated contingency | 34 W |
| **Planning simultaneous pack-side total** | **135 W** |

The first five rows are conservative load-domain allowances. The 34 W reserve
contains losses from all three full-pack converters and the still-unselected
downstream sensor/audio regulation, plus controls and unallocated measurement
contingency. This is how the mixed downstream allowances become a conservative
pack-side total; none of it is a measured result yet.

The audio mixer must limit the voice channel to about 12–15 W RMS and the purr
channel to about 10–12 W RMS, with fixed gain/attenuation so a software failure
cannot expose the 15 W drivers to the amplifier's full nameplate. The two drivers
total 30 W RMS, below the owner's 100 W ceiling. Route playback through the
reSpeaker device so its echo canceller receives the far-end reference.

Running-load acceptance requires measurement during simultaneous maximum
approved story audio, purr, wake/ASR, Gemma, camera verification and ZipDepth
sampling. Measure the DDR-240C-24, RSD-60L-12 and DDR-60L-12 inputs with lights
and all other non-Neko accessories positively isolated/off.
Do not count lights against the owner's scoped 200 W Neko limit, and do not hide
their consumption with an undocumented subtraction. Test lights-on coexistence
separately for rail sag, ripple, heat and interference. The Neko build fails if
any post-start running mode or ordinary workload transient exceeds 200 W. Set a
conservative software load-shedding threshold below that limit, provisionally
180 W, but first select an isolated full-pack voltage/current measurement path.
If it conservatively includes lights, early Neko shedding is acceptable; it must
not under-report input. Size every fuse and conductor for its audited circuit,
not from a software watt limit.

Test converter startup inrush separately with a current probe fast enough for
the pulse; a slow watt meter and the 200 W running criterion do not characterize
it. Adding a later Unitree L2 would reserve roughly another 13 W and still fit
the planning envelope after the running build passes.

No traction-pack runtime calculation is required or authorized by this note.

## Purchase and acceptance gates

1. Confirm checkout arrival within seven days to the supplied British Columbia
   postal code V9G 1L8 for every line; “ships in two days” is not “arrives within
   a week.”
2. Trace and isolate both incompatible 4–38 V converter inputs. Record whether
   each presently spans the full string, a two-battery midpoint, or another
   regulated source. Do not operate it on either of the first two topologies.
3. Photograph all four battery labels and record BMS/series permission,
   charger/transient maximum, full/rest/loaded voltage, grounding and prospective
   fault current. Confirm all three selected converter input ranges with margin.
4. Finalize full-pack fuses/holders, FG/PE/chassis bonding, startup-inrush
   sequencing/limiting, shutdown relay/controller, isolated runtime metering,
   the protected 24-to-5 V sensor regulator, the regulated audio supply/OVP or
   replacement amplifier, cable lengths, and output branch protection. Never
   feed passive 24 V into an 802.3af camera.
5. Complete empty and occupied front/rear/both-side survey images or a
   dimensioned sketch showing roof posts, bodywork, outboard camera faces, radar
   pods and the protected electronics bay. The first side/rear photograph is not
   a complete fabrication drawing.
6. Bench one camera and one radar before drilling/fabrication. Prove local RTSP,
   H.264 substream decoding, local person events, network isolation and no media
   egress.
7. Map all 360 degrees with 3.5–4.5-ft targets, adults, groups and every seat
   occupied. Record seam/occlusion blind zones and false greetings.
8. Run rain/splash, dust/dirty lens, condensation, UV/full-sun soak, vibration,
   cold/hot restart, cable-tug and two-hour combined-workload tests.
9. Measure combined watts and audio SPL/vibration during a full five-minute story.
   Do not ship solely from nameplate arithmetic.
10. Because the Jetson developer kit is rated only 0–35 C, prove the enclosure
    temperature policy and orderly degraded shutdown before claiming any 35–40 C
    operation.

## Primary source ledger

- Reolink Duo 3V specifications and local protocols:
  <https://reolink.com/ca/product/reolink-duo-3v-poe/?attribute_pa_version=2-pack>
- Reolink DC-plug guidance:
  <https://support.reolink.com/articles/12972721694617-Getting-Started-with-Power-Adapter/>
- Best Buy Canada current two-pack price, seller and dispatch terms:
  <https://www.bestbuy.ca/en-ca/product/reolink-duo-3v-poe-2-pack-16mp-uhd-ik10-dual-lens-poe-camera-with-motion-track-180-panorama-color-night-vision/18929224>
- Luxonis OAK-D W product/specification:
  <https://shop.luxonis.com/products/oak-d-w>,
  <https://docs.luxonis.com/hardware/products/OAK-D%20W>
- Slamtec S2 and current Canadian listing:
  <https://www.slamtec.com/en/s2/spec>,
  <https://ca.robotshop.com/fr/products/scanner-laser-360-rplidar-s2-30-m>
- Unitree L2 manual, official store and Canadian listing:
  <https://oss-global-cdn.unitree.com/static/Unitree%204D%20LiDAR%20L2%20User%20Manual.pdf>,
  <https://shop.unitree.com/products/unitree-4d-lidar-l2>,
  <https://ca.robotshop.com/products/unitree-4d-lidar-l2>
- Livox Mid-360 outdoor reference specifications:
  <https://www.livoxtech.com/mid-360/specs>
- DFRobot C4001 specifications and Canadian stock:
  <https://www.dfrobot.com/product-2793.html>,
  <https://www.digikey.ca/en/products/detail/dfrobot/SEN0609/23028638>
- Seeed reSpeaker current and locally stocked alternatives:
  <https://www.seeedstudio.com/reSpeaker-Flex-XVF3800-Circular-4-p-6737.html>,
  <https://www.digikey.ca/en/products/detail/seeed-technology-co-ltd/107990053/8558384>,
  <https://www.digikey.ca/en/products/detail/seeed-technology-co-ltd/107990273/24814468>
- Dayton TT25-8 manufacturer specification:
  <https://www.daytonaudio.com/product/1104/tt25-8-puck-tactile-transducer-mini-bass-shaker>
- Mean Well current converter specifications and installation rules:
  <https://www.meanwell.com/Upload/PDF/DDR-240/DDR-240-SPEC.pdf>,
  <https://www.meanwell.com/Upload/PDF/DDR-120%2C240%2C480_EN.pdf>,
  <https://www.meanwell.com/Upload/PDF/RSD-60/RSD-60-SPEC.PDF>,
  <https://www.meanwell.com/Upload/PDF/DDR-60/DDR-60-spec.pdf>
- Brainboxes SW-005 manufacturer specifications:
  <https://www.brainboxes.com/products/industrial-ethernet-switches/page/fast-ethernet>
- Teltonika TSW101 active-PoE fallback and StarTech USB-NIC fallback:
  <https://www.digikey.ca/en/products/detail/teltonika/TSW101000000/18627333>,
  <https://www.getic.lt/files/catalogue/6769/tsw101-6899c24280adb.pdf>,
  <https://www.startech.com/en-ca/networking-io/usb31000s2>
- NVIDIA Jetson Orin Nano developer-kit input and temperature specification:
  <https://developer.nvidia.com/downloads/assets/embedded/secure/jetson/orin_nano/docs/jetson_orin_nano_devkit_carrier_board_specification_sp.pdf>
- Current BC and federal treatment used for the conservative shipping-tax
  allowance:
  <https://www2.gov.bc.ca/assets/gov/taxes/sales-taxes/publications/pst-302-delivery-charges.pdf>,
  <https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/gst-hst-businesses/charge-collect-specific-situations/freight-carriers.html>
