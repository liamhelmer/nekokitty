# Neko audio and voice subsystem — research cut 2026-07-13

## Recommendation

Build the first cart audio system around a Seeed reSpeaker Flex XVF3800
Circular-4, a small two-channel Class-D amplifier, one weather-resistant
full-range speaker, and one body-mounted tactile transducer. Use the microphone
array's playback path for all sound so its hardware acoustic echo canceller has
the correct far-end reference.

The exact listed hardware subtotal was **US$179.30** on 2026-07-13. A practical
installed audio subsystem is expected to cost **US$280–445** before Canadian
tax, depending on enclosure, wiring, shipping, and whether a spare microphone
array is purchased. The owner's approximately US$2,000 ceiling applies to the
combined added system. With the recommended OV9782 perception BOM's exact
installed estimate, audio plus perception is approximately **US$1,378–1,728**,
rounded to **US$1,380–1,730**, before Canadian tax/shipping.

The preferred initial offline software path is:

```text
XVF3800 hardware AEC/beamforming/AGC/noise reduction
  -> openWakeWord: "Neko Neko"
  -> Silero VAD
  -> sherpa-onnx + Nemotron 3.5 ASR Streaming INT8
  -> deterministic intent/policy router
  -> Gemma 4 E2B when generation is needed
  -> Supertonic 3 TTS
  -> deterministic audio mixer/limiter
       -> speech/effects speaker
       -> band-limited body purr transducer
```

This is a research recommendation, not a purchase or installation record. No
audio software or hardware was installed as part of this note.

## Evidence labels

- **Vendor fact** means a specification or compatibility claim from the maker.
- **Observed fact** means availability or price retrieved from the cited page on
  2026-07-13. Prices exclude shipping, duty, Canadian tax, and exchange-rate
  changes.
- **Estimate** means an engineering planning value that has not been measured on
  Neko.
- **Acceptance target** means a proposed project requirement, not a vendor
  guarantee.

## Recommended bill of materials

| Component | Purpose | Observed price | Important facts |
| --- | --- | ---: | --- |
| [Seeed reSpeaker Flex XVF3800 Circular-4](https://www.seeedstudio.com/reSpeaker-Flex-XVF3800-Circular-4-p-6737.html), SKU `100005504` | Far-field capture, playback DAC, and acoustic DSP | US$54.90 | Four circular PDM microphones at 44 mm spacing; vendor describes 360-degree pickup, USB UAC 2.0, XMOS XVF3800 AEC/AGC/DoA/beamforming/VAD/noise suppression/dereverberation, a stereo 3.5 mm DAC output, and an onboard 10 W/4 ohm speaker output. |
| [Dayton Audio KAB-215v2](https://www.parts-express.com/Dayton-Audio-KAB-215v2-2-x-15W-Class-D-Audio-Amplifier-Board-with-Bluetooth-5.0-325-500) | Two independent amplified output buses | US$25.98 | 12–24 VDC, 4–8 ohm load support, 2 x 15 W specified at 19 V into 8 ohms, approximately 90% efficiency. The listed 82.7 mA idle figure is with Bluetooth connected. Actual output at 12 V will differ from the headline rating. |
| [Dayton Audio KAB-FC cable package](https://www.parts-express.com/Dayton-Audio-KAB-FC-Functional-Cables-Package-for-Bluetooth-Amplifier-Boards-325-110) | Power, speaker, and AUX harnesses | US$6.98 | The documented AUX/jumper arrangement allows Bluetooth to be disabled. Disable it for the deployed cart and verify after every configuration change. |
| [Visaton FR 10 WP, 4 ohm, black](https://www.visaton.de/index.php/en/products/drivers/fullrange-systems/fr-10-wp-4-ohm-black) | Neko's voice, meows, cues, and stories | [US$28.16 at DigiKey](https://www.digikey.com/en/products/detail/visaton-gmbh-co-kg/fr-10-wp-4-ohm-black/9842332) | 4-inch full-range driver, 20 W rated/30 W maximum, 80 Hz–16 kHz, 85 dB at 1 W/1 m. Vendor describes saltwater, corrosion, and UV resistance. IP66 applies from the front only when installed with a correct gasket in a sealed enclosure. |
| [Dayton Audio TT25-8 Puck](https://www.daytonaudio.com/product/1104/tt25-8-puck-tactile-transducer-mini-bass-shaker) | Body purr and gentle tactile cues | US$23.99 MSRP | 8 ohms, 15 W RMS/30 W maximum, 40 Hz resonance, approximately 20–80 Hz useful range. |
| [Dayton Audio SMRK-2 mounting ring](https://www.daytonaudio.com/product/1656/smrk-2-surface-mounting-ring-kit-for-tt25-puck-mini-bass-shaker) | Serviceable transducer mounting | US$5.99 MSRP | Surface-mount ring for the TT25 puck. |
| Mean Well [DDR-60G-12 or DDR-60L-12](https://www.meanwell.com/Upload/PDF/DDR-60/DDR-60-SPEC.PDF) | Isolated 12 V/5 A, 60 W audio supply | About US$33.30 | `DDR-60G-12` accepts 9–36 V; `DDR-60L-12` accepts 18–75 V. The G model was [US$33.30 at DigiKey](https://www.digikey.com/en/products/detail/mean-well-usa-inc/DDR-60G-12/8681213). Select only after measuring the cart battery's maximum fully charged voltage. |

Exact arithmetic for one of each listed item:

```text
54.90 + 25.98 + 6.98 + 28.16 + 23.99 + 5.99 + 33.30
= US$179.30
```

Budget another **US$100–200 estimate** for a locking/shielded USB cable, DC-rated
fuse and disconnect, wire, connectors, ferrites, splash enclosure, speaker
baffle and gasket, wind/rain protection, strain relief, vibration mounts, and
fabrication. Seeed's enclosed [reSpeaker XVF3800 USB 4-Mic Array with
Case](https://www.seeedstudio.com/ReSpeaker-XVF3800-USB-4-Mic-Array-With-Case-p-6490.html)
was US$62.99 and is an optional bench unit or spare; the Flex version is the
better final mechanical fit.

Do not order the DC/DC converter until the owner supplies the cart battery's
nominal voltage and measured fully charged maximum. The `DDR-60L-12` is suitable
for many 36/48 V nominal packs but not a pack whose charged maximum exceeds 75
V. If the cart already provides a clean, isolated, correctly fused 12 V rail
with enough headroom, the separate converter may be unnecessary.

### Power planning

The following are **estimates**, not measurements:

| State | Estimated audio-subsystem input power |
| --- | ---: |
| Capture/DSP active, amplifier quiet | 2–5 W |
| Normal speech or gentle purr | 5–15 W |
| Short loud combined peak | less than approximately 30–40 W |

Seeed does not publish a complete Flex board consumption figure. Measure voltage
and current at the audio supply during silence, ordinary speech, maximum allowed
speech, purring, and combined output. Power-gate or put the external amplifier
in standby when quiet if its turn-on transient can be made inaudible. These
figures exclude the Jetson, which remains in its existing 15 W power mode until
the full system is characterized.

## Signal routing and audio format

Use the XVF3800 as both the Linux USB capture device and the USB playback device:

```text
Orin USB
  -> XVF3800 hardware DSP and codec
       -> processed microphone stream -> wake/VAD/ASR
       -> stereo 3.5 mm AUX -> KAB-215v2
            -> left channel -> Visaton full-range speaker
            -> right channel -> TT25-8 body transducer
```

This preserves the playback signal as the far-end reference for hardware AEC.
Use Seeed's official [XVF3800 host-control
utility](https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY/tree/master/host_control)
to inspect direction of arrival and speech energy and to tune and persist the
AEC parameters. In particular, calibrate `AUDIO_MGR_SYS_DELAY` against the real
DAC, amplifier, speaker, enclosure, and acoustic path. Validate barge-in with
speech, meows, stories, and purring rather than assuming the default delay is
correct.

The current [Flex documentation](https://wiki.seeedstudio.com/respeaker_flex_introduction/)
lists `respeaker_flex_ua-io48-cir.bin` as 2-channel, 48 kHz stereo firmware,
while adjacent generic USB prose describes 16 kHz operation. Pin the exact
firmware revision and checksum it; after flashing, record the actual ALSA
descriptors and loopback behavior. The proposed deployed path is 48 kHz duplex
for better playback quality, with capture downsampled to the ASR model's 16 kHz
mono input. Supertonic's 44.1 kHz output should be resampled once in the audio
mixer to the 48 kHz device rate.

The audio scheduler, not the language model, must own routing, volume, ducking,
barge-in cancellation, fades, filters, maximum duration, and fail-silent
behavior. The transducer bus needs a low-pass or band-pass filter, limiter,
maximum duty cycle, and watchdog. Start a purr around 40–60 Hz at low level with
gentle attack and release.

## Mechanical placement

- Mount the circular microphone board horizontally near the roof center. Center
  placement minimizes roof/occupant shadowing and is more appropriate for
  all-around listening than a front-only mount.
- Use the included 20 cm FPC to keep the microphone aperture separate from the
  protected core electronics. Mount the core board, amplifier, and DC/DC unit
  inside a ventilated splash enclosure.
- The bare Flex board is not weather-rated. Provide an acoustically open
  aperture, roof rain lip, drainage path, and a replaceable open-cell windscreen
  approximately 5–10 mm away from the microphone ports.
- Isolate the entire microphone PCB on silicone M3 grommets. Do not cover or
  individually isolate microphone ports. Provide FPC and USB strain relief.
- Keep the array roughly 0.5 m or more from the speaker, Jetson fan, DC/DC
  converter, and traction-power wiring where the cart geometry permits. Use
  shielded/locking USB, short analog cable, star grounding, and ferrites as
  indicated by measured noise.
- Aim the speaker downward and outward from Neko's mouth area and baffle its
  direct path toward the roof microphone. The driver requires a sealed,
  correctly gasketed enclosure to retain its front-side IP rating.
- Attach the purr transducer to a lightweight rigid cat body or belly panel, not
  the passenger seat or vehicle chassis. A passenger-facing or chassis-mounted
  shaker could surprise or distract the driver and would couple more strongly
  into the microphones.
- Mechanical purr vibration is not ordinary acoustic echo and may survive AEC.
  Initially pause wake recognition during purrs, or use a separately measured
  purr threshold profile, until full-duplex tests demonstrate reliable results.
- Provision cable and mounting space for a second rear speaker but purchase it
  only if real all-around audibility testing shows one front/downward speaker is
  inadequate.

The vendor's nominal far-field/circular-pickup claims are not evidence of usable
speech recognition at five metres in wind and motor noise. Treat conversation
as a parked or slow-speed feature. While moving, provide a close-range or
physical push-to-talk path for important commands. Voice input must never
control vehicle motion in this revision.

## Offline wake word and turn detection

### Wake phrase

Use **`Neko Neko`** as the primary wake phrase.

Avoid `Hello Kitty` in a public-facing deployment. Sanrio's current
[intellectual-property statement](https://www.sanrio.com/pages/sanrio-intellectual-property-info)
says that it owns the HELLO KITTY names and images and that only authorized
parties may make products and services featuring them. The owner's personal,
noncommercial use lowers practical risk but does not create permission or avoid
the risk of implied affiliation. This is risk guidance, not legal advice.

### First candidate: openWakeWord

[openWakeWord](https://github.com/dscripka/openWakeWord) is the shortest path to
a custom `Neko Neko` detector on Linux Arm64. It supports ONNX inference,
optional Speex noise suppression, a Silero VAD gate, and a documented custom
model workflow. The code is Apache-2.0; released pretrained models are licensed
CC BY-NC-SA 4.0. The stated personal/noncommercial deployment is compatible
with the noncommercial condition, but the exact generated model, data, and
dependencies must still receive a license record.

The last tagged openWakeWord release is old relative to this project, so
benchmark the same cart corpus with [sherpa-onnx keyword
spotting](https://github.com/k2-fsa/sherpa-onnx). Sherpa is actively maintained,
supports Linux Arm64/Jetson, and could consolidate wake word, VAD, and ASR in one
native runtime. [microWakeWord](https://github.com/OHF-Voice/micro-wake-word) is
current but still describes high-quality custom-model training as difficult; it
is not the short-timeline primary. Picovoice Porcupine is a possible prototype,
but its AccessKey requirement and unclear generic Jetson Linux Arm64 support
make it unsuitable as an autonomous dependency without further verification.

Train and evaluate `Neko Neko` using several adult and child voices, accents,
EN/FR/ES speakers, eight approach azimuths, near/far speech, Neko's own output,
motor and fan noise, wind, crowd conversation, music, and the purr transducer.
Do not tune only against clean desktop recordings.

### VAD and end of turn

[Silero VAD](https://github.com/snakers4/silero-vad), observed at v6.2.1, is the
initial utterance-boundary candidate. Its upstream describes a roughly 2 MB,
MIT-licensed model supporting 8 and 16 kHz audio and more than 6,000 languages.
The published sub-millisecond 30 ms-chunk figure is an upstream x86 CPU result,
not a Jetson measurement. Use the XVF speech-energy signal as a cheap first
gate, and Silero for software endpointing. Start with conservative XVF noise
reduction so hardware and software suppression do not erase children's speech.

## Offline ASR

### Primary experiment: Nemotron 3.5 ASR Streaming through sherpa-onnx

NVIDIA released
[Nemotron 3.5 ASR Streaming 0.6B](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b)
on 2026-06-04. The official model is a 0.6B-parameter cache-aware
FastConformer-RNNT under OpenMDW-1.1. It supports 40 language-locales, with
English, Spanish, and French in the 19-locale transcription-ready tier,
per-stream language selection or automatic language detection, punctuation and
capitalization, and configurable streaming chunks. NVIDIA lists Jetson and
Linux for Tegra as supported, but its published throughput material is not an
Orin Nano 8 GB result.

The full official model uses F32 weights and the NeMo/PyTorch stack, so it is not
the first deployment choice on this board. On 2026-06-11, sherpa-onnx published
an independent INT8 ONNX export. Its [official sherpa
documentation](https://k2-fsa.github.io/sherpa/onnx/nemo/nemotron-streaming.html)
lists the 560 ms files as approximately 627 MB encoder, 14 MB decoder, 9.1 MB
joiner, and 128 KB token file, with microphone and per-stream language examples.
Use the 560 ms profile first as a latency/accuracy compromise.

This quantization is a community conversion rather than an NVIDIA-published
Jetson artifact. Before deployment, pin the sherpa revision and archive hash,
confirm that the upstream OpenMDW terms carry through, compare INT8 quality with
the F32 model on the cart corpus, and measure real-time factor, memory, CPU,
power, and temperature locally. Do not reuse sherpa's non-Jetson benchmark as a
cart claim.

### Portable fallback: whisper.cpp

Benchmark [whisper.cpp](https://github.com/ggml-org/whisper.cpp) with multilingual
`base` and `small` models. The official model table describes approximately 142
MiB for `base` and 466 MiB for `small`; model names without `.en` are
multilingual. Its native C/C++, Arm64, and optional CUDA paths make it a strong
recovery implementation even if Nemotron has better current multilingual
streaming quality.

Use a language hint after the user selects EN/FR/ES rather than repeatedly
auto-detecting a short command. Measure code-switching separately.

## Offline TTS and Neko's voice

### Primary candidate: Supertonic 3

[Supertonic 3](https://github.com/supertone-inc/supertonic), released
2026-04-29, is the strongest short-timeline baseline found in this research. The
official package describes a 99M-parameter ONNX CPU model, 44.1 kHz/16-bit
output, 31 languages including English, French, and Spanish, fixed local voice
styles, ten inline expression tags, quality steps from 5 to 12, speed control,
and a local OpenAI-compatible `/v1/audio/speech` server. The sample code is MIT;
the [model weights](https://huggingface.co/Supertone/supertonic-3) are
OpenRAIL-M. Synthesis is fully local after assets are present.

Audition the female F1–F5 preset styles with motherly, mischievous, soothing,
storytelling, command, French, and Spanish test scripts before collecting a
voice. Expression tags such as laugh, breath, and sigh can provide restrained
character nuance. Do not use them so heavily that speech becomes slow or
difficult for children to understand.

The open-weight package does not include official zero-shot voice cloning.
Supertone's hosted Voice Builder can turn a short reference recording into a
downloadable versioned voice JSON, after which synthesis remains local. Because
that creation step sends audio to a hosted service, it requires separate,
specific human consent and a review of the then-current service terms.

### Second candidate and fallback

- [Pocket TTS](https://github.com/kyutai-labs/pocket-tts), observed at v2.1.0
  released 2026-05-04, is a roughly 100M-parameter CPU streaming candidate with
  bundled voices and current repository claims for EN/FR/DE/PT/IT/ES. Code is
  MIT and published weights use CC BY 4.0. Its published low-latency figures are
  from Apple hardware, not Jetson. Pin and validate the release because some
  model-card language descriptions lag the current repository. Its cloning
  model is explicitly conditioned on consent.
- [Piper](https://github.com/OHF-Voice/piper1-gpl), observed at v1.4.2, is the
  deterministic low-footprint fail-safe. Code is GPL-3.0 and supports Arm64 and
  EN/FR/ES voices, but every voice has its own model-card license that must be
  checked and recorded.

Use canned, licensed meows and an immediate acknowledgement chirp rather than
generating every cat sound through TTS. A sub-250 ms earcon can acknowledge a
successful wake while slower ASR/Gemma/TTS work continues. Heavy pitch shifting
should be avoided because it reduces intelligibility; an adult warm voice,
language, timing, word choice, and restrained cat sounds should carry the
motherly/mischievous personality.

### Recording an original voice

No voice recordings currently exist. If the owner chooses to make them:

- Use a consenting adult and do not imitate a celebrity, known performer, or
  child.
- Obtain a written release that covers local synthetic use, derived embeddings
  or weights, EN/FR/ES usage, storage, deletion, revocation, and whether any
  audio may be uploaded for one-time voice-profile creation.
- As an **engineering recommendation**, record 2–5 minutes total in a quiet,
  treated room as mono 48 kHz/24-bit lossless WAV. Keep the microphone and mouth
  approximately 15–20 cm apart with a pop filter. Capture neutral/motherly,
  playful/mischievous, and story-reading passages.
- Curate multiple clean 10–20 second references rather than relying on one
  lucky take. Store raw masters encrypted off the cart and deploy only the
  minimum embedding/style files where possible.
- Keep meows, chirps, and purrs as separately licensed and reviewed sound assets
  so their level, duration, and meaning remain deterministic.

## Memory and scheduling

Concurrent residency may be possible but is not yet demonstrated. Planning
figures are:

- Gemma 4 E2B CPU path: approximately 2.25 GB peak observed in the existing
  project benchmark.
- Sherpa Nemotron INT8: approximately 650 MB of model files; **estimated**
  1–1.5 GB process footprint after runtime and caches.
- Supertonic 3: 99M parameters; **estimated** 0.5–1.2 GB process footprint
  including ONNX Runtime and working buffers.
- Wake/VAD and orchestration: **estimated** less than 0.7 GB together.

These estimates suggest a roughly 5–6.5 GB complete headless workload but are
not evidence of safe operation within 7.3 GiB usable memory. Benchmark the real
duplex pipeline together. Keep wake and lightweight VAD resident, assign ASR a
bounded thread pool, then serialize Gemma generation and TTS CPU-heavy phases.
Audex should load only after stopping other heavy workers and should never be
required for basic commands.

Gemma's measured CPU TTFT is longer than the desired conversational feel. The
first version should aim for immediate local acknowledgement, deterministic
commands under one second, and conversational first speech in approximately
6–10 seconds until a stable accelerated model path is demonstrated. The owner's
stated tolerance is a few seconds, so this latency needs explicit acceptance
testing rather than being hidden.

## Privacy and cloud consent

Revision one should never send raw microphone audio off the cart:

- Perform XVF processing, wake detection, VAD, ASR, TTS, meows, and purrs
  locally.
- Maintain only a volatile 10–15 second RAM ring buffer needed for wake and
  utterance processing, then discard it.
- Disable raw recordings and transcript logging by default. Logs should retain
  events, timings, failure codes, and aggregate metrics rather than content.
- Under the owner's current policy, only final redacted text may be routed to an
  allowed remote model. Network loss must immediately and transparently fall
  back to local operation.
- A future raw-audio cloud feature must require a one-shot physical button or
  owner UI action, visible recording/upload indication, clear clip/scope review,
  and deletion policy. Spoken `yes` alone is inadequate consent, especially in
  the presence of children.
- A Codex or Z.AI consumer subscription must not be assumed to grant unattended
  API use. API terms, credentials, cost limits, and secrets handling need their
  own deployment decision.

## Cart acceptance corpus and targets

Record a consented test corpus through the final mounted hardware at:

- eight azimuths around the cart;
- 1, 2, 3, and 5 metre distances;
- cart parked, powered, and moving at approved test speeds;
- quiet, fan, motor, wind, crowd, music/story, speech playback, and purr states;
- adult and child speakers with likely accents in English, French, and Spanish;
- natural, quiet, excited, interrupted, and overlapping speech.

Proposed **acceptance targets**, not vendor claims:

| Test | Initial target |
| --- | --- |
| `Neko Neko` true activation | at least 95% parked at 1.5 m; at least 85% parked at 3 m |
| False wake rate | fewer than 1 per 8 representative operating hours |
| Deterministic-command intent accuracy | at least 90% on the cart corpus |
| Audible wake acknowledgement | less than 250 ms after accepted wake |
| Deterministic local response | less than 1 second when no LLM is needed |
| Barge-in | reliably interrupts speech/story playback without self-triggering |
| Output safety | measured SPL cap, no clipping, no latched output after worker failure |

For each ASR/TTS configuration record cold and warm start, endpoint delay,
time-to-first-audio, real-time factor, WER by language/noise condition, wake
misses and false accepts, AEC behavior, process and total RAM, CPU/GPU use,
input power, temperature, SPL, and subjective voice quality. Test amplifier and
transducer temperatures at the maximum configured purr duty cycle. A measured
volume cap suitable for nearby children is required; do not expose raw
amplifier maximum to the language model or ordinary UI.

## Remaining owner decisions

1. Cart battery chemistry, nominal voltage, and measured fully charged maximum;
   whether a clean fused 12 V accessory rail already exists.
2. Exact roof, mouth, electronics-bay, and body-panel geometry; weather exposure
   and available mounting distances.
3. Whether conversation is explicitly parked/slow-only and whether a physical
   push-to-talk button is acceptable while moving.
4. Target maximum SPL at 1 m, quiet hours, and whether the rear arc must hear
   stories at full intelligibility. This determines whether to add a second
   speaker and amplifier channel.
5. Approval to standardize on `Neko Neko` and retire `Hello Kitty` as a wake
   phrase.
6. Whether a Supertonic preset is sufficient for the first ship date or an
   original adult voice and release should be recorded.
7. Desired consistency of the same character voice across EN/FR/ES, and whether
   accented French/Spanish is acceptable for revision one.
8. Source and licensing policy for meows, purr loops, music, and story assets.
9. Exact privacy indicator/button design if any future audio-upload workflow is
   desired. The present recommendation is no off-cart audio.
10. Acceptance of the proposed wake, latency, volume, purr-duty, and moving-cart
    test thresholds.
11. Whether the short timeline justifies ordering a spare enclosed XVF3800 and
    second Visaton speaker with the initial shipment.

## Primary-source ledger

Sources were retrieved on 2026-07-13. Hardware prices are volatile.

- Seeed Flex product and current documentation:
  <https://www.seeedstudio.com/reSpeaker-Flex-XVF3800-Circular-4-p-6737.html>,
  <https://wiki.seeedstudio.com/respeaker_flex_introduction/>
- Seeed XVF3800 control utility:
  <https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY/tree/master/host_control>
- Dayton amplifier and harness:
  <https://www.parts-express.com/Dayton-Audio-KAB-215v2-2-x-15W-Class-D-Audio-Amplifier-Board-with-Bluetooth-5.0-325-500>,
  <https://www.parts-express.com/Dayton-Audio-KAB-FC-Functional-Cables-Package-for-Bluetooth-Amplifier-Boards-325-110>
- Visaton speaker:
  <https://www.visaton.de/index.php/en/products/drivers/fullrange-systems/fr-10-wp-4-ohm-black>
- Dayton tactile transducer and ring:
  <https://www.daytonaudio.com/product/1104/tt25-8-puck-tactile-transducer-mini-bass-shaker>,
  <https://www.daytonaudio.com/product/1656/smrk-2-surface-mounting-ring-kit-for-tt25-puck-mini-bass-shaker>
- Mean Well converter data:
  <https://www.meanwell.com/Upload/PDF/DDR-60/DDR-60-SPEC.PDF>
- openWakeWord, Silero, sherpa-onnx, whisper.cpp:
  <https://github.com/dscripka/openWakeWord>,
  <https://github.com/snakers4/silero-vad>,
  <https://github.com/k2-fsa/sherpa-onnx>,
  <https://github.com/ggml-org/whisper.cpp>
- NVIDIA Nemotron 3.5 ASR and sherpa conversion documentation:
  <https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b>,
  <https://k2-fsa.github.io/sherpa/onnx/nemo/nemotron-streaming.html>
- Supertonic 3:
  <https://github.com/supertone-inc/supertonic>,
  <https://huggingface.co/Supertone/supertonic-3>
- Pocket TTS and Piper:
  <https://github.com/kyutai-labs/pocket-tts>,
  <https://github.com/OHF-Voice/piper1-gpl>
- Sanrio trademark/IP statement:
  <https://www.sanrio.com/pages/sanrio-intellectual-property-info>
