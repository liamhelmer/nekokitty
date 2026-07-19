# Quality/latency rebalance — attended experiment

Date: 2026-07-17 (America/Vancouver)

## Status

This is an attended quality experiment, not a production acceptance result. It
supersedes the *default interaction choice* of the 2026-07-16 low-latency
experiment: the fast Piper/LFM first-sentence path remains available for
measurement, but the attended voice-loop default is now Kiki/Micro at 1.2x and
a complete bounded LFM response. No systemd unit was changed.

## Why

The first live test exposed that the 1.309-second measurement was achieved by
an intentionally over-restrictive profile: Lessac/Piper audio, a 2–4-word first
sentence, `temperature=0.1`, and discarding every token after the first
sentence. The result was prompt and intelligible but did not sound like Neko.

The owner now accepts up to five seconds for ordinary replies and ten seconds
for complex replies. Natural speech and a credible character are therefore
product requirements, not optional polish.

## Measured components

All measurements below were warm, local, and use the 15 W Orin Nano profile.
They measure PCM delivery, not acoustic onset.

| Component | Measurement |
| --- | --- |
| LFM Q5_K_M, 256 prompt / 64 generation tokens | 200.19 ms TTFT p50; 29.49 ms inter-token p50; 33.91 tok/s, using the required structured Jetson llama.cpp wrapper and deployed image digest |
| LFM, 10 ordinary prompts, relaxed experimental persona | complete response median 1.639 s, max 2.714 s; first completed sentence median 0.431 s, max 0.698 s |
| LFM, six-example experimental persona | complete response median 1.312 s, max 2.788 s; first sentence median 0.682 s, max 0.962 s |
| Kiki/Micro 1.2x, early short clause | 0.603–1.121 s to first PCM across the tested examples |
| Kiki/Micro 1.2x, single 11–14 word first sentence | 3.048–3.366 s to first PCM |
| Piper/Lessac medium | 0.089–0.630 s to first PCM, but the owner rejected its audible quality in the live test |

Inference: with the new complete-response/Kiki default, a typical warm reply
should start PCM around 2.5–4.5 seconds after speech end when the text begins
with a short clause. A long unbroken first sentence can approach or exceed the
five-second ordinary-response allowance. Actual acoustic onset, P95/P99 and
full ASR/VAD/device measurements remain required.

## Current source changes

- `neko/gemma_client.py` replaces the forced 2–4-word opening with a natural
  spoken-response contract and uses `temperature=0.45`.
- `GemmaClient.reply_complete_streamed()` retains cancellable SSE transport but
  collects a complete bounded reply before the current one-request Kiki worker
  is asked to synthesize it.
- `scripts/neko_voice_assistant.py` defaults to `/run/neko/tts.sock` (the
  accepted Kiki worker) and `--response-mode complete`. The former
  `--response-mode first-sentence` remains an explicit latency-lab option.

The Kiki worker streams sentence frames once it has received text, but the
current protocol cannot accept additional text while rendering its first frame.
Achieving the lower 1.6–2.3 second estimate with natural multi-sentence speech
requires a separate text/PCM queue: synthesize/play the first complete sentence
while LFM continues to generate later sentences. Do not claim that capability
until it is implemented and measured.

## Quality boundary

Prompt examples improved style but did not make the 1.2B model consistently
reliable for factual child questions: observed experimental answers included
incorrect explanations of sky colour and rain. Treat LFM as suitable for brief
social chat, deterministic commands, and tightly curated story material, not as
an unsupervised factual authority. Evaluate a quality-oriented local model
sequentially before expanding open factual conversation.

## Engagement sound proposal

The right engagement sound is a **short, rare acknowledgement**, not a disguise
for latency. Trigger it only after a request is accepted and only when the
supervisor predicts a longer reply (for example, story retrieval, a complex
question, or a model switch). It must be cancellable on barge-in and must not
cover required text.

Candidate derived attention meows are 0.644–0.940 seconds. They are still
fail-closed: the global cat-audio runtime, all actions, and asset approvals are
disabled pending derived listening and real speaker/transducer acceptance. Do
not enable them merely to improve a benchmark.

## Remaining gates

1. Reconnect a real output device and run an attended A/B: Kiki complete versus
   Piper first-sentence, with the owner judging voice and character separately
   from latency.
2. Capture at least 20 warm end-to-end turns, then report P50/P95/P99 from
   speech end to electrical/acoustic onset.
3. Implement and test the sentence/PCM queue before targeting sub-2.5-second
   natural multi-sentence replies.
4. Evaluate a sequential quality model and a deterministic local fact/story
   route; do not solve factual reliability with persona prompting alone.
5. Complete the derived-cat-audio and production-hardware acceptance sequence
   before any autonomous acknowledgement meow is enabled.

## 2026-07-17: expressive real-cat cue contract

The accepted Kiki live test kept an estimated end-of-speech to first-audio range
of 2.37--3.54 seconds. Its response time and voice are acceptable to the owner.
The next interaction-quality priority is regular, appropriate use of the local
curated real meows and purrs, rather than synthesizing the words.

`neko/cat_audio.py` now accepts a closed semantic cue vocabulary. It is parsed
locally in the existing response text, so it adds no model request or tool-call
round trip:

| Model cue | Deterministic action | Intended moment |
| --- | --- | --- |
| `[meow]` / `[feeling:curious]` | `meow_general` | neutral or curious reaction |
| `[meow:thanks]` / `[feeling:grateful]` | `meow_thank_you` | thanks, affection, successful help |
| `[meow:attention]` | `meow_attention_candidate` | short attention request; still disabled |
| `[purr]` | `purr_short` | brief contentment |
| `[purr:relaxed]` / `[feeling:cozy]` | `purr_relaxing_short` | calm or rest |
| `[purr:playful]` / `[feeling:happy]` | `purr_playful_affection` | happy playful connection |

The prompt now frames one cue as normal for **most ordinary replies**, and two
as rare. It explicitly allows no cue when a safety instruction, factual
correction, very short command acknowledgement, or explanation of the words
would be less clear. It requires each cue to be adjacent to the words it
colours and does not permit a model to choose an audio file, gain, output, or
cooldown. Unknown bracket text is ordinary spoken text, not an action.

The production allowlist remains disabled. A separate
`config/cat-sounds/attended-headphone-allowlist.json`, usable only with
`--attended-cat-sounds` and speaker output, lets an adult perform an explicit
headphone listening test of selected mastered bench candidates. It is not a
boot setting and cannot approve cart hardware. The normal catalog still requires
derived-content, hardware, and release approval for any production playback.

The 1.2B LFM did not reliably emit a cue during the first attended run. The
supervisor therefore starts a selected short *thinking cue* while local LFM
generates only at a low 12% configured rate. The cue is
chosen from the child's request, not from a model-selected filename: thanks use
the gratitude meow, rest uses a relaxed purr, stories use a playful purr, and
ordinary turns use the neutral meow. This starts actual character audio without
waiting for model text. When model text is ready, it stops the cue and begins
Kiki; user speech cancels Kiki but deliberately **does not** cancel an active
real-cat cue. Explicit stop/sleep/shutdown still cancel both. This satisfies the
owner’s turn-taking rule and prevents a long purr from adding its full duration
to normal reply latency.

Prompt compliance alone is still not enough to make a cue occur *within* spoken
language. When LFM omits one, a local response scaffold now inserts a neutral
meow between the first and second sentence on 75% of multi-sentence ordinary
replies. It never adds the old pre-answer cue to a one-sentence response and
leaves a valid model-emitted cue intact. This is a transparent deterministic
presentation layer, not a fake tool call or extra model latency.

The owner refined the sound grammar: meows are beginnings/inter-sentence
punctuation; short happy purrs are occasional beginnings; long purrs belong
after an affirming reply or happy story. The attended policy now permits the
26-second primary-purr loop. A tail purr is started asynchronously after such a
warm ending, continues while the child begins the next turn, and is stopped only
when Neko's next generated speech is ready (or on explicit stop/sleep/shutdown).
It never blocks a normal answer. This behaviour is supervised-headphone-only
until production hardware acceptance; the exact long-purr rate and shorter-purr
derivative needs remain listening gates.

The first tail-purr continuation test exposed a separate state bug: the normal
30-second dialogue deadline could expire while a story and its 26-second purr
were playing, incorrectly requiring the child to say the wake word again.
`BehaviorController.extend_active_session()` now renews an already-open session
only while a tail purr is active; it never opens one from ambient speech. This
preserves history for an addressed follow-up during the tail. The live headset can
also create VAD edges from its own purr output, so a finalized request is no
longer discarded solely for a speech-sequence change while that tail is active.

## Story sound treatment

The live story route selects exact owner-reviewed text from the local
manifest-gated shelf. The original implementation guaranteed one inter-sentence
meow and an asynchronous ending purr with a three-sound ceiling. On 2026-07-18,
the owner superseded that ceiling with the density policy documented in
`2026-07-18-casual-voice-and-purr-followup.md`: roughly one sound per 75 spoken
words, at most ten, with the final long purr included in the budget.

The persona now records Neko as an orange-and-black striped, tabby/tiger-ish
kitty carrier with fuzzy paws, a long tail, and a deliberately occasional,
non-gross gummy-worm rear-treat-hatch joke. She is a parked, non-autonomous
people carrier who loves light cat stories. "Calico" is not used as a literal
coat description because the specified orange/black stripes describe a tabby;
the owner can deliberately revise that visual canon later.

### Story-library next boundary

The first manifest-gated local shelf is implemented with five original stories.
The next boundary is bounded name/scenario substitution only after the whole
resulting scene passes the existing child policy. Do not ask LFM to invent long
stories from an unconstrained prompt: it has already shown generic and factually
weak answers in short conversation. The existing story research and manifest
rules remain controlling.

## Noisy-event address and pronunciation policy

An opening `Neko` or `Neko Neko` is required only when a child begins speaking
while Neko is actively producing her spoken turn. Unaddressed VAD speech during
that overlap is discarded and cannot cancel either an ordinary reply or a story.
Once Neko's spoken turn is complete, ordinary follow-ups work without repeating
her name for as long as the in-memory session remains active. This includes a
follow-up during an asynchronous tail purr, because the purr follows the completed
spoken turn. An addressed interruption retains the existing bounded dialogue
history and the previous story's curated summary; it does not start a blank
conversation. The global `bye bye`, `goodbye`, and `good bye` sleep phrases remain
unprefixed emergency exits. Generic output playback and synthesized spoken-turn
state are separate: a standalone thinking meow or completed-turn tail purr does
not impose the address requirement, while narration and spoken dialogue do.

For prompt barge-in, the streaming keyword detector accepts Neko only within the
first two seconds of a VAD utterance. During spoken-output overlap, an accepted
opening wake detection is required before the segment can interrupt. KWS can
repair an omitted initial name in ASR, but a later occurrence of Neko is outside
the acoustic prefix window and is not an interrupt. Outside active spoken output,
the deterministic behavior layer accepts unprefixed speech only while a
conversation session is active. This is an
attended bench policy until noisy-event false-accept and false-reject rates are
measured with the production microphone array and speaker echo cancellation.

The character remains written `Neko`. Immediately before a request crosses the
private TTS socket, whole-word case-insensitive `Neko` tokens are rewritten to
`Nekko`. This pronunciation shim does not alter model prompts, story source,
transcripts, logs, history, filenames, or wake-word spelling.

Neko can also hear her own loudspeaker. Spoken text is therefore sent to TTS in
sentence chunks, and microphone KWS detections are ignored while the currently
playing sentence contains Neko's own name. The guard is deliberately narrow:
addressed barge-in remains available during every other sentence. Its tradeoff
is a brief interruption blind spot if a child says Neko over the same sentence.
Production acceptance still requires the microphone array's far-end-reference
acoustic echo cancellation plus loudspeaker/noisy-crowd false-accept and
false-reject measurements; the output-aware guard is not a substitute for AEC.
