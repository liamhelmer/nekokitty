# Casual voice and spoken-purr follow-up

Date: 2026-07-18 (America/Vancouver)

## Status

Implemented in source and activated in the current attended assistant by
restarting `scripts/neko_voice_assistant.py`. No package, model, media asset,
systemd unit, or boot policy changed. Production cat-audio approval remains
separate from the attended-headphone policy.

## Behavior

If an ordinary completed model answer contains a purr word or purr cue, Neko
starts the existing asynchronous long tail purr after all spoken TTS and inline
cat sounds finish. Matching is case-insensitive and covers `purr`, `purrs`,
`purred`, `purring`, elongated `purrrrr`, `purry`, `purrfect`, and approved
`[purr:*]` cues. A final `[purr:tail]` already starts that same action and is
detected structurally, so it is not duplicated. The explicit spoken-purr rule
wins even if the answer already contains three other cues. Child speech can
continue the current session during the tail purr; the purr stops when Neko's
next generated speech is ready, or on stop/sleep/shutdown, as before.

This rule applies to model answers. The reviewed story path starts its own tail
purr after a completed story and uses the later story-density policy below.

## Story-language and sound-density follow-up

All five approved local stories were edited for spoken delivery without changing
their plots, safety lessons, retrieval metadata, or 5–7 audience: contractions,
shorter sentences, everyday words, looser dialogue, playful fragments, and less
formal narration. They remain 500–616 Markdown words and under the five-minute
target. The shared TTS contraction pass also applies to every story chunk as a
backstop.

The old three-sound story ceiling is superseded. `StoryLibrary` now calculates a
total sound budget near one sound per 75 spoken words, bounded to at most ten,
reserves one for the post-story long purr, and places the remaining varied meows
near evenly spaced sentence boundaries. The five current stories receive seven
or eight sounds total, or one per 70.6–79.6 spoken words. This density is local
presentation logic; markers are not stored in story prose or conversation
history. Ordinary replies retain their three-marker parser ceiling.

## Casual-language layers

The LFM system persona now describes Neko as a playful older kid or relaxed
family friend, gives two short positive examples, makes contractions the
default, permits light forms such as `wanna`, `gonna`, `kinda`, and `lemme`, and
limits ordinary answers to one to three short spoken sentences with at most one
useful follow-up. The per-request instruction repeats the short/casual/
contractions requirement close to the generation turn. Temperature remains
`0.45`; changing sampling was unnecessary and would also change factual and
safety variance.

The ordinary complete-stream generation cap changed from 128 to 80 tokens;
nonstreaming text and audio replies changed from 96 to 80. Reviewed local
stories use their separate library path and are not shortened by this cap.

`prepare_tts_text()` now applies a conservative, speech-only contraction pass
after the established `Neko` -> `Nekko` pronunciation rewrite. It covers common
pronoun/auxiliary and negative forms such as `I am` -> `I'm`, `you are` ->
`you're`, `let us` -> `let's`, and `do not` -> `don't`, while preserving sentence
case and word boundaries. It deliberately does not mechanically turn every
`going to` into `gonna`, because that could distort quotations, titles, or
factual wording. Logs, transcripts, model output, and conversation history stay
unchanged; only the TTS request receives these rewrites.

## Local evaluation

Eight ordinary prompts were run against the warm local
`LFM2.5-1.2B-Instruct-Q5_K_M.gguf` at the unchanged temperature of 0.45 before
and during prompt iteration. The baseline was generally grammatical and already
used some contractions, but repeatedly produced service-like phrases such as
`Would you like to`, `Of course`, `I’ll be happy to`, and `let me know`.

An intermediate long negative-instruction prompt backfired: it repeated some
of the prohibited phrases and produced a long answer. That version was removed.
The selected shorter, positive-example prompt produced clearly more casual
forms including `I'm gonna`, `let's`, `yep`, `sure thing`, and shorter everyday
phrasing. The 1.2B model still occasionally emitted a generic greeting, exceeded
the requested sentence count, or produced an emoji despite the prompt. These
are known small-model compliance limits; the deterministic contraction layer
guarantees only the safe audible transformations and does not pretend to solve
general response quality.

The exact live response immediately before restart included `just thinking and
purring a bit`; this is a representative regression case that now requests a
post-speech tail purr. No private audio or transcript was added to Git.

The earlier targeted unit validation passed 37 tests covering persona request
construction, TTS rewriting, purr variants, structural tail-marker
de-duplication, and the explicit-purr override after three cues. The story
follow-up adds density, short-story, and expanded parser-budget regressions.
The final repository suite passed all 147 tests; Python compilation and
`git diff --check` also passed.

## Rollback

Revert the changes in `neko/gemma_client.py`, `neko/tts_protocol.py`, and
`scripts/neko_voice_assistant.py`, plus their tests, then restart the attended
assistant. No artifact removal, package rollback, systemd change, or model
download is needed.
