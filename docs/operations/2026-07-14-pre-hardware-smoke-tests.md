# Pre-hardware smoke tests — 2026-07-14

This runbook uses temporary USB equipment to validate Neko's replaceable device
boundaries before the production camera, microphone array, amplifier, speakers,
transducer, radars, converters, and switch arrive. Passing these tests does not
accept the production hardware or the cart installation.

## What can be completed now

- Stable discovery of V4L2 cameras and ALSA/PipeWire capture/playback devices,
  including USB reorder and unplug/replug behavior.
- Camera decode, colour conversion, and resize to ZipDepth's `672x384` input
  geometry without retaining frames.
- Microphone capture and resampling to mono 16 kHz PCM, with RMS activity
  measurement but no retained audio.
- Quiet, explicitly requested playback routing through temporary USB headphones.
- Synthetic camera/audio processing when no peripheral is connected.
- The loopback Gemma readiness/persona request and its bounded response latency.
- Development of deterministic commands, state, stories, privacy policy, cloud
  text routing, service health checks, and crash/network-loss tests against
  mocks or temporary devices.
- A real C922-to-ZipDepth scene-quality and combined-load experiment once a
  reviewed test scene is deliberately captured; ZipDepth remains relative depth,
  never a metric greeting or safety sensor.

## What temporary hardware cannot prove

- The Reolink RTSP/substream latency, camera event metadata, two-camera seams,
  private Ethernet isolation, outdoor coverage, weather performance, or occupied
  360-degree geometry.
- C4001 range, four-sector interference, weather pods, approach/dwell behavior,
  or camera/radar confirmation.
- Far-field pickup, four-microphone beamforming, XVF3000 acoustic echo
  cancellation, wind/motor rejection, or eight-azimuth wake performance.
- The Soberton AUX path, fixed gain, amplifier limiter, speaker SPL, body-shaker
  vibration/duty cycle, hardware fail-silent behavior, or playback-to-microphone
  echo under the real acoustics.
- Received-device power, startup, thermal, ingress, cabling, or the combined
  under-200 W acceptance gate.

## Harness

`scripts/smoke_test_devices.py` uses only the system Python standard library and
the already-installed GStreamer/ALSA/PipeWire utilities. The default run sends
camera and microphone data to `fakesink`; it writes no images, audio, or
transcripts and produces JSON metadata/results on stdout. Playback is omitted
unless `--audible` or the explicit `playback` command is used.

### Initial live result

On 2026-07-14, the connected Logitech C922 exposed two V4L2 nodes and one USB
capture device. The first generic camera attempt selected Jetson `nvjpegdec` for
the camera's MJPEG default and failed negotiation. The harness now deliberately
selects the C922's uncompressed `640x360 YUY2 @ 30 fps` mode, centre-crops it to
the engine's 7:4 aspect ratio, then converts and resizes to `672x384 RGB`; this
passed without retaining frames. Separate runs
processed 60 frames in 2.866 seconds and 180 frames in 12.647 seconds. The broad
range (20.94 and 14.23 wall-clock fps, including setup/teardown) is adequate for
software integration but is not a production-camera latency or frame-rate claim.

The C922 microphone passed three seconds of capture/resampling with 27 RMS
samples from -44.43 to -32.38 dBFS on one run. A complete safe suite then passed
synthetic audio/video, 60 live camera frames, 29 microphone level samples, and a
Gemma persona request. The complete-run Gemma response arrived in 2.177 seconds.
No playback was requested, no media was retained, and no temporary result file
remained. Later that day, an Ora GQ Bluetooth headset was paired, trusted, and
reconnect-tested. PipeWire exposed playback and microphone endpoints using its
mSBC HSP/HFP profile, and the owner reported that the connection worked. A
controlled harness tone and A2DP profile remain untested.

Inventory only:

```bash
python3 scripts/smoke_test_devices.py inventory
```

Safe default suite (synthetic paths, connected camera/microphone, Gemma):

```bash
python3 scripts/smoke_test_devices.py all \
  --camera-match C922 \
  --capture-match C922 \
  --frames 60 \
  --duration 3
```

After connecting USB headphones, first inspect their exact ALSA name, turn their
hardware volume down, wear/remove them as appropriate, then request a quiet tone:

```bash
python3 scripts/smoke_test_devices.py playback \
  --playback-match 'USB' \
  --duration 1 \
  --volume 0.02
```

For a Bluetooth headset exposed only through PipeWire, use the bounded ASR path
with the headset selected as PipeWire's default source. It retains no audio and
prints only timing, signal levels, and the final transcript:

```bash
/home/neko/.local/share/neko/venvs/asr/bin/python \
  scripts/neko_asr_transcribe.py \
  --pipewire-seconds 10 \
  --language en \
  --threads 4
```

PipeWire 1.0.5 `pw-record` on this host returns status 1 after the helper's
bounded SIGINT even when it flushes valid PCM. The helper accepts that status
only for its own timed interrupt, with non-empty valid PCM and empty stderr.
Use the reported RMS/peak values to distinguish silence from recognition errors.

Do not use the audible test against the production amplifier until its fixed
gain, driver protection, and safe output limits are established. The script
hard-rejects a software test-tone amplitude above `0.1`; that is a bench guard,
not an SPL or electrical safety limit.

## Swap-over contract

The production devices replace only selectors and transport-specific workers:

| Bench source/sink | Production replacement | Contract retained |
| --- | --- | --- |
| C922 V4L2 frames | two Reolink H.264 RTSP substreams | decoded RGB metadata/frame worker |
| C922/headset USB mic | reSpeaker USB capture | mono 16 kHz ASR feed plus device health |
| USB headphones | reSpeaker 3.5 mm to Soberton AUX | bounded PCM playback and cancellation |
| synthetic presence events | four C4001 plus camera confirmation | typed ephemeral social events |
| synthetic relative-depth frames | selected real-camera ZipDepth samples | `672x384` RGB preprocessing only |

Do not hard-code `/dev/video0` or ALSA card numbers in services. Select the final
camera by RTSP endpoint and the final USB audio device by stable USB/ALSA identity;
record received serial-specific udev details only in local configuration if they
are needed, not in committed documentation.

## Remaining immediate sequence

1. Run this harness after every USB plug/unplug and after one real cold reboot.
2. Build the deterministic behavior/health skeleton and canned-audio fallback.
3. Select and benchmark one local wake/VAD/ASR/TTS chain at a time against the
   temporary mic/headphones; do not install all candidates into normal boot.
4. Exercise network loss, killed Gemma, missing camera, missing microphone, and
   missing playback; every case must degrade predictably.
5. On arrival, bench one production device of each type and repeat the same
   contracts before mounting or enabling services at boot.
