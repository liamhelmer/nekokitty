# KittenTTS Kiki and cat-audio toolbox — 2026-07-16

## Decision

Keep KittenTTS 0.8.1 with the 80M `kitten-tts-mini-0.8` Kiki voice at 1.2x
speed as an installed, on-demand English voice candidate. It is small and fully
local, but its first Jetson CPU measurement was slower than real time. Do not
replace multilingual Supertonic or enable a KittenTTS service until warm,
sentence-chunk, coexistence, and subjective listening comparisons pass.

For cat vocalizations, ship a curated and attributed local sound palette first.
Real recordings provide predictable latency, mood, loudness, and child-safety.
Keep generative cat audio as a sequential laboratory profile rather than a
resident runtime.

## KittenTTS evidence

Primary sources checked on 2026-07-16:

- <https://github.com/KittenML/KittenTTS>
- <https://huggingface.co/KittenML/kitten-tts-mini-0.8>

Upstream calls KittenTTS a developer preview and offers 15M, 40M, and 80M ONNX
models. It documents eight voices, native speed control, 24 kHz output, CPU-only
operation, and Apache-2.0 code/model terms. `Kiki` maps to
`expr-voice-5-f` in the pinned Mini configuration.

The exact 0.8.1 wheel declares a much larger stack than its local ONNX inference
path uses. Its `onnx_model.py` imports Misaki but never references it; Misaki's
English extra pulls spaCy, spaCy Curated Transformers, and Torch. Package import
also eagerly imports the Hugging Face downloader, while its download helper does
not accept a revision. Neko therefore uses an exact local model directory and a
two-file reproducible patch that removes the unused Misaki import and exposes
only the local ONNX class at package import. This is a local integration patch,
not an upstream performance claim.

Pinned artifacts and installation details are in `docs/operations/setup-log.md`.
The repository contains:

- `deploy/requirements/kittentts.in` — audited 32-package inference closure;
- `deploy/requirements/kittentts.lock` — aarch64/Python 3.12 hashes;
- `deploy/patches/kittentts-0.8.1-minimal-offline.patch` — exact wheel patch;
- `scripts/neko_kittentts_speak.py` — offline, hash-checking sample generator.

The first Kiki 1.2x audition used:

```text
text              Hello, little kitten! I'm Neko. Shall we curl up together
                  and hear a cat story?
load              1.629 s
generation        8.238 s
audio duration    6.150 s
real-time factor  1.339
peak process RSS  278.9 MiB
output            24 kHz, mono, signed 16-bit PCM
playback          PipeWire Ora GQ Headphone sink; successful
retention         transient WAV deleted immediately
```

A second short process measured 1.577 s load, 3.787 s generation for 2.792 s
audio, 1.356 real-time factor, and 276.3 MiB peak RSS. These are cold-process,
single-utterance CPU observations, not a warm streaming benchmark. ONNX Runtime
logged harmless failed DRM-device discovery while continuing on CPU. A clean
temporary environment installed all 32 hash-locked packages with `--no-deps`,
accepted the recorded patch, and imported the local class successfully.

## Curated cat-sound sources

### Pinned candidate: CatMeows

Primary record: <https://doi.org/10.5281/zenodo.4008297>.

Version 1.0.2 contains 440 PCM meows from 21 cats. Zenodo labels the record CC BY
4.0; the authors' additional terms describe scientific research and
non-commercial use and require acknowledgement. Neko is personal/non-commercial,
but the archive remains external and will not be redistributed in this MIT
repository. The files are labeled by context:

| Context | Count | Initial playback policy |
| --- | ---: | --- |
| Brushing (`B`) | 127 | Candidate after listening review |
| Waiting for food (`F`) | 92 | Candidate after listening review |
| Isolation (`I`) | 221 | Exclude by default; possible distress |

All 440 files are mono, 16-bit, 8 kHz WAV. Durations are 1.085–4.002 s, mean
1.831 s, 805.684 s total. The archive and extraction are pinned outside Git at:

```text
/home/neko/models/cat-sounds/catmeows/4008297/dataset.zip
MD5     b5fa911bcd6514e39dfef6876f747df4 (matches Zenodo)
SHA-256 214000280e6ef33b10e39ef063ccc1f2f83d789ab57f2a5d111da63b06f659ae
/home/neko/models/cat-sounds/catmeows/4008297/dataset
```

Extraction followed a path-traversal check. No clip has been selected, edited,
played, or added to Neko's runtime. The next step is a human listening pass over
the brushing and food groups, recording friendly/neutral/reject labels and
selecting several different cats rather than overusing one animal.

### Supplemental sources

- Wikimedia Commons has dedicated meowing and purring categories. Every file's
  description page has its own license and attribution, so category membership
  alone is not clearance.
- Freesound offers CC0, CC BY, and CC BY-NC assets. Prefer CC0, otherwise retain
  title, author, source URL, license URL, retrieval date, and source checksum in
  a manifest. As of July 2026, Freesound also exposes uploader generative-AI
  preferences; those must be respected separately if a clip becomes training
  data. Playback/remixing and model training are distinct clearance decisions.

### Owner-curated Freesound library

On 2026-07-16 the owner supplied `/home/neko/curated-cat-sounds`, a 127 MiB
collection of 24 Freesound downloads whose filenames retain the Freesound sound
ID, uploader, and title. After owner review, 20 `keep_*` originals are copied
unchanged into Git under `assets/cat-sounds/originals`; the two maybes and two
non-standalone sources remain external. The repository source manifest at
`config/cat-sounds/curated-freesound.json` records each
expected filename, SHA-256, source page, creator, title, exact Creative Commons
license URL, source duration/sample rate, provisional semantic tags, and review
state.

Each of the 24 original Freesound pages resolved on 2026-07-16 and matched the
ID/uploader/title encoded in the local filename. No license or URL sidecar was
present in the supplied directory, so page verification was necessary. The
license inventory is:

| License | Files | Revision-one handling |
| --- | ---: | --- |
| CC0 1.0 | 15 | Preferred subset; retain provenance anyway |
| CC BY 4.0 | 3 | Attribute creator/title/source/license |
| CC BY-NC 3.0 | 2 | Personal/noncommercial profile only; attribute |
| CC BY-NC 4.0 | 4 | Personal/noncommercial profile only; attribute |

The whole library is 812.226 seconds (13:32) of source audio. Filename and
publisher-description triage gives 10 meow-led, 11 purr-led, two mixed
meow/purr, and one processed novelty/alarm recording. This is deliberately
provisional: no audio was played during the inventory. In particular, the
kitten-attention recording and the multi-cat veterinary recording carry an
explicit `distress-review-required` tag, and the rhythmic alarm is manual-only.
No entry is yet enabled for unattended runtime playback.

The listening pass should record, per source or selected time range: emotional
valence, friendly/neutral/reject, vocalization type, usable start/end times,
background speech/noise, abrupt edits, suitability for speaker and/or body
transducer, and a conservative gain. Approved excerpts—not the originals—then
become normalized, lossless delivery assets. Preserve originals and checksums.
The manifest is a playback/remix ledger only and grants no permission to use a
recording for model training; Freesound uploader AI preferences remain a
separate gate.

#### Guided-review loudness policy

The first fixed-25%-volume preview was nearly inaudible, and the sub-second item
1 could finish before the Bluetooth sink woke. All 24 originals were therefore
measured with GStreamer 1.24.2 `rganalysis` using forced per-track ReplayGain at
the conventional 89 dB reference. Results are pinned in
`config/cat-sounds/curated-freesound-normalization.json`; originals remain
bit-identical to their source-manifest hashes.

The review player applies a 0.35 common digital master and the measured track
gain, reducing only gains that would exceed -1 dBFS sample peak. It keeps one
PipeWire stream open with two seconds of silence before each file, then plays
exactly one complete source and exits. This is non-destructive review leveling,
not final acoustic mastering: ReplayGain is not calibrated cart SPL, sample peak
is not oversampled true peak, and speaker/transducer masters need separate field
calibration. Use `scripts/neko_cat_sound_review.py list` and
`scripts/neko_cat_sound_review.py play <index-or-id>`.

Item 1 measured +12.28 dB and played with multiplier 1.439, about 5.8 times the
failed preview amplitude. The owner retained it as a candidate: plaintive,
interrogatory, insistent, slightly fuzzy, but good; likely actions are question
or attention request. Structured results are in
`config/cat-sounds/curated-freesound-listening-review.json`. It remains disabled
until the complete palette review and mastering pass.

#### Completed owner classifications

The one-source-at-a-time pass completed on 2026-07-16. Twenty-three recordings
played in full. The owner stopped item 22 after hearing enough of its long,
breathy, distance-variable purr to reject it for standalone use; it remains only
possible excerpt source material. The outcome was 19 primary/keep candidates,
two secondary maybes (items 2 and 12), one manual-only novelty remix (item 8),
and two sources not selected for standalone runtime (20 and 22). Owner language,
scores, emotional classifications, output roles, and editing constraints are
preserved verbatim and structurally in the review JSON.

Highest-priority meow material:

| Item | Score | Intended role | Required work |
| ---: | ---: | --- | --- |
| 10 | 10/10 | Clean neutral/general-purpose meow | Master only |
| 14 | 9/10 | Affectionate “thank you” meow/purr | Master only |
| 21 | 9/10 | Clean neutral-to-insistent attention meows | Split and intensity-label |
| 15 | 9/10 | Friendly two-cat conversation/storytelling | Preserve multi-cat identity |
| 9 | 9/10 | Kitten/older-cat begging or food anticipation | Select a short excerpt |
| 3 | 7/10 | Loving, happy meow/purr combination | Reduce minor noise if useful |

Highest-priority purr material:

| Item | Score | Intended role | Required work |
| ---: | ---: | --- | --- |
| 17 | 10/10 | Primary clean purr; best transducer source | Remove final 0.5 s; build loop/fades |
| 24 | 10/10 | Snuffly, playful, curious affectionate purr | Master speaker/transducer versions |
| 23 | 9/10 | Very relaxing short/bass-forward purr | Master transducer version |
| 18 | 9/10 | Short interjected purr | Master quick-action version |
| 5 | 8/10 | Warm, cuddly, sleep-friendly long purr | Select scratch-free loop |
| 16 | 8/10 | Hypnotic low-level sleep purr | Prefer clean later range; remove tail |
| 11 | 8/10 | Strong short purr | Inspect apparent source clipping |

Other useful characters include item 1's plaintive question/attention meow,
item 4's friendly-but-pushy interaction request, item 6's curious meow with a
cut-off tail, item 7's excited treat anticipation, and item 13's patient neutral
question. Item 8 is never autonomous: it is an unnatural trippy cat alarm/remix
for explicit novelty or music play only. Items 20 and 22 are superseded by
cleaner purrs. The owner did not hear distress in items 9 or 21; both were
reclassified as food/attention material, with bounded duration and cooldowns.

The listening decision does not enable playback. On 2026-07-16 the non-hardware
portion of the next gate produced 25 reproducible, lossless P0 bench candidates
from items 10, 14, 17, 18, 21, 23, and 24. Originals remain hash-identical.
Exact cuts, ordered DSP, FFmpeg build/hash, loudness/true-peak measurements,
attribution, output paths, known peak-limited exceptions, and rollback are in
`docs/cat-sounds/DERIVED_AUDIO_BENCH.md` and the machine manifest under
`assets/cat-sounds/derived`.

The common build target is -23 LUFS-I within 0.5 LU and no more than -2 dBTP,
using only linear gain capped by peak. All 25 are within the peak ceiling and
have zero clipped samples; 23 reach the loudness target. Item 24's two speaker
copies remain at -27.13/-28.76 LUFS-I because the friendly snuffle transients
reach -2 dBTP. Compression/limiting was rejected at this stage to preserve the
owner-approved natural dynamics. The transducer copies reach target.

The outputs are not approved runtime media. Item 21's nine splits require owner
intensity/multi-cat classification, item 17's loop/phase sequence requires
continuous listening, all derived clips need a post-master audition, and all
speaker/transducer copies need the final physical hardware test. The semantic
allowlist is therefore present but entirely disabled and fail-closed.

The maintained human catalog is `docs/cat-sounds/CAT_SOUNDS_MASTER.md`; the
separate worklist is `docs/cat-sounds/PROCESSING_AND_REMIX_QUEUE.md`. Distributed
paths/checksums/licences are pinned independently in
`assets/cat-sounds/manifest.json`. Inclusion does not place the audio under MIT,
does not enable runtime playback, and does not grant model-training clearance.

The first palette should contain approximately 12–20 approved assets spanning:

- greeting trill/chirp;
- short friendly meows with several intensities;
- question/attention meow;
- contented purr start, steady loop, and stop tail;
- playful chatter;
- a quiet acknowledgement suitable under speech.

Normalize approved playback assets offline to a documented loudness/true-peak target,
trim noise manually, preserve a lossless master, and create device-rate delivery
copies. Do not use hisses, growls, caterwauls, or isolation calls for routine
child interactions. The behavior supervisor chooses a tagged asset and bounded
pitch/gain variation; an LLM never emits an arbitrary filename or amplitude.

## Generative cat-audio research

Older AudioLDM can perform text-to-audio and audio-to-audio generation, but its
official repository specifies an 8 GB discrete GPU and at least 16 GB system RAM.
That is not a sensible concurrent Orin Nano 8 GB profile.

The important current candidate is Stability AI's May 2026
`stable-audio-3-small-sfx` release:

- 433M diffusion model with the SAME-S edge/CPU autoencoder;
- text-to-sound-effects, audio-to-audio, inpainting, and continuation;
- publisher CPU support, 44.1 kHz stereo, up to 120 seconds;
- publisher Mac CPU numbers, but no Jetson benchmark;
- gated weights under the Stability AI Community License plus redistributed
  T5Gemma components under the Gemma terms.

The owner accepted the gated terms and supplied a local Hugging Face token on
2026-07-16. The token was read only into process memory; its value was never
printed, copied into the repository, or recorded. The generic PyTorch path was
not used. The same official source now contains a portable ARM TFLite/LiteRT
backend using XNNPACK, with no PyTorch or Transformers runtime. That path was
pinned and tested as described below.

### Executed Stable Audio 3 Small SFX evaluation

Exact source and runtime:

```text
source        /home/neko/models/stable-audio-3
Git commit    0385302ea26522f00c80392c4b708df5ebf1adf5
backend       optimized/tflite; CPU XNNPACK; six threads
environment   /home/neko/.local/share/neko/venvs/stable-audio-3-tflite
runtime       Python 3.12.3; ai-edge-litert 2.1.6; 24 locked packages
environment   125 MiB
weights repo  stabilityai/stable-audio-3-optimized
revision      08c64b96b1e59942aade69759f60fb88c58c90c4
weights path  /home/neko/models/stable-audio-3-optimized/<revision>
```

The first profile paired the fastest dynamic-int8 SFX DiT with the reference
FP32 SAME-S decoder and FP16 T5Gemma encoder. The three verified files total
about 1.25 GB:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `dit_w8a8-dyn.tflite` | 467,069,712 | `9bae6401e925e9dc0f721955f2d92549e07d7c54e43070b779d2f35750ec42b2` |
| `dec_fp32.tflite` | 218,377,156 | `cd87fa6686b24a56dc3497e05fbb26a34cf9604afe49c6631e829c9e70fccf21` |
| `encoder_fp16.tflite` | 563,818,608 | `8530d0b3e6b9b9dcf1239145c2a853fb749708eaddbb472ff8f0802b50059372` |

With Gemma stopped, 20-second/eight-step/CFG-off samples measured:

| Sample | Seed | Model wall | Real time | Peak RSS | Peak input | Peak temp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Friendly meow | 12016 | 15.04 s | 1.33x | 2,106.8 MiB | 9.409 W | 49.75 C |
| Soft purr | 22016 | 14.37 s | 1.39x | 2,107.0 MiB | 9.409 W | 50.38 C |

The owner rejected this first pair for unattended use: the first meows sounded
very distressed, the latter half was mostly good, and the full pair sounded
choppy. This is decisive child-facing quality evidence. The exact raw WAV hashes
were `5297570f785c6236ed264e2758071a7e8e95385c3e5e544bd137865753450bc3`
and `08762cac226fe5f2dd15507335a888697c44e2038f298dcdc42543e4065933aa`;
both raw and peak-normalized audition copies were deleted.

The higher-quality weight-only-int8 DiT was then pinned:

```text
tflite/sa3-sm-sfx/dit_w8a32.tflite
467,132,768 bytes
SHA-256 7a6c8c48233b31b0f5482236d2681aa3690ba7ea71c87ec1870c9ceaab653de7
```

It is not viable on this 8 GB host. Both batched and sequential CFG 2.0 runs
were killed before sampling at observed process peaks of 6,501.7 and 6,466.1
MiB respectively. Neither produced audio. Keep the verified file only as
research evidence; do not retry it without a larger-memory host or a proven
lower-memory runtime.

The dynamic-int8 path was finally retested with CFG 2.0, sequential guidance,
explicitly relaxed/contented positive prompts, and negative prompts excluding
distress, yowling, rhythmic pulsing, and abrupt cuts. The guided meow generated
20 seconds in 21.75 seconds at 2,108.2 MiB peak RSS; its raw waveform exceeded
full scale (`1.085`) and the official writer clipped it. The guided purr took
21.29 seconds at 2,108.5 MiB peak RSS and remained below full scale. Their raw
SHA-256 values were
`b9da5dfd756d79e45100a6bfb3cc7648b23aca882fa239677ee7437b384e01a9`
and `b9588a196d3345c5af7bdbafdd6b2778ceaacba9d0a962dc830e0cfd56d42978`.
Attenuated copies were played through Ora, and every WAV was then deleted. The
owner found the quality not much better and decided pre-generated library sounds
are required. Stable Audio text-to-audio is therefore rejected for revision-one
Neko playback; do not spend more time tuning prompts, seeds, guidance, or
precision on this host.

The measured operational conclusion is strong but narrow: this optimized model
is fast enough and small enough for offline research, but its accepted-output
quality is too low for Neko. It is neither resident nor part of the assistant
pipeline. Raw generated output is forbidden from autonomous child-facing
playback. The controlling revision-one path is now pre-recorded, human-reviewed
library audio. Audio-to-audio variation may be reconsidered only as a future
research experiment; it additionally requires the SAME-S encoder artifact.

## Acceptance gates

1. Owner confirms the Kiki audition subjectively and compares it against at
   least one Supertonic voice on the production speaker.
2. Measure KittenTTS warm repeated generation, first playable chunk, and combined
   Gemma/ASR/perception memory and power.
3. Human-curate and attribute at least 12 lossless cat assets; reject distress,
   excessive noise, clipping, and ambiguous rights.
4. Implement a manifest-driven soundboard with mood/action tags, gain ceilings,
   cooldowns, interruption, and deterministic fallbacks.
5. Stable Audio raw generation is closed for revision one after two failed
   subjective auditions. Use only human-reviewed pre-recorded assets plus
   bounded, reversible DSP variants; revisit generation only in a future phase.

## Rollback

Removing KittenTTS does not affect Supertonic or any service:

```bash
rm -rf /home/neko/.local/share/neko/venvs/kittentts
rm -rf /home/neko/models/kittentts
```

Remove the CatMeows candidate archive with:

```bash
rm -rf /home/neko/models/cat-sounds/catmeows/4008297
rm -rf /home/neko/.local/share/neko/venvs/stable-audio-3-tflite
rm -rf /home/neko/models/stable-audio-3
rm -rf /home/neko/models/stable-audio-3-optimized
```

Then revert the KittenTTS and Stable Audio input/lock files, patch, helper,
notices, and documentation. No boot-enabled unit or system package was created.
