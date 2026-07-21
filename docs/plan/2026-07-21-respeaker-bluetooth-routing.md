# ReSpeaker-first audio with Bluetooth mirror and fallback

## Owner decision

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

Outstanding acceptance includes spoken ASR at passenger distance, AEC while the
amplified speaker is active, mirror audibility/latency listening, volume and
limiter tuning, actual USB unplug/replug, Bluetooth disconnect/reconnect, and a
second cold boot with both devices present.

## Rollback

Disable `neko-audio-policy.service`, remove only its user-unit symlink, revert the
voice unit's ordering change, and restart the voice assistant. Stopping the
policy unloads its virtual source and sink. Set defaults manually with `wpctl` or
`pactl`. Remove `pulseaudio-utils` only if no other local tooling depends on
`pactl`; removing the package does not remove PipeWire Pulse.
