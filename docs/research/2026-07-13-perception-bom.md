# Social-perception hardware and 360-degree coverage — 2026-07-13

> **Superseded for the one-week revision on 2026-07-13:** the active Canadian
> purchase and integration decision is
> [`2026-07-13-canadian-one-week-bom.md`](2026-07-13-canadian-one-week-bom.md).
> Where this longer note recommends an OAK-D W, RPLIDAR S2L, existing C922, or
> three C4001 sectors, that recommendation is historical research rather than the
> current order. The active build uses **two opposing Reolink Duo 3V PoE cameras
> and four C4001 sectors**. No lidar is purchased this week.

## Current one-week decision

Mount one Reolink Duo 3V PoE below the front roof edge and one below the rear
edge, with their 180-degree panoramas facing in opposite directions. Add **four**
DFRobot C4001 sectors at nominal yaws 0, 90, 180, and 270 degrees. Radar provides
anonymous presence/range hints; a camera-confirmed person is still required
before a spoken greeting. Both cameras remain local-only on an isolated wired
network with recording, microphones, speakers, sirens, P2P, cloud, UPnP, email,
and FTP disabled.

The owner-reported roof underside is about 7 ft (2.13 m). A roof-mounted 2D lidar has
the wrong geometry: level rays pass above children, and tilting one scan plane
does not create a downward surround cone. A child-height S2L is too exposed and
occlusion-prone for this one-week people-carrying build. The preferred later
lidar experiment is an **inverted hemispherical 3D lidar** under the roof, after
delivery, ingress, optical-window, power, and cost gates pass.

## Superseded earlier value-tier recommendation

The following OAK/S2L/C922 design remains useful comparative research, but it is
not the current one-week bill of materials. Neko remains manually driven and no
perception path may command propulsion, steering, or braking.

The earlier short-timeline/value design was:

1. One **Luxonis OAK-D W with the OV9782 wide/global-shutter color sensor** at
   the front, doing person detection, tracking, and metric stereo depth on the
   camera. Luxonis's current USB ingress claims conflict; use USB only after
   written confirmation/certification for the exact camera/OV9782/cable assembly
   and when that cable reaches the protected hub/Jetson. Otherwise prefer the
   specified IP65 PoE/M12 variant and a standards-compliant active injector from
   the 24 V accessory branch.
2. One **Slamtec RPLIDAR S2L** as an anonymous 360-degree horizontal range and
   approach/dwell sensor, but only if Neko has a clear, useful-height scan plane.
3. Reuse the existing **Logitech C922** at the rear for low-rate person
   confirmation. Run it only on a lidar event or at a low idle frame rate.
4. Publish ephemeral track/event metadata to the behavior layer; do not retain
   or transmit ordinary camera frames.

The observed sensor subtotal on 2026-07-13 was **US$778**: US$479 for the OAK-D
W/OV9782 and US$299 for the S2L, with the existing C922 treated as sunk cost.
The US$429 base OAK-D W/IMX378 reduces that to **US$728**, but its 95-degree
horizontal RGB view wastes much of the 127-degree-wide stereo coverage. The
US$50 OV9782 option is the recommended purchase.

This design is conditional on geometry. A 2D lidar produces one plane, not a
3D volume. It is genuinely useful only if it can sit approximately **0.9–1.2 m
above ground, level, with a substantially clear horizon**. A level lidar on a
roughly 2 m roof may scan over children and many adults; one buried among the
cart body or passengers will have large blind sectors. If a clear scan plane is
not possible, use the distributed-radar fallback below rather than pretending
the roof lidar provides 360-degree human coverage.

The recommended USB/OV9782 perception configuration is approximately
**US$1,098–1,283 installed before tax, shipping, and duty**, prudently rounded to
US$1,100–1,300. Combined with the separate audio subsystem's US$280–445 range,
the same arithmetic gives approximately **US$1,378–1,728**, rounded to
**US$1,380–1,730**, against the owner's approximate US$2,000 combined added-system
ceiling. The separate economy configuration can approach US$1,010 for perception
only by using the base camera and reusing some infrastructure. The PoE/OV9782
camera is currently US$150 more than USB; its observed M12/RJ45 cable adds
[US$24.99](https://shop.luxonis.com/products/ethernet-cable-m12-rj45-3m-cable),
and budget US$40–80 as an estimate for the active 24 V-input 802.3af injector.
That makes the provisional PoE perception range **US$1,313–1,538** and the
combined audio/perception range **US$1,593–1,983**, before tax, shipping, and
duty. Use PoE when exact-SKU ingress evidence or the measured exterior route
requires the more robust link, then re-cost the assembled system. Ask whether
the US$2,000 ceiling includes tax, shipping, duty, and fabrication. Do not order
or rewire power until the existing 24 V converter and full battery topology are
audited.

If no useful lidar mounting plane exists, the lowest-cost practical fallback is
one OAK-D W plus three distributed 24 GHz presence/range modules. It costs less
but has materially weaker direction, multi-person, and false-positive behavior.

No perception hardware was purchased while preparing this note. Subsequent
software provisioning created the isolated ZipDepth export environment, faithful
static ONNX, and board-built FP32 and FP16 TensorRT engines. They are experimental
artifacts, not an accepted perception runtime: deterministic TensorRT numerical
parity and model-only timing pass; camera-input geometry, real-scene quality,
end-to-end power/performance, and combined soak remain.

## Evidence labels and price scope

- **Vendor fact** is a specification or behavior documented by the manufacturer.
- **Observed price** is the public price retrieved on 2026-07-13.
- **Estimate/inference** is an engineering planning value that must be measured
  on Neko.
- Prices are US dollars before sales tax, Canadian import costs, shipping, and
  currency movement unless another currency is shown.

## Why three front-roof RGB cameras are not 360-degree perception

Three wide-angle cameras can cover a full circle only when their optical axes
and physical locations expose the full circle. Three cameras clustered under
the front roof cannot see through the roof, cart shell, pillars, seats, driver,
or passengers. Lens field of view cannot recover physically occluded rays.

A usable three-camera surround layout puts pods around the perimeter, normally
at yaw angles of approximately 0, +120, and -120 degrees. Even then it has blind
areas:

- immediately below and inside the cart;
- behind roof posts, cat-body features, the driver, and passengers;
- at stereo's close-range limit;
- around narrow seams if the advertised field of view is diagonal rather than
  horizontal;
- in sun glare, darkness, rain, dirty-lens, reflective, or low-texture cases.

For the requested low-power build, a metric front camera plus a lower-bandwidth
360-degree presence layer is more useful than three host-fed RGB streams. It
also leaves Orin memory and compute for ASR, TTS, and Gemma.

## Superseded OAK/S2L value-tier bill of materials

This table and its US-dollar arithmetic are preserved for later comparison. They
are not the current Canadian one-week purchase list.

| Item | Qty | Observed unit price | Planning power | Role and evidence |
| --- | ---: | ---: | ---: | --- |
| [OAK-D W](https://shop.luxonis.com/products/oak-d-w), OV9782 color option | 1 | US$479 | Up to about 5 W | Front person detection, persistent track, and metric XYZ on the RVC2 device. The product page calls the current USB product IP66, but Luxonis's general ingress page contains a conflicting no-USB-rating statement and its linked certificate does not unambiguously cover every option. Require written confirmation/certificate for the exact SKU, OV9782 option, connector, and waterproof screw-lock cable. The [hardware page](https://docs.luxonis.com/hardware/products/OAK-D%20W) gives approximately 127 degrees horizontal and 79.5 degrees vertical FOV for the wide stereo pair. |
| [OAK-D W PoE](https://shop.luxonis.com/products/oak-d-w-poe), OV9782 option | alternative | US$629 camera | About 4 W average, under 6.25 W | IP65 camera with locking M12 Ethernet, preferred when the measured exterior data run is longer than the exact USB assembly. Add the correctly mated M12 cable and a standards-compliant active 802.3af injector/switch; never feed passive 24 V into the camera. This replaces, rather than duplicates, the USB OAK line. |
| [RPLIDAR S2L](https://www.slamtec.com/en/s2) | 1 | [US$299](https://files.seeedstudio.com/Bazaar/product_pdf/101110081.pdf) | Up to 3 W running; 7.5 W startup | Anonymous 360-degree range clusters. The manufacturer product page advertises IP65. The S2L v2.3 data sheet retrieved through the official [support page](https://www.slamtec.com/en/support) on 2026-07-13 (SHA-256 `3e0432252f0b55ece4ba792de6e2eccaaff4a880d6c8545884a73f063d745bd2`) gives 0.05–18 m on 90% reflectivity, 0.05–8 m on dark/10% reflectivity, 32,000 samples/s, 10 Hz, 0.12-degree angular resolution, typical +/-50 mm accuracy, Class 1 laser, 500 mA typical/600 mA maximum running current, and 1.5 A startup at 5 V. |
| Existing Logitech C922 | 1 | US$0 incremental | Budget 2.5 W until measured | Rear person confirmation. It is already connected; no new camera is needed for the first build. Use low rate/event-triggered capture and an outdoor enclosure. |
| [StarTech ST7300USBME](https://www.startech.com/en-us/usb-hubs/st7300usbme) or equivalent industrial powered USB hub | 1 | US$135.29 observed | Estimate 2–4 W loss/idle | Seven ports, 7–48 V DC input, 35 W downstream USB budget, ESD/surge protection, and locking terminal input. A less expensive powered hub is acceptable for bench work, but vibration and power transients make an industrial hub preferable on the cart. |
| Protected 24 V branch, local 5 V regulation/hub, disconnect, wiring | 1 lot | US$60–120 estimate | Conversion loss included later | Audit the existing full-pack-fed 24 V converter first. Use separately protected sensor distribution. At the S2L connector retain 4.9–5.2 V, no more than 150 mV ripple, and at least its documented 1.5 A startup capacity; a 3 A local design target gives integration margin. |
| Rear-camera pod, lidar rain/splash guard, vibration mounts, strain relief | 1 lot | US$75–150 estimate | Negligible | The current exact USB OAK assembly need not be put behind a second optical window. Keep all guards clear of the camera FOV and lidar plane. Do not add an arbitrary transparent lidar cylinder; Slamtec says translucent-cover feasibility must be cleared with it. |
| Cables, connectors, fabrication contingency | 1 lot | US$50–100 estimate | Negligible | Prefer short, secured USB runs; test every final cable rather than assuming nominal USB length is reliable. |

Cost arithmetic:

```text
OAK-D W/OV9782 + S2L + existing C922
= 479 + 299 + 0
= US$778 sensors

Sensors + hub + power + mechanics/cabling
= 778 + 135.29 + (60..120) + (75..150) + (50..100)
= approximately US$1,098..1,283 installed
```

The separate economy US$1,010 lower estimate assumes the US$429 base camera and
some shared/reused mounting and power parts. Use **US$1,100–1,300** as the
prudent planning range for the recommended OV9782 version.

### Power budget

The following is a design estimate, not a measurement:

```text
OAK-D W                         <= 5 W vendor maximum
RPLIDAR S2L                     ~= 3 W running, 7.5 W startup
C922                            <= 2.5 W USB planning allowance
hub/DC conversion/cabling loss ~= 2..4 W
---------------------------------------------------------------
steady sensor subsystem         ~= 12.5..14.5 W before host inference
```

Provide a **20 W continuous sensor rail with startup headroom**, or use the
35 W-capable industrial hub. Verify at least the S2L's documented 1.5 A startup
at its connector plus the 4.9–5.2 V/ripple limits. A dedicated local 24-to-5 V
regulator should be rated at least 3 A as design margin; do not require 3 A from
a hub port when the verified device requirement is lower. The Jetson's extra
power for rear person detection
is not included. Measure it with the real pipeline. Event-triggered 5–10 FPS
rear processing should be much cheaper than continuous full-resolution video.

### Placement and coverage

**OAK-D W:** mount front-center, outside or immediately under the leading edge of
the 4-by-8-ft solar roof/cat face, clear of fascia and posts. Project the optical
face far enough that a rain/sun eyebrow does not clip its wide FOV. Do not attach
through a solar panel. Start at yaw 0 degrees and pitch 20–25 degrees down.
At about 1.9 m mounting height and an approximately 80-degree vertical FOV, that
starting angle can retain some view above the horizon while placing the lower
ray near the ground roughly 1 m ahead. Confirm it with real child and adult
targets; do not rely on this trigonometric starting point.

**S2L:** place level at a clear 0.9–1.2 m scan height, for example on an exposed
cat-head/cowl feature or a protected short mast. Keep riders, body panels, and
posts out of the horizon where possible. Record a static self-mask for unavoidable
cart returns and a minimum range mask around the chassis. Do not put it at roof
height merely because that makes the mechanical installation easy; its nearly
planar scan would pass above much of the 5–10-year-old audience. A rain cap and
bottom splash/drain treatment must stay outside the plane, the optical band must
remain cleanable, and bottom M3 screws must not exceed Slamtec's 4 mm limit.

The S2L's documented operating range is -10–50 C. The OAK-D W documentation gives
-20–50 C at full VPU utilization. Both belong below the roof edge with shade and
airflow, not on a hot solar-panel surface or in an unventilated clear pod. Reject
the mounting location if the representative parked-sun soak approaches its limit.

**C922:** put it rear-center at yaw 180 degrees with a similar modest downward
pitch, in a splash enclosure with drainage and a replaceable optical window.
Locate it far enough outward that passengers do not block its entire view.

The lidar makes nominal 360-degree **range coverage**, not 360-degree semantic
person recognition. The front OAK supplies the highest-confidence social zone;
the rear C922 confirms rear people. Side lidar clusters remain anonymous.
Neko may make a soft generic meow for a sustained, approaching side cluster,
but should reserve a spoken greeting or conversation for a camera-confirmed
person.

## Superseded three-sector radar fallback research

This earlier fallback paired one OAK with three radar modules. It is retained for
cost/capability history, but three nominal 100-degree sectors cover only 300
degrees before beam roll-off. The current build instead uses four sectors on
90-degree centers and two opposing Reolink panoramas, as specified in the
superseding Canadian note.

| Item | Qty | Unit price | Subtotal | Notes |
| --- | ---: | ---: | ---: | --- |
| OAK-D W, base IMX378 | 1 | US$429 | US$429 | Upgrade to OV9782 for US$50 if the total budget permits. |
| [DFRobot C4001/SEN0609](https://www.dfrobot.com/product-2793.html) 24 GHz radar | 3 | US$13.90 | US$41.70 | The [official wiki](https://wiki.dfrobot.com/sen0609/) gives a 100 x 40-degree beam, 1.2–25 m ranging, 16 m presence claim, 25 m motion claim, UART, and 3.3/5 V operation. |
| RP2040/ESP32-class UART aggregator | 1 | US$20 estimate | US$20 | Three independent UART inputs, watchdog, timestamping, configuration, and one host link. Wireless should be disabled in deployment. |
| RF-transparent weather radomes, brackets, cable | 1 lot | US$60–120 estimate | US$60–120 | The bare radar PCBs are not weather rated. Validate each radome material at 24 GHz. |
| Powered hub/power/fabrication | 1 lot | US$100–190 estimate | US$100–190 | May overlap with other cart infrastructure. |

The sensing subtotal is **US$470.70** with the base OAK or **US$520.70** with
OV9782. A practical installed range is approximately **US$630–800**.

Mount the OAK front. Put the radars near yaws +95, 180, and -95 degrees, at
roughly 1.2–1.5 m height, aimed outward and perhaps 5–10 degrees down. Provide
a metal ground/backshield behind each antenna, but do not cover the active face
with metal. Configure a 3–5 m social maximum rather than the advertised maximum.
Use the C922 for rear semantic confirmation.

This tier is lower confidence than the lidar design:

- a 100-degree sector is not a bearing measurement;
- inexpensive modules commonly expose one dominant target, not a robust list of
  multiple people;
- the documented numeric ranging floor is 1.2 m;
- moving riders, traction hardware, fans, swaying objects, and reflections can
  trigger detections;
- radar can see through some plastics, which is useful or harmful depending on
  the body panel;
- colocated modules may interfere and need physical-spacing/channel/time tests;
- these boards are not rugged or IP rated.

DFRobot support material describes target state, range, speed, and energy output,
not a trustworthy human-classification bit. Treat “human presence” as the
module's intended application, not proof that every report is a person. Require
dwell and approach consistency, camera confirmation for speech, and a cooldown.
If C4001 firmware/target-output behavior is unreliable in testing, the older
[DFRobot SEN0395](https://www.dfrobot.com/product-2282.html) is a more expensive
US$29 fallback with a vendor-documented 100 x 40-degree beam, 9 m presence range,
and 90 mA at 5 V.

The C4001 page does not state operating current. Budget no more than 0.5 W each
until measured; that is an inference from similar modules, not a C4001 vendor
specification.

## Two-camera mid-tier

A second on-device RGB camera is useful only if rear host inference proves too
fragile or expensive:

```text
OAK-D W/IMX378 front        US$429
OAK-1 W/IMX378 rear         US$319
two C4001 side radars        US$27.80
------------------------------------------------
sensor subtotal             US$775.80
```

The current [OAK-1 W](https://shop.luxonis.com/products/oak-1-w) can perform
rear RGB inference/tracking on-device but has no metric depth. Luxonis's
[2026-07-09 pricing notice](https://shop.luxonis.com/pages/pricing-change-oak-lite-oak-1)
documents the current base price change. The OV9782 options add US$50 per camera
and take the sensor subtotal to US$875.80. Power is approximately 5 W for the
OAK-D plus an estimated 3.5–4.5 W for OAK-1 and less than 1 W for the radars,
before power-conversion losses.

Because the C922 already exists, this is an upgrade path, not the initial buy.

## Premium all-OAK surround: technically clean, financially wrong for v1

For true camera-semantic surround coverage, place three wide OAK cameras around
the perimeter at yaw 0, +120, and -120 degrees, each pitched roughly 20–25
degrees down. With the OV9782 sensor's approximately 127–128-degree horizontal
view, this leaves only about 7–8 degrees nominal seam overlap. Place seams away
from pillars and verify the real calibrated FOV.

Two possible hardware totals are:

```text
three OAK-D W/OV9782
= 3 * US$479
= US$1,437 cameras

one OAK-D Pro W/OV9782 front + two OAK-D W/OV9782
= US$579 + 2 * US$479
= US$1,537 cameras
```

The [OAK-D Pro W](https://shop.luxonis.com/products/oak-d-pro-w) adds active IR
illumination/dot projection for the front. With the industrial hub, regulated
power, mounts, and wiring, the passive topology is approximately
**US$1,707–1,842** and the Pro topology approximately **US$1,807–1,942** before
tax/shipping. That consumes almost the entire project ceiling before audio, so
it is a premium later phase rather than the default recommendation.

The three cameras consume up to about 15 W for the passive version. A Pro unit
can draw more with IR enabled; provide a 35 W camera rail rather than sizing to
an optimistic average. All cameras should run their detector, spatial network,
and [object tracker](https://docs.luxonis.com/software-v3/depthai/depthai-components/nodes/object_tracker)
on-device and send only tracklets/XYZ/velocity. Do not stream three RGB and depth
feeds to the Orin in ordinary operation.

The current OAK-1 W/OV9782 costs US$369, only US$110 less per view than OAK-D
W/OV9782. If three new OAK devices are being bought, saving US$330 by abandoning
metric stereo is poor value; choose OAK-D W.

## Commodity UVC cameras plus ZipDepth

This is a useful prototype and backup, not the preferred shipping design.

A representative camera is the Arducam B020201/B0202 IMX291 low-light WDR UVC
module, advertised with a 160-degree diagonal fisheye and up to 300 mA at 5 V.
One current retailer listing was
[EUR 60.90 including VAT](https://www.welectron.com/Arducam-B020201-1080P-Low-Light-WDR-USB-Camera-Module-with-Metal-Case_1)
and showed an approximately three-month lead time on 2026-07-13, which fails the
short-timeline requirement. Equivalent locally stocked UVC modules should be
evaluated rather than waiting for this exact part.

A rough three-camera prototype can land near US$460–550 when reusing the C922
and adding two wide UVC cameras, a powered hub, enclosures, three cheap radars,
and an aggregator. The cameras alone plan around 4.5 W; host inference is the
larger concern.

Compromises include:

- “160 degrees” is diagonal, not guaranteed horizontal coverage;
- no metric depth, onboard AI, hardware synchronization, or rugged enclosure;
- rolling shutter, exposure mismatch, lens distortion, and seam calibration;
- host USB bandwidth and unreliable device identity after reboot;
- three detector streams competing with the LLM, ASR, and TTS;
- front-coincident mounting still cannot see through the cart or passengers.

### ZipDepth's role

[ZipDepth](https://zipdepth.github.io/) is a 6.1M-parameter, approximately
3-GMAC model at 384 x 384. The authors report 77 FPS/13.1 ms for TensorRT FP16
on an Orin NX 16 GB at 15 W. That is not an Orin Nano 8 GB result and excludes
camera capture, person detection, tracking, and the voice stack. The official
[repository](https://github.com/fabiotosi92/ZipDepth) and project evaluation use
affine-invariant inverse depth with scale/shift alignment.

ZipDepth therefore **does not output metres** and cannot own greeting thresholds,
approach speed, or collision decisions. Running three cameras at 5 FPS each may
be computationally feasible, but must be benchmarked on this exact Orin. A
faithful static `384x672` ONNX plus diagnostic FP32 and candidate FP16 TensorRT
engines are now provisioned on this board. Successful export/build is not
enough by itself; the subsequent exact deterministic PyTorch-to-FP32-to-FP16
numerical gates pass and model-only timing is recorded. Camera geometry, real
scene quality, end-to-end power, and combined workload tests remain. See the
[runtime assessment](2026-07-13-zipdepth-runtime.md). A rough extrapolation from
the authors' Orin NX energy data suggests several watts at 15 total FPS; that is
an inference, not a Nano measurement.

Use ZipDepth only after a physical metric layer works, for:

- foreground/background and relative-nearest ordering;
- visual effects or story interactions;
- an auxiliary confidence cue inside a camera-confirmed track;
- experimental gap/occlusion understanding.

Do not keep three ZipDepth contexts/streams active merely to imitate a 3D sensor.
After the remaining camera/combined-soak gates pass, the single provisioned
fixed-shape FP16 engine should process selected frames sequentially.

## Alternatives considered and rejected for the first build

### OAK ToF

The [OAK-D ToF family](https://docs.luxonis.com/hardware/products/OAK-D%20ToF)
provides true time-of-flight depth, roughly 0.2–5 m operation, and strong indoor
accuracy, but its depth view is only about 70 degrees horizontal. At the current
approximately US$479 device price, roughly six would be needed for meaningful
360-degree overlap: about US$2,874 before infrastructure. It does not fit the
power or cost ceiling.

### ST multizone ToF

ST announced the [VL53L9CX](https://www.st.com/en/imaging-and-photonics-solutions/vl53l9cx.html)
on 2026-06-22 with 2,300 zones, a 55 x 42-degree FOV, 5 cm–9 m range, and up to
100 Hz. The product page still described it as evaluation/under characterization
and did not show normal distributor availability at inspection. It is too new
for the shipping schedule. The mature
[VL53L8CX](https://www.st.com/en/imaging-and-photonics-solutions/vl53l8cx.html)
has only 8 x 8 zones, about 45 x 45 degrees, and up to 4 m nominal range; daylight
performance and the number of modules needed make it a near-body supplement, not
the primary 360-degree layer.

### TI mmWave

Three [TI IWRL6432BOOST](https://www.ti.com/tool/IWRL6432BOOST) boards, with
approximately 120-degree azimuth and 80-degree elevation coverage, could form an
excellent anonymous surround tracker. The observed distributor price was
[US$150.01 each](https://www.mouser.com/ProductDetail/Texas-Instruments/IWRL6432BOOST),
or about US$450 for three. The [IWRL6432](https://www.ti.com/product/IWRL6432)
silicon is explicitly designed for low-power presence/motion sensing, and TI
publishes a [people-tracking reference design](https://www.ti.com/tool/TIDEP-01000).

The EVMs still require radar firmware/SDK integration, target-list fusion,
rugged housings, interference tests, and production carrier/power work. Their
headline milliwatt low-power presence modes are not the consumption of a complete
USB EVM continuously producing people tracks. This is the most interesting
phase-two research option, but not the shortest route to a reliable v1.

### Consumer 360 cameras

Products such as the [Ubiquiti G6 Pro 360](https://store.ui.com/us/en/products/uvc-g6-pro-360)
(US$499 observed) or [Insta360 X5](https://store.insta360.com/in/product/x5)
(roughly US$610 observed) offer broad panoramic video, not metric range. They
bring vendor ecosystems, equirectangular distortion, host inference, recording
and privacy concerns, and uncertain continuous embedded/UVC workflows. They do
not solve the actual proximity problem.

### Ultrasonic

The rugged [MaxBotix MB7389](https://maxbotix.com/products/mb7389) is IP67,
very low power, and covers about 0.3–5 m, but costs US$109.95 each, runs at only
6.7 Hz, and reports the largest return in a narrow beam. Eight modules approach
US$880 before the controller, still have gaps/crosstalk, and cannot classify a
person. Ultrasonic is suitable for future near-body confirmation, not primary
social surround sensing.

## Superseded Orin implications for the earlier OAK/S2L design

This section's `front_oak`, RVC2, lidar, and C922 details apply only to the
historical design above. They are not current implementation guidance; the
active Reolink H.264/event and four-C4001 path is defined in the
[`2026-07-13 Canadian one-week BOM`](2026-07-13-canadian-one-week-bom.md).

The earlier value design deliberately offloads front detection, stereo, and tracking to
the OAK's RVC2 processor. Lidar clustering is a small CPU workload. The Orin
should receive compact events such as:

```json
{
  "track_id": "ephemeral-42",
  "source": "front_oak",
  "sector_deg": 12,
  "range_m": 1.8,
  "radial_velocity_mps": -0.4,
  "person_confirmed": true,
  "confidence": 0.91,
  "age_ms": 820
}
```

Do not send full frames through the assistant message bus. Keep OAK host queues
bounded to one or two messages and disable preview/depth streams outside
diagnostics. Rear C922 detection should be event-triggered or 5–10 FPS at a
reduced resolution. A lightweight detector/tracker process is expected to fit
within a few hundred MB, but that is an estimate to be validated alongside
Gemma, ASR, and TTS.

Cross-sensor fusion should be deterministic. Calibrate sensor extrinsics to a
cart coordinate frame, use position/velocity and timing to merge overlapping
tracks, and expire IDs after seconds. Do not use face recognition to deduplicate
people. The behavior state machine, not the LLM, owns dwell, hysteresis,
cooldowns, privacy, and whether a greeting is allowed.

## Privacy and behavior policy

- Process every camera locally. Per the owner's policy, images and audio may
  leave the cart only after explicit human consent; the perception service
  should have no network access by default.
- Do not implement face recognition, demographic inference, identity storage,
  or continuous recording.
- Retain only short-lived anonymous track IDs and aggregate health/false-trigger
  metrics. Diagnostic frame capture must be an explicit, visible maintenance
  mode with bounded retention.
- Add a visible indicator and plain-language sign that local cameras/range
  sensors support interaction.
- Prefer lidar/radar to decide that “someone may be nearby”; require visual
  confirmation before person-specific speech.
- Suggested starting behavior bands: awareness at 4 m, sustained approach/dwell
  for 0.8–1.5 s, spoken greeting at 1–3 m only after person confirmation, and a
  per-sector/person cooldown. Tune from field tests.
- An unconfirmed side event may produce one soft meow. It must not repeatedly
  solicit a passerby or claim to recognize them.
- No perception result in this revision is valid for braking, steering, safe
  clearance, or autonomous motion.

## Phased delivery plan

### Phase 0 — geometry and electrical survey

Before ordering, map the cart body and an occupied cart at 15-degree yaw
increments. Record the front/rear panorama faces, seams, roof posts, four radar
pods, protected electronics bay, solar cabling, full/rest/loaded series-string
voltage, configured BMS limits, both converter labels, and maximum underside-roof
temperature after a parked full-sun soak. The roof-height 2D-lidar geometry is
already rejected for this revision; do not make S2L purchase depend on another
survey.

### Phase 1 — value-tier bench and cart prototype

Order the Reolink Duo 3V PoE two-pack and **four** C4001 modules only after the
postal-code delivery and power/network gates in the superseding Canadian note
pass. Bench one camera and one radar before fabrication. Prove local RTSP/ONVIF,
H.264 substream decoding, local person-event behavior, four-UART aggregation,
network isolation, the bounded local event schema, deterministic social-state
machine, sensor health checks, and no-frame logging.

### Phase 2 — field validation and enclosure

Test the final mounts with real adults and children, passengers in every seat,
motor and accessories on/off, daylight and night, and stationary/slow manual
operation. Tune panorama seams, camera/radar association, dwell, and cooldown.
Then install the exact rated seals/guards, protected 24 V distribution, secured
cabling, dirty-window health checks, and boot health reporting.

### Phase 3 — local camera inference hardening

Validate camera-local person events as triggers, but retain a low-rate local
TensorRT detector on H.264 substreams until the event API proves adequate. Do not
continuously decode both 16 MP streams.

### Phase 4 — optional relative depth and later 3D lidar

The fixed-shape TensorRT FP16 ZipDepth candidate is now built. Only after metric
perception is accepted should it undergo real-camera preprocessing/quality,
end-to-end power/performance, and combined-soak validation as an auxiliary
signal; its deterministic numerical and model-only timing gates already pass.
Evaluate an inverted hemispherical 3D lidar later if Canadian availability,
weather integration, optical-window constraints, and landed cost improve. Do
not substitute a roof-mounted 2D lidar.

## Acceptance tests

Record raw results, software/firmware versions, ambient conditions, input power,
Orin power mode, and mounted geometry for every test.

### Coverage and ranging

- Draw a 360-degree polar coverage map at 15-degree increments and 0.5, 1, 2,
  3, 4, and 6 m where space permits.
- Repeat with the cart empty and with representative adults/children in every
  passenger/driver seat. Mark occluded sectors rather than smoothing them away.
- Test adults, short children, seated/crouched people, groups, partial bodies,
  wheelchairs/strollers, pets, bicycles, plants/flags, and reflective/dark
  clothing.
- Measure camera ground-plane estimates and all four radar sectors against a
  tape/laser reference. Verify the C4001's 1.2 m documented ranging floor.
- Test stationary dwell, perpendicular walking, approach/departure at several
  speeds, people crossing seams, and two people entering one sector.

### False triggers and behavior

- Run at least four-hour unattended observation sessions in representative
  locations with the cart motor/accessories off and on. Classify every event.
- Initial acceptance target: no more than one false spoken greeting in four
  hours and no repeated greeting to the same stationary person during cooldown.
  Generic meows may use a separately measured, less strict threshold.
- Measure event latency from physical entry to track event; target less than
  500 ms after the configured dwell window so total conversational latency stays
  within the owner's “few seconds” requirement.
- Verify that an anonymous side cluster never becomes a spoken/person-specific
  greeting without camera confirmation.

### Environment and mechanics

- Direct sun into each lens, backlight, deep shade, dusk/night, headlamps, wet
  surfaces, and any rain/fog exposure intended for shipping.
- Clean, dusty, fingerprinted, water-spotted, and partly blocked camera/radar
  windows; confirm degraded health rather than confident nonsense.
- Cart vibration, bumps, roof/body flex, wind, and the complete allowed manual
  speed range. Check that calibration and mounts remain fixed.
- Parked full-sun soak beneath the active solar roof, cold start, hot restart,
  condensation transitions, rain/road spray, and the approved cleaning method.
  Pressure washing is excluded unless the complete installed assembly is rated
  for it.
- For radar, test interference with all four modules, passengers, traction
  electronics, DC/DC converters, fans, and RF-transparent body panels.

### Compute, power, restart, and privacy

- Measure cold boot, sensor readiness, warm restart, USB disconnect/reconnect,
  blocked sensor, corrupted/no data, and process crash behavior.
- Verify stable device identity after at least ten reboots and after swapping USB
  ports. A missing sensor must degrade gracefully rather than block audio/LLM
  startup.
- Run at least a two-hour combined perception + wake/ASR + TTS + Gemma soak.
  Record peak/steady DRAM, CPU/GPU load, total input watts, temperatures,
  throttling, dropped frames/events, and response latency.
- Validate the two-camera PoE/network branch and four-radar/aggregator branch at
  full and loaded series-string voltage and during all allowed simultaneous
  workloads.
- Packet-capture or firewall-audit the perception service to prove that frames
  do not leave the cart. Verify that ordinary logs contain metadata only and
  that diagnostic recordings expire as configured.

## Measurements and owner answers still required

1. Cart outer width/length, roof height, roof overhang/cat-head geometry,
   windshield and pillar locations, solar panel/controller/cable layout,
   structural attachment points, and intended sensor mounting surfaces.
2. Photos or a dimensioned sketch with an adult and child seated in every
   position, showing both panorama seams and all four radar sightlines.
3. Minimum child height within the fixed 5–10-year-old audience, desired
   interaction radius, and
   whether proactive interaction is permitted while the cart is moving or only
   parked/very slow.
4. All four battery make/models and topology/BMS; measured full/rest/loaded pack
   voltage, configured BMS limits, and controlled shutdown threshold; both
   converter models, full-pack input wiring, isolation,
   protection, output tolerance/noise, connector type, and available continuous/
   peak watts on the existing 24 V and 19 V branches.
5. Minimum/maximum/storage temperature, rain while operating/parked, overnight
   exposure, washing method, coastal salt, dust/mud, and maximum measured
   underside-roof temperature in full sun.
6. Whether an inverted hemispherical 3D lidar under the roof should be revisited
   after revision one; a roof-mounted 2D lidar is not a current option.
7. Acceptable blind sectors and whether “near-360 anonymous awareness with front/
   rear semantic confirmation” meets the experience, or whether every side
   person must be visually classified.
8. Final Ethernet/power cable lengths and routes, isolated switch location, and
   the exact active-PoE or qualified 24-to-12 V camera topology.
9. Expected operating light at night and whether visible/IR illumination is
   acceptable.
10. Postal-code delivery confirmation and checkout totals for the Canadian
    one-week bill; the active ceiling is CAD 2,000 landed, including tax and
    shipping.

## Source ledger

Primary manufacturer/project sources used in this cut:

- Luxonis OAK-D W product and hardware documentation:
  <https://shop.luxonis.com/products/oak-d-w>,
  <https://docs.luxonis.com/hardware/products/OAK-D%20W>
- Luxonis current ingress and PoE/M12 alternatives:
  <https://docs.luxonis.com/hardware/platform/environmental-specifications/ip-rating>,
  <https://shop.luxonis.com/products/oak-d-w-poe>,
  <https://docs.luxonis.com/hardware/platform/deploy/powering-poe/>,
  <https://shop.luxonis.com/products/ethernet-cable-m12-rj45-3m-cable>
- Luxonis stereo-depth accuracy:
  <https://docs.luxonis.com/hardware/platform/depth/depth-accuracy/>
- Luxonis object tracking:
  <https://docs.luxonis.com/software-v3/depthai/depthai-components/nodes/object_tracker>
- Slamtec S2/S2L product and specifications:
  <https://www.slamtec.com/en/s2>, <https://www.slamtec.com/en/s2/spec>,
  <https://www.slamtec.com/en/support>. The English v2.3 data sheet retrieved
  through support had SHA-256
  `3e0432252f0b55ece4ba792de6e2eccaaff4a880d6c8545884a73f063d745bd2`.
- DFRobot C4001 product and documentation:
  <https://www.dfrobot.com/product-2793.html>,
  <https://wiki.dfrobot.com/sen0609/>
- ZipDepth project and source:
  <https://zipdepth.github.io/>,
  <https://github.com/fabiotosi92/ZipDepth>
- ST ToF parts:
  <https://www.st.com/en/imaging-and-photonics-solutions/vl53l9cx.html>,
  <https://www.st.com/en/imaging-and-photonics-solutions/vl53l8cx.html>
- TI low-power mmWave and people tracking:
  <https://www.ti.com/product/IWRL6432>,
  <https://www.ti.com/tool/IWRL6432BOOST>,
  <https://www.ti.com/tool/TIDEP-01000>
- MaxBotix MB7389:
  <https://maxbotix.com/products/mb7389>

Retailer price evidence is linked next to the relevant observed price. Prices
and availability must be rechecked immediately before ordering.
