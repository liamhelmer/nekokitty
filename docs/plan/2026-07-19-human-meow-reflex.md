# Human-meow reflex

Status: implemented and locally validated on 2026-07-19; live owner acceptance is
pending.

## Behavior contract

This reflex is a deterministic audio-policy path, not an LLM intent. Neko may
answer a finalized VAD segment with one approved real-cat recording only when:

1. streaming ASR produced no recognizable transcript; and
2. the offline tagger reports a `Meow` score strictly greater than `0.10`, or its
   highest-scoring AudioSet label is exactly `Music` or `Mantra`.

Recognizable speech always wins. The tag result and reply are not added to the
conversation history and do not wake or extend an LLM session. A qualifying new
segment may produce another response; misses are acceptable. Selection is
weighted and avoids immediately repeating the previous asset. Every candidate
is capped at ten seconds and is non-interruptible while playing.

The attended headphone profile enables `meow_reply`; the physical deployment
profile remains fail-closed until speaker acceptance. The runtime disregards the
action cooldown for this reflex so a later human meow can receive a fresh reply.
Neko records her own playback interval plus a one-second tail and rejects
overlapping microphone segments, preventing open-speaker recursion. This also
means a human meow that overlaps Neko's reply may be missed until acoustic echo
cancellation or source separation exists.

## Classifier and calibration

The classifier is sherpa-onnx's small INT8 Zipformer AudioSet model, loaded on
CPU with two threads. The full 527-result list is requested because `Meow` must
remain available even when `Speech`, `Music`, or another class ranks higher.
Failure to load disables only this optional reflex. A runtime inference fault is
reported without audio content and disables further tagging for that process so
ambient activity cannot create a hot error loop.

The owner-authorized 45-second C922 fixture contains twelve Silero VAD events.
Five score strictly above ten percent for `Meow` (41.7%); adding the deliberately
permissive `Music` and `Mantra` alternatives yields seven possible replies
(58.3%). This matches the owner's preference for playful partial recall rather
than aggressive detection. The fixture and precise consent/score metadata are in
`tests/fixtures/audio`; it contains the adult owner's voice and no child voice.

Pitch shifting is deferred. The initial reply pool uses naturally varied,
owner-reviewed recordings because synthetic shifts could make clean friendly
meows sound distressed or artificial. It can be evaluated later as separately
reviewed derived assets without changing the classifier policy.

## Acceptance and rollback

Automated acceptance requires the strict threshold, Music/Mantra alternatives,
nonempty-transcript rejection, real-model fixture inference, weighted library
selection without action cooldown, playback bookkeeping, and self-output
exclusion. Live acceptance requires several owner meows to produce occasional
varied replies without Neko answering ordinary speech or recursively answering
her speaker.

Rollback is a source revert of `neko/audio_tagging.py`, its assistant integration,
the `meow_reply` mappings, fixture/tests, and documentation. Removing the model
directory is optional and does not affect conversation, stories, ASR, or TTS.
