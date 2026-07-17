# Cat Sound Processing and Remix Queue

Last updated: 2026-07-16

This is the working list for sounds that need trimming, splitting, cleanup,
looping, device-specific mastering, or optional creative treatment. Update the
Cat Sounds Master and machine manifests whenever an output is accepted.

## Delivery contract for every derived asset

- Preserve the checked-in original byte-for-byte.
- Use a lossless working/delivery master; record source ID, exact time range,
  operations, sample rate/channels, SHA-256, licence, creator, source URL, and
  whether the output targets speaker or body transducer.
- Measure integrated loudness and oversampled true peak. The current ReplayGain
  values were for listening review, not final acoustic mastering.
- Create separate conservative speaker and transducer masters where both are
  needed. Validate on the final amplifier/drivers before enabling runtime use.
- Mark modifications and carry required attribution for every BY/BY-NC source.
- Never use generative fill or source separation without adding a provenance and
  quality review step. Never treat remix permission as model-training clearance.

## P0 — first usable soundboard

Build status on 2026-07-16: all seven source rows have deterministic lossless
bench candidates, provenance, TASL/change notices, a disabled semantic allowlist,
and automated integrity/mastering tests. This completes the non-hardware build,
not acceptance. Owner listening remains for every derivative, item 21 still
needs intensity/multi-cat labels, item 17 needs continuous loop/phase approval,
and all speaker/transducer candidates need final hardware testing. Exact cuts and
measurements are in `DERIVED_AUDIO_BENCH.md`.

| Item | Output | Work | Acceptance |
| ---: | --- | --- | --- |
| 10 | Speaker | Bench candidate built | Listen/hardware pending; no clipping; `meow_general` |
| 14 | Speaker | Bench candidate built | Listen/hardware pending; natural dynamics retained; `meow_thank_you` |
| 21 | Speaker | Nine bench excerpts built; one overlapping group retained | Owner intensity/multi-cat classification pending; full chorus disabled |
| 17 | Transducer + speaker | Six start/loop/stop bench candidates built; noisy tail excluded | Continuous loop/phase listening and transducer test pending |
| 23 | Transducer + speaker | Two short relaxing-purr bench candidates built | Bass/rattle hardware acceptance pending |
| 24 | Transducer + speaker | Four short/sustained bench candidates built | Character listening pending; speaker versions peak-limited below target; body resonance pending |
| 18 | Transducer + speaker | Two short-interjection bench candidates built | Onset/stop listening and hardware acceptance pending |

## P1 — distinct emotional coverage

| Item | Work | Intended result |
| ---: | --- | --- |
| 1 | Try gentle broadband cleanup/EQ; reject processing if it harms the meow | Plaintive question/attention meow |
| 3 | Reduce minor ambient noise conservatively | Loving, happy affectionate greeting |
| 4 | Master and enforce metadata cooldown | Friendly-but-pushy interaction request |
| 5 | Find scratch-free ranges; create sleep loop and fades | Warm cuddly/rest purr |
| 6 | Inspect cut tail; repair with a natural short fade if possible | Curious/inquisitive meow |
| 7 | Segment only if individual meows improve action control | Excited treat/reward anticipation |
| 9 | Select short representative kitten/older-cat calls | Brief begging/food anticipation without a minute of insistence |
| 11 | Inspect waveform for source clipping; verify or rebuild loop seam | Short contented transducer purr |
| 13 | Master unchanged | Patient neutral question |
| 15 | Preserve or lightly edit the two-cat exchange as a scene | Multi-cat conversation/storytelling, never default solo Neko |
| 16 | Prefer clean middle/later region; remove final 0.5 s; inspect clipping | Hypnotic low-level sleep purr |
| 19 | Remove/avoid microphone impact near 12 s; inspect clipping | Secondary medium contented purr |

## Manual remix and special processing

| Item | Allowed experiment | Hard boundary |
| ---: | --- | --- |
| 8 | Beat-aligned edits, short stingers, rave/music call-and-response, deliberately trippy variants | Manual authenticated trigger only; never greeting, emotion inference, autonomous playback, or routine child interaction |
| 15 | Spatialized or alternating-channel two-cat conversation | Preserve that these are multiple cats; do not impersonate a single Neko utterance |
| 21 | Assemble an optional chorus from the approved individual meows | Default actions use single clips; chorus must be explicit and rate-limited |
| 24 | Short playful snuffle/purr variants and gentle loop experiments | Preserve natural friendly character; no pitch shift that sounds distressed |

Bounded non-generative variation may later test tiny speed/pitch changes on clean
CC0 assets, but every variant needs a listening label and safe gain. Do not apply
random DSP at runtime.

## Deferred external-only sources

- Item 2: deep active/playful purr, 6/10; ambient noise. Add only if cleanup
  supplies a role not covered by items 17, 23, or 24.
- Item 12: mixed meow/purr, 6/10; microphone rubbing/background noise. Inspect
  only if a unique isolated moment is required.
- Item 20: rejected due background noise; no processing planned.
- Item 22: breathy/wheezy and variable microphone distance; retain externally as
  possible source material, not a standalone candidate.

## Completion checklist

When a queue item is accepted:

1. add its derived file under a clearly named `assets/cat-sounds/derived/` path;
2. add source range, processing recipe, licence/attribution, hashes, and device
   role to a derived-assets manifest;
3. update the Cat Sounds Master status/action mapping;
4. add a deterministic supervisor allowlist entry and tests;
5. record speaker/transducer hardware level, true peak, audible defects, and
   rollback in the setup log;
6. only then change its runtime status from disabled.
