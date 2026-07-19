# Pre-recorded Mini/Kiki story audio

Date: 2026-07-19 (America/Vancouver)

## Status

Implemented for all five approved local stories. Narration is committed as
lossless FLAC/PCM16 and selected by a hash-verified local manifest. The attended
assistant must be restarted before its already-imported `StoryLibrary` can use
the new playback code; after restart, atomic manifest updates from background
repairs are hot-reloaded. No model, package, systemd unit, or boot target changed.

## Why and rendering profile

The resident Micro/Kiki worker is optimized for conversational latency and feeds
KittenTTS 120-character chunks. That makes sense for a live answer but gives the
model little context for story cadence, dialogue, punctuation, and paragraph
shape. Stories have no reason to pay that quality/latency tradeoff repeatedly.

`scripts/build_story_recordings.py` loads the already pinned KittenTTS 0.8.1
**Mini** model, the largest installed KittenTTS profile, once and renders the
approved shelf offline:

- model revision: `c02725660cea441db4c383af69f1f26f5cd00947`;
- Mini ONNX SHA-256:
  `0f5bbae4fc4800c98dbc544a87ecfa79510de2fb8222db30d12e5bfe9177df91`;
- voices SHA-256:
  `40ad2638952b77b7b2f30127e2608e169fc69dd256b53bd8aaa3409a33193c42`;
- config SHA-256:
  `6b160bc9b19e24ecb21e84bc14f8a7da21fdf47ec72d42450bc5cf514b61804a`;
- voice/speed: Kiki at 1.2x;
- inference: CPU ONNX Runtime, four threads for the initial attended build;
- synthesis section: whole adjacent Markdown paragraphs grouped to at most 380
  characters, inside KittenTTS upstream's 400-character long-text boundary;
- output: mono 24 kHz FLAC with lossless PCM16 samples.

The build command was:

```bash
/home/neko/.local/share/neko/venvs/kittentts/bin/python \
  scripts/build_story_recordings.py
```

The initial build loaded Mini in 1.673 seconds, rendered in 1,062.35 seconds,
and reported 905.6 MiB peak process RSS. It produced 53 sections, 828.958
seconds of narration, and 19,750,176 bytes under
`content/stories/recordings/mini-kiki-v1`. All files decoded as finite mono
24 kHz audio. Section peaks ranged 0.46280–0.81659 and RMS ranged
0.07189–0.08387, with no clipping.

| Story | Sections | Narration | Fixed cues after sections | Ending purr |
| --- | ---: | ---: | --- | --- |
| Elsa’s Wacky Wand Concert | 11 | 177.687 s | 1 general, 5 general | yes |
| Heidi and the Ravens’ Muddy Masterpiece | 12 | 177.854 s | 6 general, 10 friendly | yes |
| Luna’s Very Important Stick Garden | 10 | 151.945 s | 3 friendly, 7 general, 9 general | no |
| Magic Girl and the Gummy-Worm Moon | 11 | 165.812 s | 2 general, 5 general, 8 general | yes |
| Neko and the Great Gummy-Worm Parade | 9 | 155.678 s | 3 general, 5 general, 7 general | yes |

## Fixed cat punctuation and playback

The build uses seed `neko-story-audio-mini-kiki-v1` and a 0.35 selection rate to
choose occasional non-adjacent meow positions at section boundaries. Every
section boundary is also an original paragraph boundary. The chosen action—not
an arbitrary file path—is stored in the manifest, so the existing cat-audio
allowlist still owns asset approval, gain, output, and cooldown. The seed makes
the one-time random layout reproducible; playback itself does not move cues.

Ending purrs are explicit editorial booleans, not runtime chance. Four warm
endings purr; Luna's brisk fetch ending does not. Purr audio stays separate from
narration so the speaker/body-transducer policy can evolve without regenerating
speech. A child can still interrupt narration with the addressed wake policy:
PipeWire terminates the current pre-rendered section immediately. Conversation
history still receives only the curated story summary and essentials.

At selection time, `StoryLibrary` verifies the source-story hash, spoken-text
hash, section order, contained `.flac` paths, every audio SHA-256, duration, cue
vocabulary, and ending-purr boolean. Invalid or absent audio degrades to the
existing live-TTS story path.

## Self-healing stale recordings

If selection discovers missing, stale, or corrupt story audio, the voice
supervisor atomically queues only that story under
`/var/tmp/neko-story-recording-rebuild`, logs a media-free event, and immediately
uses live TTS. It launches `scripts/neko_story_recording_worker.py` through:

```text
/usr/bin/nice -n 19 /usr/bin/ionice -c 3 \
  /home/neko/.local/share/neko/venvs/kittentts/bin/python \
  scripts/neko_story_recording_worker.py
```

The queue deduplicates by story ID and is mode 0700; requests are mode 0600. A
nonblocking file lock permits one worker. The worker drains requests serially,
uses one ONNX CPU thread, inherits lowest CPU priority and idle-class I/O, and
never uses the GPU. It calls the builder with `--story-id`, `--incremental`, and
`--threads 1`. Exact section text and audio hashes allow unchanged sections to
be reused; changed, missing, or corrupt sections alone are rendered. The
manifest is replaced atomically only after success, and the running library
hot-reloads it by modification time on the next story request. A failed request
remains queued for a later retry and the live fallback remains available.

An integration queue run reported nice value 19, `ionice` class `idle`, used one
thread, reused all ten unchanged Luna sections, preserved all five manifest
entries, and completed in about three seconds including Mini load. Hard realtime priority was deliberately
not granted to the assistant: on this shared six-core Jetson, a runaway realtime
thread could starve audio, ASR, supervision, and system recovery. Lowest-priority
CPU/I/O plus a single repair thread isolates this non-urgent CPU-only work without
that failure mode.

## Validation and rollback

The repository tests cover complete recording coverage, hash verification,
stale-source rejection, atomic manifest hot reload, queue permissions and
deduplication, expanded recorded-story playback ordering, and first-audio source
telemetry. Full-suite results are recorded in the setup log.
The completed repository suite passed all 152 tests; Python compilation and
`git diff --check` also passed.

The attended assistant was restarted from the unchanged manual command after
deployment and reported ready in 5.470 seconds with the expected LFM and Kiki
endpoints. A full human listening pass of all five Mini recordings remains the
quality acceptance step; decode, integrity, level, routing, and control behavior
are validated independently.

Rollback: remove or move
`content/stories/recordings/mini-kiki-v1/manifest.json` and restart the attended
assistant. Neko will use the prior live-TTS story path. Disable automatic repair
at the same time by reverting the queue call, otherwise a missing manifest is
intentionally rebuilt. FLAC files, the external pinned Mini model, and the queue
can then be removed independently; no systemd rollback is required.
