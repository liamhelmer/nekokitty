# Canadian one-week hardware decision — 2026-07-13

This note supersedes the earlier US-dollar purchase recommendation in
[`2026-07-13-perception-bom.md`](2026-07-13-perception-bom.md) and the overseas
audio purchase path in
[`2026-07-13-audio-voice.md`](2026-07-13-audio-voice.md) wherever they conflict.
Those longer notes remain the component and acceptance-test research record.

No part was ordered, installed, wired, or configured while preparing this
update. Prices and stock were observed on 2026-07-13 and must be checked at the
actual checkout. The arithmetic below uses the British Columbia planning rate of
5% GST plus 7% PST because the host timezone is America/Vancouver; the delivery
province and postal-code ETA remain purchase gates.

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
- Rain, dust/dirt, sun, vibration, and temperature exposure are normal.
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
   weather-resistant voice speaker, and one protected body transducer.

This is the lowest-risk path found that is weather-capable, nominally covers the
full azimuth, recognizes people, **can** fit the one-week procurement window if
every checkout gate below passes, stays well below 200 W in the design
allocation, and leaves a useful cash reserve. It is not a claim of perfect
360-degree coverage: panorama seams, roof posts, occupants, bodywork, dirty
lenses, and very close targets still need a measured blind-zone map.

An **inverted hemispherical 3D lidar is geometrically valid on the roof** and is
the preferred later lidar experiment. It is deferred only because current
Canadian stock, weather integration, and landed cost do not beat the camera/radar
build inside this one-week revision.

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
| [Dayton TT25-8 Puck](https://solen.ca/en/products/dayton-audio-tt25-8-puck-tactile-transducer-mini-bass-shaker-8-ohm) plus SMRK-2 ring | 1 | 32.50 | 36.40 plus CAD 20–40 estimated expedited shipping | Eight individual pucks reported in stock; telephone/checkout confirmation required |

The DigiKey lines, including all four radars, total CAD 328.40 pre-tax and
approximately CAD 367.81 after BC tax. That clears DigiKey's CAD 100 Canadian
free-shipping threshold. The exact distributor promise and cut-off time still
control the order.

Allow **CAD 250–450 landed** for the as-yet mechanically dependent items:

- a qualified 24-to-12 V camera branch or a standards-compliant active PoE
  solution, plus a small isolated camera Ethernet switch;
- a wired four-UART aggregator or adapters, regulated 5 V, radar radomes/pods,
  and protected cabling;
- Ethernet, USB and audio cable, glands, gaskets, wind treatment, brackets,
  drip loops, strain relief, baffle, fasteners and fabrication.

Planning total:

```text
Reolink pair after assumed BC tax                         CAD 470.39
DigiKey combined radar/audio/protection batch            CAD 367.81
Solen transducer/ring after tax and estimated shipping   CAD  56.40..76.40
remaining power/network/weather/mechanics                 CAD 250.00..450.00
--------------------------------------------------------------------------
estimated complete landed addition                       CAD 1,144.60..1,364.60
headroom under CAD 2,000                                 CAD   635.40..855.40
```

This is a planning range, not a checkout quote. Do not spend the reserve until
the mounts, 24 V converter, cable lengths, delivery date, and thermal layout are
known.

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
  initially about 1.2–5 m, rather than the advertised maximum.
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

## Power acceptance

The following is a deliberately conservative design allocation, not a measured
result:

| Domain | Allocation |
| --- | ---: |
| Existing Jetson, NVMe and cooling at the current 15 W module profile | 30 W |
| Two Reolink cameras at their nameplate maximum | 24 W |
| Four radars and wired aggregator | 5 W |
| Microphone array, Ethernet switch and low-voltage data electronics | 10 W |
| Limited amplifier, one 15 W RMS speaker and one 15 W RMS transducer | 35 W |
| Conversion loss, thermal controls and measured contingency | 25 W |
| **Planning simultaneous total** | **129 W** |

The audio mixer must limit the voice channel to about 12–15 W RMS and the purr
channel to about 10–12 W RMS, with fixed gain/attenuation so a software failure
cannot expose the 15 W drivers to the amplifier's full nameplate. The two drivers
total 30 W RMS, below the owner's 100 W ceiling. Route playback through the
reSpeaker device so its echo canceller receives the far-end reference.

Acceptance requires measurement during simultaneous maximum approved story
audio, purr, wake/ASR, Gemma, camera verification and ZipDepth sampling. Measure
the 19 V converter input and either (a) the 24 V converter input with lights and
all other non-Neko accessories positively isolated/off, or (b) a dedicated
metered Neko 24 V sub-feed plus separately measured incremental converter loss.
Do not count lights against the owner's scoped 200 W Neko limit, and do not hide
their consumption with an undocumented subtraction. Test lights-on coexistence
separately for rail sag, ripple, heat and interference. The Neko build fails if
its allowed steady or transient operation exceeds 200 W. Set a conservative software
load-shedding threshold below that limit, provisionally 180 W, but size every
fuse and conductor for its own audited circuit rather than using a software watt
limit as electrical protection. Adding a later Unitree L2 would reserve roughly
another 13 W and still fit the planning envelope.

No traction-pack runtime calculation is required or authorized by this note.

## Purchase and acceptance gates

1. Confirm the delivery province and postal-code arrival date for every
   marketplace/overseas line; “ships in two days” is not “arrives within a week.”
2. Photograph the two existing converter labels and verify that both inputs span
   the complete four-battery series string. Record maximum 24 V output tolerance,
   noise/transients and spare current before connecting cameras or audio.
3. Select the exact 24-to-12 V or active-PoE/network topology and all cable
   lengths. Never feed passive 24 V into an 802.3af camera.
4. Produce an occupied-cart sketch/photo showing roof posts, bodywork, front/rear
   camera faces, radar pods and the protected electronics bay.
5. Bench one camera and one radar before drilling/fabrication. Prove local RTSP,
   H.264 substream decoding, local person events, network isolation and no media
   egress.
6. Map all 360 degrees with 3.5–4.5-ft targets, adults, groups and every seat
   occupied. Record seam/occlusion blind zones and false greetings.
7. Run rain/splash, dust/dirty lens, condensation, UV/full-sun soak, vibration,
   cold/hot restart, cable-tug and two-hour combined-workload tests.
8. Measure combined watts and audio SPL/vibration during a full five-minute story.
   Do not ship solely from nameplate arithmetic.

## Primary source ledger

- Reolink Duo 3V specifications and local protocols:
  <https://reolink.com/ca/product/reolink-duo-3v-poe/?attribute_pa_version=2-pack>
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
