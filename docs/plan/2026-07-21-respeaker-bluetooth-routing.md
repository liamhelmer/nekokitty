# Bluetooth-speaker/C922 audio with retained ReSpeaker fallback

## Current decision (2026-07-22)

The ReSpeaker and external amplifier exhibited severe electrical resonance in
the cart power environment and cannot be used. Revision one therefore uses an
`AR SEDONA` A2DP Bluetooth speaker for output and the Logitech C922 for capture.
The implementation below remains available for controlled ReSpeaker bench
diagnosis but is superseded operationally.

Two identical speakers are paired, bonded, and trusted without committing their
addresses. The confirmed primary is normally connected; the tested backup is
normally disconnected. The active PipeWire route is the primary's 48 kHz stereo
sink plus the C922 source. The existing policy supports this sink-only Bluetooth
case by falling through to the webcam when the speaker has no capture source.

## Previous owner decision and retained implementation

The ReSpeaker USB array is Neko's primary microphone and primary speaker-output
device. A connected Bluetooth headset is a backup. When both outputs are
available, Neko must play through both; when ReSpeaker is absent, Bluetooth must
become the sole output and microphone. The already-connected C922 microphone is
the final input fallback when neither ReSpeaker nor a Bluetooth microphone is
available. Internal Jetson audio is never selected by this policy.

## Hardware discovery

Immediately after the 2026-07-21 full reboot, the ReSpeaker LEDs lit but Linux
showed no device, USB event, ALSA card, or PipeWire node for it. Replacing its USB
cable fixed the fault. The board then enumerated as Seeed USB `2886:0018`,
`ReSpeaker 4 Mic Array (UAC1.0)`, with a 16 kHz stereo playback sink and a 16 kHz
multi-channel capture source. This is strong evidence that the first cable
provided power without reliable USB data; illuminated LEDs alone do not prove
enumeration.

A four-second direct ReSpeaker microphone smoke test retained no media, returned
success, and observed quiet-scene block RMS from about -70.5 to -57.1 dBFS. This
proves capture, not passenger-distance intelligibility or production SNR.

The factory capture profile exposes the board's processed ASR channel together
with raw microphone channels. Generic mono capture linked all three and would
downmix them. The deployed policy therefore creates
`neko_respeaker_processed` with PipeWire Pulse `module-remap-source`, selects
only the physical source's `front-left`/channel-zero stream, disables remixing,
and makes that mono virtual source the default. On the documented six-channel
factory firmware, channel zero is the DSP-processed ASR channel.

## Dynamic routing implementation

`neko/audio_policy.py` and `scripts/neko_audio_policy.py` run as the enabled,
lingering `neko-audio-policy.service`. Every two seconds they inspect PipeWire
Pulse nodes using JSON from `pactl`. ReSpeaker is matched by official USB IDs or
stable product/card text; Bluetooth is matched generically without committing a
device address. The deterministic policy is:

| Available devices | Default output | Default microphone |
| --- | --- | --- |
| ReSpeaker + Bluetooth | `neko_mirror` to both sinks | processed ReSpeaker channel 0 |
| ReSpeaker only | ReSpeaker sink | processed ReSpeaker channel 0 |
| Bluetooth only | Bluetooth sink | Bluetooth source |
| Neither | leave output unmanaged | C922, if available |

The mirror uses `module-combine-sink`, resampling each follower as required.
Bluetooth and ReSpeaker have different transport latency, so a listener wearing
the headset may hear acoustic doubling from the physical speaker; this is an
accepted consequence of the requested bench mirror and must be judged on-cart.

The service removes only stale modules bearing Neko's exact virtual sink/source
names, recreates them after hotplug changes, and records only route categories,
never Bluetooth addresses. A change in selected physical microphone requests a
nonblocking restart of `neko-voice-assistant.service`, because its long-lived
PipeWire ALSA capture stream binds its source when opened. The voice unit now
orders itself after the notify-ready audio policy at boot.

## Installation and validation

Installed Ubuntu arm64 package `pulseaudio-utils`
`1:16.1+dfsg1-2ubuntu10.1` with `--no-install-recommends`; it added approximately
545 kB and supplies `pactl`. No PulseAudio daemon was installed: `pactl` controls
the existing PipeWire Pulse server.

The first user-service start failed before Python ran because this user manager
could not apply empty capability directives. Those two directives were removed;
the remaining no-new-privileges/read-only sandbox is active. The recovered
service reached active/running with zero restarts after reset.

Six routing tests cover official ReSpeaker identity, mirror choice, Bluetooth
fallback, C922 last fallback, stale-module cleanup, idempotent mirror creation,
processed-source creation, and capture restart on source transition. The full
repository suite passes 190 tests with one designed skip, compileall and
`git diff --check` pass, and both user units pass `systemd-analyze --user verify`.

Two audible tones with silent Bluetooth pre-roll entered `neko_mirror`. Live
PipeWire links and sink-inputs proved simultaneous fan-out to the ReSpeaker's
left/right playback ports and the Bluetooth headset's mono playback port. A
reversible real fallback test disabled the ReSpeaker card profile: output and
input both changed to Bluetooth and the voice process restarted. Restoring the
profile rebuilt the mirror, restored `neko_respeaker_processed`, and restarted
voice capture again. No microphone media was retained.

The 2026-07-22 pairing first selected an unrelated nearby fitness-device audio
endpoint; it produced no audible test and its bond was removed. Pairing the
correct `AR SEDONA` then exposed NVIDIA's R39 systemd drop-in, which launched
BlueZ with `--noplugin=audio,a2dp,avrcp,sap`. Repository source
`deploy/systemd/bluetooth.service.d/zz-neko-audio.conf` is installed below
`/etc/systemd/system` and resets the command to:

```text
/usr/libexec/bluetooth/bluetoothd -d --noplugin=sap
```

The `zz-` ordering is required to override the vendor `nv-` file. After daemon
reload and Bluetooth restart, A2DP connected, the policy selected Bluetooth
output/C922 input, and the owner heard the primary two-tone test. The backup also
connected and completed an explicit-sink tone test before the primary was
restored; owner confirmation of that second tone is pending.

## Persistent reconnection

The 2026-07-23 cold boot preserved both paired/bonded/trusted devices and the
BlueZ A2DP override, but neither speaker connected. BlueZ does not guarantee
outbound reconnection merely because a sink is trusted.

`neko/bluetooth_reconnect.py` and
`scripts/neko_bluetooth_reconnect.py` now run in the enabled lingering
`neko-bluetooth-reconnect.service`. Every ten seconds the service:

1. leaves either configured speaker connected if one is already working;
2. otherwise tries the configured primary;
3. tries the backup only when the primary is unavailable; and
4. keeps polling so a speaker powered after boot can still connect.

The ordered addresses are host configuration, not source:
`~/.config/neko/bluetooth-speakers.env` is mode 0600 and contains the
`NEKO_BLUETOOTH_SPEAKERS` value. The service never prints addresses. Telemetry
contains only state and one-based preference slot. `NOTIFY_SOCKET` is removed
from `bluetoothctl` child environments so only the main process can notify
systemd. The audio policy wants and starts after this reconnect service, and
Neko's health command treats it as essential.

Four focused reconnect tests cover strict configuration parsing, connection
state parsing, no replacement of a working backup, and primary-before-backup
attempt order. A live forced disconnect reconnected slot one during the next
poll and restored the AR SEDONA default sink while C922 remained the default
source.

Outstanding acceptance includes spoken ASR at passenger distance, AEC while the
speaker is active, volume/limiter tuning, speaker-off-at-boot then power-on,
physical backup failover, and another cold boot.

## Rollback

Disable `neko-audio-policy.service`, remove only its user-unit symlink, revert the
voice unit's ordering change, and restart the voice assistant. Stopping the
policy unloads its virtual source and sink. Set defaults manually with `wpctl` or
`pactl`. Remove `pulseaudio-utils` only if no other local tooling depends on
`pactl`; removing the package does not remove PipeWire Pulse.

Disable `neko-bluetooth-reconnect.service` and remove only its user-unit symlink
to stop automatic reconnect. The host-private environment file can then be
removed separately; this does not unpair either speaker.

To restore NVIDIA's BlueZ policy, remove or rename only
`/etc/systemd/system/bluetooth.service.d/zz-neko-audio.conf`, run
`sudo systemctl daemon-reload`, and restart `bluetooth.service`. That rollback
intentionally makes A2DP unavailable again.
