# Low-latency local voice path

Date: 2026-07-16 (America/Vancouver)

## Outcome

The attended owner-fixture path now reaches the first PCM write an estimated
**1.309 seconds after the end of speech**. This is the first measured Neko path
below the owner's two-second target. The estimate is composed from Silero's
configured 600 ms trailing-silence endpoint and monotonic timestamps at VAD
finalization and the first PCM write. It does not include an independently
measured speaker acoustic onset, so it is a software acceptance result, not yet
the final production-output result.

The latency route is:

```text
16 kHz capture
  -> Silero VAD + open-vocabulary keyword spotter
  -> Nemotron streaming decode while the child is still speaking
  -> LFM2.5-1.2B Q5_K_M on CUDA llama.cpp, 16K context
  -> stop at the first complete, directly useful short sentence
  -> resident Piper Lessac medium
  -> PipeWire playback with barge-in cancellation
```

Gemma 4 E2B, LiteRT, KittenTTS Micro/Kiki, Supertonic, and the audio-input route
remain installed as comparison/fallback profiles. Nothing was deleted.

## Why the previous route missed

The original attended loop waited sequentially for:

1. 600 ms Silero end silence;
2. a second, whole-utterance Nemotron decode after VAD finalization;
3. Gemma's audio frontend and the entire 96-token response;
4. a complete KittenTTS sentence waveform.

Repeated owner-fixture requests took 11.73–12.38 seconds inside buffered-audio
Gemma alone. Enabling LiteRT's existing SSE path did not fix the model/backend
delay: a realistic warm text request emitted its first content at 9.398 and
10.883 seconds, and its first complete sentence at 9.559 and 11.067 seconds.
Streaming was necessary, but the CPU LiteRT backend was still far too slow.

The new path removes redundant audio understanding from the normal route, feeds
Nemotron continuously during capture, and sends the already-available text to a
CUDA model server. `--llm-route audio` remains an explicit diagnostic route.

## Current model research and decision

Research was refreshed from primary sources on 2026-07-16. The first benchmark
order was:

1. [LiquidAI LFM2.5-1.2B-Instruct](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct)
   because its official card gives 1.17B parameters, a 32,768-token supported
   context, English/French/Spanish among eight languages, official GGUF and
   llama.cpp support, and edge-oriented architecture;
2. Gemma 3 1B QAT as a Google/LiteRT control;
3. Qwen3.5 0.8B after its current Arm64 tokenizer issue is resolved;
4. Granite 4.0 350M only as a deterministic degraded fallback.

LFM won the first local gate, so no additional language model was downloaded.
Its LFM Open 1.0 terms are not MIT/Apache; the owner's personal noncommercial
use is within the recorded project scope. Model weights remain outside Git.

### Pinned LFM artifact

| Field | Value |
| --- | --- |
| Upstream | `LiquidAI/LFM2.5-1.2B-Instruct-GGUF` |
| Revision | `047e06635fbe71469926b35ea414537245218200` |
| File | `LFM2.5-1.2B-Instruct-Q5_K_M.gguf` |
| Bytes | 843,354,944 |
| SHA-256 | `fa03f3ac4da941a53a0cd4450aacf6a80804c6a1ff885d2fdcbe9406c03215c4` |
| Local root | `/home/neko/models/LFM2.5-1.2B-Instruct-GGUF/047e06635fbe71469926b35ea414537245218200` |

The exact download used the already-authorized local Hugging Face token without
printing or copying it into the repository.

## Language-model measurements

All local numbers are from this Jetson Orin Nano in its existing 15 W mode. The
benchmark wrapper warned that MAXN would be preferable for cross-run comparison;
15 W is nevertheless the intended current operating mode and therefore useful
for product latency.

### Gemma 4 GGUF comparison

The already-pinned official Gemma 4 E2B QAT Q4_0 GGUF was tested first through
the digest-pinned NVIDIA llama.cpp container. The structured wrapper result at
128 prompt/32 generation tokens and 99 GPU layers was:

| Metric | Result |
| --- | ---: |
| prompt/TTFT proxy | 219.45 ms |
| token interval / TPOT | 53.39 ms |
| generation | 18.73 tok/s |

A real 16,384-token server with Q4_0 K/V cache loaded successfully. Warm Neko
requests reached first text in 0.139–0.443 seconds and first sentence in
0.533–0.860 seconds. The 16K K/V allocations were only about 30 MiB because of
Gemma 4's architecture and quantized cache.

It still failed combined residency. With Gemma 4 llama.cpp, Nemotron ASR,
keyword/VAD, and KittenTTS loaded, only about 199,464 KiB remained available.
That is not enough operating margin on a no-swap 8 GB Jetson.

### Selected LFM result

The required NVIDIA benchmark wrapper produced this structured result at the
same 128/32/99-layer/4-thread setting:

| Metric | Result |
| --- | ---: |
| prompt/TTFT proxy | 105.58 ms |
| token interval / TPOT | 29.82 ms |
| generation | 33.54 tok/s |

The 16K server uses:

- all 17 layers offloaded;
- Q4_0 K and V caches;
- one 16K slot;
- Flash Attention;
- four CPU threads;
- 256 MiB bounded in-memory prompt cache;
- no mmap;
- a local digest-pinned NVIDIA llama.cpp image.

The server reported about 54 MiB K/V cache, 0.16 MiB recurrent state, 136 MiB
CUDA compute buffer, 40 MiB host compute buffer, 802 MiB CUDA model buffer, and
105 MiB CPU model buffer. Its Docker cgroup used about 1,004–1,018 MiB after
warmup. With full ASR/KWS/VAD and both TTS workers present, a live snapshot still
showed about 2,967,384 KiB available. With only boot workers idle after deployment,
about 3,996,396 KiB was available.

Warm real prompts reached first text around 0.21–0.31 seconds before persona
tuning. The final direct-answer prompt produced useful English first sentences
around 0.33–0.54 seconds and simple French/Spanish first sentences around
0.60 seconds in the small attended sample. This is not a language-quality
acceptance suite.

## 16K context decision

The owner lowered the desired context from 64K to a hard minimum of 16K. The
deployed server is explicitly `--ctx-size 16384`; it is therefore not the old 2K
service and does not silently substitute a smaller context. This meets the
runtime requirement while leaving safe memory room for the voice stack.

Stories should still be loaded and streamed in bounded sections instead of
placing an entire library into context. The current fast conversation method
intentionally stops generation after its first complete sentence. Story mode
must use a separate sentence queue, retain the larger response, and apply the
story safety/remix checks before or per approved scene; it must not inherit the
four-word conversational first-sentence limit for all narration.

## Continuous ASR change

`ContinuousSpeechInput` now creates a Nemotron stream at speech onset, supplies
up to 512 ms of in-memory pre-roll, and decodes ready frames on the capture
thread while speech continues. The same frames continue through VAD and keyword
spotting. At VAD finalization the recognizer receives `input_finished`, decodes
only remaining work, and stores the final text and step count on the in-memory
`SpeechSegment`.

In the accepted owner-fixture replay, ASR finalization rounded below 1 ms after
the configured VAD tail instead of taking the old 0.79–1.59 seconds after VAD.
The fixture was neither named nor printed, and no microphone or replay media was
written by the assistant.

## Streaming response boundary

The OpenAI-compatible client now supports SSE. For ordinary conversation it:

1. requests at most 64 completion tokens;
2. buffers only until punctuation forms the first complete sentence;
3. closes the stream at that boundary;
4. sends only that bounded sentence to TTS;
5. stores only the spoken sentence in dialogue history.

The persona/user contract requires a concrete direct answer of at most four
words in the first sentence, with no emoji, markdown, generic praise, or
preamble. This is a latency profile, not a general story-generation profile.
The deterministic behavior controller still owns wake, sleep, stop, muting,
session state, and barge-in. Small language models are not treated as a child
safety mechanism; broader adversarial/content testing remains a production gate.

## TTS comparison and selected fast profile

KittenTTS Micro/Kiki remains the owner's preferred English voice. Direct resident
socket measurements showed:

| Text | Micro/Kiki first PCM | Nano INT8 first PCM |
| --- | ---: | ---: |
| `Hi!` | median 0.675 s | not selected |
| short greeting | median 1.163 s | not selected |
| normal seven-word question | median 1.539 s | not selected |
| `They feel safe!` | median 1.069 s | median 1.134 s |
| longer factual sentence | median 1.874 s | median 1.755 s |

The socket/header copy was negligible. KittenTTS's ONNX graph emits a whole
waveform per sentence and cannot safely stream internal PCM without redesigning
the model graph. Nano was not faster for the short response that matters.

[Pocket TTS 2.1](https://github.com/kyutai-labs/pocket-tts) is the best next
quality/latency experiment: upstream documents CPU streaming and about 200 ms
to its first chunk, plus English/French/Spanish. Its weights require a separate
Hugging Face contact-sharing acceptance. That acceptance was not assumed or
performed. Do not download the gated weights until the owner authorizes it.

The installed immediate fallback is [Piper 1.4.2](https://github.com/OHF-Voice/piper1-gpl)
with the Lessac medium US English voice. Piper code is GPL-3.0-or-later and runs
as an external local service; the voice's own model card/dataset terms remain
controlling. It is not relicensed under Neko's MIT license.

### Piper pins

| Artifact | Value |
| --- | --- |
| `piper-tts` | 1.4.2; Arm64 wheel SHA-256 `6736329f1ef58c39272215849dffdacae601201480b08a0c892938fa4d7c8c67` |
| voice repository revision | `82999b670b06c78cabeb830d535b63a31cd0ca22` |
| ONNX | 63,201,294 bytes; SHA-256 `5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f` |
| config SHA-256 | `efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0` |
| model card SHA-256 | `ce49eb457742208166d399a40cdec2c7fa9db77960930031564ab56f12882645` |
| runtime | `/home/neko/.local/share/neko/venvs/piper` |

Resident Piper produced first audio in 0.099–0.122 seconds for `They feel
safe!`, 0.149–0.166 seconds for `Purring means happy feelings.`, and
0.198–0.218 seconds for the longer tested cat sentence. The deployed worker
uses about 120 MiB after warmup. The owner heard one primed Lessac sample; final
voice acceptance is pending owner feedback. Kiki remains active at its original
socket for immediate A/B and rollback.

## Deployed services

| Service | Boot state | Endpoint | Role |
| --- | --- | --- | --- |
| `neko-llm.service` | enabled/active | `127.0.0.1:9380` | LFM 16K CUDA llama.cpp |
| `neko-tts-fast.service` | enabled/active | `/run/neko/tts-fast.sock` | Piper low-latency TTS |
| `neko-tts.service` | enabled/active | `/run/neko/tts.sock` | accepted Kiki quality profile |
| `neko-gemma.service` | disabled/inactive | `127.0.0.1:9379` when selected | old LiteRT 2K lab/fallback |

`neko-llm.service` uses the locally rebuilt loader-fixed image by immutable
digest, loopback-only host networking, read-only root, read-only model mount,
dropped capabilities, no-new-privileges, 64 PID limit, and 2.5 GB Docker memory/
swap limit. Its `ExecStartPost` health check keeps systemd activation pending
until `/health` succeeds. The container is still based on the previously noted
older NVIDIA Orin image; a host-matched native R39 build remains desirable.

`neko-tts-fast.service` is a readiness-notifying, private-network/private-device,
bounded user service. `TtsClient` now honors the worker-announced sample rate,
so Kiki's 24 kHz and Piper's 22.05 kHz services use the same cancellation-safe
protocol.

The integrated always-listening assistant itself remains attended and is not
boot-enabled. That restraint is intentional until AEC/false-wake/soak gates pass.

## End-to-end validation

The same private owner wake/request fixture used for the earlier 11.8-second
path passed without printing its transcript:

| Event | Result |
| --- | ---: |
| ASR/KWS/VAD load | 5.251 s (startup only) |
| streaming ASR finalize after VAD | <0.001 s rounded |
| first complete LFM sentence | 0.515 s |
| VAD finalize to first PCM write | 0.709 s |
| estimated speech end to first PCM write | **1.309 s** |

The generated sentence played to the connected Bluetooth headphones and
playback completed. Earlier Kiki replay on the same new LFM/streaming-ASR path
measured 1.668 seconds for a very short greeting, showing that Kiki can also meet
the target for unusually short responses.

Remaining latency gates:

- collect at least 20 warm full-pipeline turns and report P50/P95/P99;
- measure true acoustic onset with wired production output or electrical/
  microphone loopback instead of equating PCM write with audibility;
- repeat with production reSpeaker AEC/reference audio, speaker and transducer;
- test mid-sentence child pauses before reducing the 600 ms VAD tail;
- measure CPU/GPU contention with perception workers and during story streaming;
- validate English, French, and Spanish comprehension/voice quality separately;
- cold reboot and two-hour soak.

## Next audio milestone

The next authorized feature is a manifest-driven cat-sound insertion layer. It
should not ask the LLM for filesystem paths. The deterministic supervisor should
map approved semantic markers/actions to the existing disabled allowlist, then
choose a compatible mastered meow or purr with seeded randomness, no immediate
repeat, mood/session cooldowns, speaker/transducer routing, and fixed gain.
Natural sounds may acknowledge wake or replace a written `meow`/`purr`; they
must not cover required safety text. All selected assets remain subject to their
per-file licence and the pending hardware listening acceptance.

## Rollback

To return to the former Kiki + LiteRT profile:

```bash
sudo systemctl disable --now neko-llm.service neko-tts-fast.service
sudo systemctl enable --now neko-gemma.service neko-tts.service
```

Then point the attended assistant to the old endpoints explicitly:

```bash
/home/neko/.local/share/neko/venvs/asr/bin/python \
  scripts/neko_voice_assistant.py \
  --base-url http://127.0.0.1:9379 \
  --model gemma-4-e2b-it \
  --llm-route audio \
  --tts-socket /run/neko/tts.sock
```

The fast profile can be removed independently after disabling its services:

```bash
sudo rm -f /etc/systemd/system/neko-llm.service
sudo rm -f /etc/systemd/system/neko-tts-fast.service
sudo systemctl daemon-reload
rm -rf /home/neko/.local/share/neko/venvs/piper
rm -rf /home/neko/models/piper-voices
rm -rf /home/neko/models/LFM2.5-1.2B-Instruct-GGUF
```

Do not remove the old Gemma, Kiki, Supertonic, ASR, VAD/KWS, or private replay
fixtures as part of this rollback. Private fixtures still require an explicit
owner deletion instruction.
