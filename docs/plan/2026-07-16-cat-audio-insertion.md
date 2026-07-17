# Curated cat-audio insertion pipeline

Date: 2026-07-16 (America/Vancouver)

## Outcome

Neko now has a deterministic, interruption-safe layer that can replace explicit
expressive `[meow]` and `[purr]` cues with approved real recordings. The code is
integrated into the attended voice loop, but autonomous recorded-sound playback
remains deliberately disabled. Every derived asset still requires its derived
listening decision and the real speaker/transducer hardware acceptance recorded
in the manifest and allowlist. Until then, a marker falls back to Piper/Kiki
speaking the word, so conversation does not fail.

This separates language generation from physical audio authority:

```text
LLM text: "[purr] That's cozy!"
  -> strict marker parser (maximum two cues)
  -> deterministic semantic action: purr_short
  -> deny-by-default manifest/allowlist policy
  -> approval, output, duration, cooldown and integrity gates
  -> weighted selection with no immediate repeat
  -> fixed supervisor gain and PipeWire output target
  -> cancellable pw-play process
```

The model can request only the semantic actions `meow_general` and `purr_short`
through those two markers. It cannot name a file, choose gain, choose a device,
or authorize a pending asset. Plain prose such as `Cats purr when comfy.` is not
parsed as an action. Unknown markers remain text. Cue parsing is capped at two
per response.

## Implementation

`neko/cat_audio.py` retains the earlier non-destructive normalization helpers and
adds:

- `parse_audio_script`, which recognizes only exact case-insensitive `[meow]`
  and `[purr]` markers;
- `CatSoundCatalog`, which loads the checked derived manifest and runtime
  allowlist, fails unless the global runtime and requested action are enabled,
  requires autonomous/output approval, filters to fully accepted assets,
  enforces duration and cooldown, and verifies the selected file SHA-256;
- weighted selection through a system random source, with injectable seeded
  randomness for repeatable tests;
- a per-action/output last-played record that prevents an immediate repeat when
  another approved candidate exists;
- `CatSoundPlayer`, which invokes `/usr/bin/pw-play` with the supervisor's fixed
  gain and optional PipeWire target, and terminates playback on the existing
  barge-in cancellation event.

`scripts/neko_voice_assistant.py` now renders text and recorded-sound parts in
order under one `speaking`/cancellation scope. The first audible-path callback is
emitted once even if a response has multiple parts. Selection/playback events
contain semantic action, public asset ID and logical output only; they do not
accept or disclose arbitrary paths. The CLI exposes logical speaker or body-
transducer output plus optional fixed PipeWire targets. These are operator
configuration, never model output.

The LFM persona permits an expressive cue only at the beginning of its bounded
first sentence. This ensures the first-sentence streaming boundary does not drop
a cue that appears after punctuation. It also explicitly forbids markers for
factual uses of the words.

## Gain and routing

`config/cat-sounds/runtime-allowlist.json` now gives each action an explicit
`default_gain_db` inside its existing min/max envelope:

- speaker meows: 0 dB relative to the already -23 LUFS mastered files;
- purrs: -6 dB for the initial conservative profile.

The model cannot alter these values. `/usr/bin/pw-play --volume` receives the
corresponding linear amplitude. The final fixed gain/EQ and target node for each
physical channel still require the installed amplifier, speaker, transducer and
cart-body tests. The current Bluetooth headphone output represents only the
logical speaker path. Do not infer body-transducer acceptance from it.

## Current fail-closed state

The controlling allowlist still has:

```text
runtime_status = disabled_pending_derived_listening_and_hardware_acceptance
all actions enabled = false
all actions autonomous_allowed = false
```

The derived manifest still marks listening/hardware/release approval as pending.
Changing only one of these fields cannot enable playback: the catalog requires
the global runtime, the action, autonomy, output and all three per-asset approval
fields to pass together. It also re-hashes the selected file immediately before
playback. A local smoke confirmed the checked production policy returns
`cat-sound runtime is disabled`.

## Tests

The repository suite now has 106 passing tests. New coverage verifies:

- strict markers versus ordinary uses of `meow`/`purr`;
- the two-cue bound;
- deny-by-default unknown/raw requests;
- global and per-action disable behavior;
- accepted-asset, duration, output and hash gates;
- weighted seeded selection, cooldown and no immediate repeat;
- fixed-gain and fixed-target PipeWire invocation;
- integrated TTS fallback and a single first-output latency event.

Compilation and `git diff --check` also pass. No real cat recording was played
by this implementation test.

## Activation sequence

1. Complete the guided derived-listening pass for the meow/purr candidates and
   record accepted/rejected status in the master, manifest and attribution notes.
2. With the installed production output at a conservative level, validate each
   accepted file separately on the speaker and/or transducer, including body
   rattles, clipping, apparent loudness and outdoor audibility.
3. Mark only accepted output-specific assets `derived_content_review = accepted`,
   `hardware_acceptance = accepted` and `release_status = accepted`.
4. Enable only the desired semantic actions, set `autonomous_allowed = true`,
   then change the global runtime status to `enabled` in the same reviewed
   milestone.
5. Configure fixed PipeWire speaker/transducer targets and run cue/fallback,
   randomness, cooldown, wake, barge-in and sleep tests.
6. Measure marker-to-acoustic-onset latency and repeat the two-hour combined soak.

Start with `meow_general` and `purr_short`. Keep attention, group, sustained/
looping and novelty actions disabled until their separate intensity, phase-loop,
cooldown and context reviews pass.

## Rollback

Set the global `runtime_status` to a disabled value; this immediately restores
spoken fallback without changing language or TTS services. To remove the feature
entirely, revert the cat-audio module/integration/tests and persona marker text.
Do not delete any curated original, mastered derivative, attribution, review
ledger, or private recording as part of runtime rollback.
