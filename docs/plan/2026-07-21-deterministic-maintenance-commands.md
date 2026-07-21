# Deterministic local maintenance commands

## Owner request and boundary

On 2026-07-21 the owner requested four local voice commands that must bypass the
LLM and never enter conversation history:

- `tell me your IP address` reads the preferred non-loopback IPv4 source address;
- `full reboot` speaks `OK, going to have a quick power nap now!` and only then
  requests a complete Jetson reboot;
- `are you online?` immediately performs the same two-packet ICMP probe as the
  background online monitor and updates shared online state on any transition;
- `are you healthy?` checks Neko's essential units and speaks the exact playful
  success response or a bounded description of unhealthy unit names/states.

The phrases are exact after punctuation/case normalization. They remain behind
the existing wake/session policy: an idle conversation must first address Neko,
while an already active session accepts a normal follow-up. The reboot parser is
deliberately narrow so a general discussion about restarting cannot power-cycle
the computer.

## Implementation

`neko/local_commands.py` owns parsing and the bounded operations.
`scripts/neko_voice_assistant.py` routes these commands before online Codex jobs,
schedule retrieval, stories, thinking cues, or local LFM. Results are spoken
directly and are not retained in LLM history.

IP discovery runs `/usr/sbin/ip -j route get 8.8.8.8`, reads only `prefsrc`,
rejects loopback/invalid output, and spells IPv4 digits individually for reliable
TTS. It does not require Internet reachability; the command asks the kernel which
source address it would use for that route.

The online question calls `ConnectivityMonitor.probe_once()`, which uses the
existing owner-selected `/usr/bin/ping -c 2 -W 2 8.8.8.8`. Its normal transition
callback updates and logs online/offline state immediately.

The reboot request is sequenced after successful acknowledgement playback. It
uses the owner's existing passwordless local-administrator policy through the
fixed argv `/usr/bin/sudo -n /usr/bin/systemctl reboot`; no transcript content is
ever interpolated into a command. If playback is interrupted, reboot is not
requested. A failed request produces a deterministic spoken failure. No new
sudoers or PolicyKit privilege was installed.

## Health contract

`scripts/neko_health_check.py` is a standalone JSON/exit-status wrapper around
the same health logic used by voice. It checks these enabled essential units:

- system: `docker.service`, `neko-llm.service`, `neko-tts-fast.service`,
  `neko-tts.service`, and `neko-what-if-refresh.timer`;
- user: `pipewire.service`, `neko-audio-policy.service`,
  `neko-voice-assistant.service`, and `neko-git-sync.timer`.

For each unit it requires `ActiveState=active`, a successful unit result, and no
journal entry at priorities emergency through error (`0..3`) since that unit's
current active-run timestamp. Only the unit and problem class are logged/spoken; journal message bodies
are never copied into telemetry or speech. The intentionally disabled Gemma and
Audex laboratory profiles are excluded. The three pre-existing failed DHCP/DNS
services are unrelated to Neko and are likewise excluded.

Healthy speech is exactly: `I feel healthy, but you should check me for worms!`
An unhealthy response names each affected Neko function and whether it is down,
failed, uncheckable, or has error-priority journal records.

## Validation and operational caution

Unit coverage verifies exact/near-miss parsing, route JSON and TTS spelling,
fixed reboot argv, active/inactive/error health behavior, privacy-safe summaries,
and voice routing before LLM work. The complete system-Python repository suite
passes 184 tests with one designed dependency skip.

The host reported a boot time of 2026-07-14 09:07 PDT during implementation.
Therefore the owner's immediately preceding observation was an assistant/service
restart, not yet proof of this new full-host reboot command. The command is
installed live, but an owner-initiated spoken reboot and post-boot audio/device
check remain the destructive acceptance test.

## Rollback

Revert `neko/local_commands.py`, `scripts/neko_health_check.py`, and their routing
in `scripts/neko_voice_assistant.py`, then restart
`neko-voice-assistant.service`. No privilege file, package, model, or persistent
health state needs removal.
