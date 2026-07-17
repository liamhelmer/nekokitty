# Interruptible buffered-audio voice loop

> Historical implementation record. The normal route described here was
> superseded later the same day by continuous ASR, LFM2.5 with a real 16K
> context, streamed first-sentence generation, and fast Piper TTS. See
> [Low-latency local voice path](2026-07-16-low-latency-voice.md). The wake,
> barge-in, sleep, privacy, and production-gate findings below remain applicable.

Status on 2026-07-16: attended implementation and automated private-fixture
bench pass; deliberately not boot-enabled. The final repository verification ran
95 tests, compiled all Python sources, and passed `git diff --check`.

## Implemented architecture

```text
16 kHz mono PCM, continuously captured in memory
  -> Silero VAD (speech onset/end plus buffered utterance)
  -> sherpa 3M open-vocabulary keyword spotter
       Neko Neko / Neko pronunciation variants
       bye bye / goodbye sleep commands
  -> deterministic wake/session/stop/sleep policy
  -> Nemotron streaming ASR (best-effort text hint)
  -> same buffered utterance as inline WAV to local Gemma 4 E2B
  -> complete checked response
  -> resident Micro/Kiki TTS -> interruptible PipeWire playback
```

The VAD supplies the requested audio buffer. It retains speech from onset while
the keyword model reaches its decision, so a wake word detected near the middle
of processing does not discard the audio that preceded detection. At end of
turn, Neko serializes the bounded float PCM as a mono 16 kHz WAV in memory and
base64-encodes it directly into the local loopback request. No microphone WAV is
created by the live path and no media leaves the Jetson.

Gemma treats audio as source of truth. Nemotron's transcript is a hint and an
in-memory history label, not the wake gate. This matters because owner-spoken
tests rendered the same activation as forms including `Eko Neko`, one `Neko`,
`Echo Necho`, `Echo necko`, `Go`, or omitted it entirely. The narrow transcript
aliases remain fallback behavior, but the separate keyword model is primary.

Conversation history is limited to six user/assistant turns and 2,400
characters. A new wake session clears previous history; the session expires
after 30 seconds. History and transcripts are process-memory only. Replies remain
bounded at 96 output tokens and are not spoken until complete, which preserves
the whole-response child-safety check at the cost of latency.

## Barge-in behavior

VAD and microphone capture continue while Neko speaks. Speech onset sets a
cancellation event. The TTS client terminates `pw-cat` so queued PCM does not
drain, then shuts down the TTS Unix socket to unblock a pending worker read.
Cancellation wins until the playback process has actually exited; a race found
in the first human attempt was corrected so an exit-1 caused by cancellation is
not treated as an output failure. The single-threaded TTS worker may finish its
current non-interruptible ONNX chunk, but that compute-release delay cannot keep
audio audible.

If a new utterance begins while Gemma is thinking, the stale response is
discarded before playback. If speech begins during playback, playback stops and
the new finalized audio becomes the next turn. The prior turn is recorded with
an interrupted marker rather than the unheard full assistant answer.

`stop`, `cancel`, `stop talking`, and `be quiet` cancel locally. `bye bye`,
`goodbye`, and `good bye` are deterministic sleep words: they cancel playback,
close the session, clear history, and return to wake-only listening without an
LLM call. Short sleep commands are also keyword-spotted because Nemotron returned
an empty transcript for the recorded `bye bye` fixture.

## Reproducible private-fixture test

The owner explicitly authorized recording a small test set. Six trimmed clips
exist only in an owner-readable private data directory outside the repository:
wake request, barge-in request, follow-up, negative/no-wake control, stop, and
sleep. Do not commit, upload, hash into public documentation, or package these
voice-biometric fixtures. Long raw captures were deleted after Silero trimming;
the retained files are mode `0600` under a mode `0700` parent.

`--replay-wav` replays private 16 kHz mono fixtures through the same detector and
assistant, rather than a mock policy. Frames are paced at wall-clock speed. For
multiple inputs, later clips wait for the real TTS `speaking` event and then
begin 350 ms later, which provides a deterministic barge-in.

Generic command shape (paths intentionally omitted):

```bash
/home/neko/.local/share/neko/venvs/asr/bin/python \
  scripts/neko_voice_assistant.py \
  --replay-wav "$PRIVATE_WAKE_WAV" \
  --replay-wav "$PRIVATE_INTERRUPT_WAV"
```

Validated results:

- Negative control: transcript completed, no keyword event, no session, no
  Gemma request, no playback, clean exit.
- Real owner wake clip: keyword event fired despite `Echo, necko` ASR, session
  opened, buffered audio reached Gemma, appropriate silly-cat reply returned.
- Full barge-in: first reply began, the timed owner interruption triggered VAD,
  playback returned `cancelled`, the interruption transcribed correctly, Gemma
  generated a cat-fact replacement, and replacement playback completed.
- Sleep: first reply began, recorded `bye bye` cancelled it; even with an empty
  ASR transcript, keyword-only `sleep` reached policy, emitted
  `audio_cancelled/sleep-word`, made no second Gemma request, and exited.
- A deterministic timer cancellation set at 1.5 seconds returned `cancelled` at
  1.755 seconds wall time. This is not yet a microphone-onset-to-audible-silence
  measurement.

## Latency observed

- ASR + VAD + keyword models loaded together in 5.09-5.35 seconds.
- Owner fixture ASR was about 0.79-1.59 seconds for roughly 2.1-4.0 seconds of
  VAD-selected audio.
- Buffered-audio Gemma replies were 11.73-12.38 seconds in repeated owner-fixture
  runs after warm service state.
- A separate synthetic 2.942-second inline-audio request took 16.057 seconds.
- Earlier text-only live requests took 10.29-11.82 seconds.
- Resident Micro/Kiki normally produces its first sentence frame in about 1.1
  seconds. End-to-end spoken response is therefore currently well above the
  desired “few seconds”; the correctness work does not hide that result.

## Context-window experiment

The normal Gemma unit remains capped at 2,048 total tokens. The engine budget
includes prompt/history and output; the client requests at most 96 output tokens.
Gemma 4 E2B's architectural context is 128K, but that does not make the cache fit
this 8 GB Jetson.

An isolated LiteRT `--max-num-tokens 65536` profile started in 1.278 seconds.
LiteRT warned that 65,536 exceeded its internal target/magic number of 32,003 and
substituted 32,000. On the first tiny request, the process reached about
5,617,280 KiB anonymous RSS and was killed by its isolated 5.5 GiB memory cgroup.
The normal 2K service was restored automatically and remained healthy. This is
not a 64K success; even the runtime's 32K substitute leaves no safe room for the
audio stack. A truthful 64K experiment must use the GGUF/llama.cpp alternate
with quantized KV cache and will likely require sequential worker residency.

## Remaining gates

1. Run false-wake and missed-wake evaluation over multiple speakers, distances,
   azimuths, cabin noise, playback leakage, and both approved languages before
   freezing keyword score/threshold.
2. Measure speech-onset-to-audible-silence with the production reSpeaker AEC
   reference path. Bluetooth headphones currently provide acoustic isolation.
3. Decide normal routing after latency comparison: buffered Gemma audio as the
   robust source-of-truth path, or faster keyword-gated Nemotron text with audio
   fallback when ASR confidence/semantics are poor.
4. Measure simultaneous resident RAM, input power, temperature, device unplug,
   worker crash, network loss, and a two-hour soak.
5. Only after those gates, add/enable the headless user-session assistant unit,
   arrange PipeWire startup/linger, and perform a real cold-boot test. Gemma and
   TTS remain the only enabled assistant dependencies today.

## Manual bench and rollback

Live attended bench:

```bash
/home/neko/.local/share/neko/venvs/asr/bin/python \
  scripts/neko_voice_assistant.py --verbose-transcripts --max-dialogues 2
```

Omit `--verbose-transcripts` outside an attended diagnostic so recognized text
and replies are not printed/journaled. Ctrl-C stops capture and cancellation.

Rollback is independent of Gemma/TTS: stop any live assistant process, revert
the voice loop, behavior aliases/sleep words, Gemma audio/history client, TTS
cancellation, keyword config and tests; then remove the external VAD/KWS model
directories if no other sherpa work uses them. Delete private fixtures only on
explicit owner request.
