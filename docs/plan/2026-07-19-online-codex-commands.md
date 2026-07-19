# Online-only Codex commands

## Owner decision and scope

On 2026-07-19 the owner authorized two spoken, text-only online enhancements:

- `search the web` or `web search` runs a Codex one-shot with
  `gpt-5.6-luna`, low reasoning, live web search, a Plan-mode instruction, and
  a read-only sandbox;
- `compose story`, `compose a story`, or `compose a new story` runs a Codex
  one-shot with `gpt-5.6-terra`, low reasoning, and the explicitly requested
  full-access/YOLO switch. It may add exactly one story file and one approved
  manifest entry, then Neko queues that story for the existing low-priority
  Mini/Kiki renderer.

These are narrow additions. Ordinary conversation, the approved story shelf,
event schedule, wake/stop controls, and cat sounds remain local and continue to
work offline. Only the final ASR text after one of these explicit phrases is
sent to Codex. Raw audio and images are not sent. Online tool results stay out
of local LLM conversation history.

## Connectivity state

`neko.online_jobs.ConnectivityMonitor` runs the owner-selected command
equivalent to:

```bash
/usr/bin/ping -c 2 -W 2 8.8.8.8
```

It probes once before the voice loop reports ready, then every 120 seconds. A
successful command immediately sets online mode; any nonzero result, execution
error, or eight-second outer timeout immediately sets offline mode. There is no
success or failure grace period. Only transitions emit the media-free
`online_mode_changed` event. This intentionally tests IPv4 ICMP reachability to
Google's public resolver, not DNS, HTTPS, or Codex authentication; a network
that blocks ICMP is conservatively offline even if some web traffic works.

If either online intent arrives while offline, Neko says exactly:

> I'm sorry, I'm not on the internet right now, so I can't do that. Did you
> want to hear a story instead?

No local feature receives that refusal merely because the network is down.

## Job and audio behavior

At most one Codex job can run at a time. It runs in a daemon worker so capture,
KWS, VAD, ASR, and the assistant event loop remain responsive. The ceiling is
30 minutes, deliberately longer than the ordinary two-minute conversational
expectation. Codex is invoked with `--ephemeral`, and its final-response scratch
file is created beneath mode-0700 `/var/tmp/neko-online-jobs`, under an inherited
0077 umask, and deleted immediately after it is read. Codex account/provider
retention remains governed by that service and is not claimed to be local.
The spoken request is supplied on the child's stdin (`codex exec -`), never as
a command-line argument, so it does not appear in the local process list.

While a job is active, the approved primary loop asset repeats until completion.
This explicit supervisor state may begin inside the ordinary purr cooldown; all
model-selected and conversational sounds retain their normal cooldown policy.
Unaddressed speech is ignored. Saying `Neko` stops the purr mid-clip, speaks
`I'm working on your request to ...`, and resumes the purr if the job is still
active. Job completion stops the purr mid-clip before the one-shot's short plain
text final answer is synthesized. `Neko stop` cancels speech, the work purr, and
the Codex process group immediately; a cancelled job does not later announce a
completion.

The search prompt treats the spoken topic as untrusted data, disallows local
file access/mutation, requests current sources, and asks for two to five short
plain spoken sentences without Markdown, URLs, or citation syntax. Both Codex
prompts carry Neko's full presentation persona: cute, motherly, playful and a
little mischievous; an orange-and-black striped cat-car with fuzzy hands, a long
tail, and a magical gummy-worm rear drawer; informal contractions, short words,
warmth, and silliness. This explicitly cannot override evidence or uncertainty.
Final responses may contain at most one approved real-sound marker, while story
files never contain markers because the renderer owns paragraph sounds. Codex CLI
0.144.4 does not expose the interactive collaboration-mode selector through
`codex exec`; the one-shot therefore receives an explicit Plan-mode instruction
and is independently constrained by `-s read-only`. Live web search must be a
top-level CLI option (`codex --search exec ...`) in this version.

The story prompt similarly treats the theme as untrusted data and limits edits
to `content/stories/originals` plus `content/stories/library.json`. It requires
one unique `original.*` entry, 500–650 words to preserve the five-minute bound,
ages 5–7, non-scary informal language, paragraphs no longer than 350 characters,
summary/tags/essentials, Neko's warm mischievous narration voice, JSON validation,
and no render/commit/push. After a
successful one-entry delta, `enqueue_story_rebuild()` launches the existing
nice-19, idle-I/O, one-thread incremental renderer. New stories default to a
warm ending purr. The runtime reloads the source library immediately and the
recording manifest hot-reloads when rendering publishes it atomically.

## Exact runtime commands and validation

The pinned executable used by the assistant is:

```text
/home/neko/.nvm/versions/node/v24.18.0/bin/codex
```

Its observed version is `codex-cli 0.144.4`. No package, model, service, token,
or credential was installed or modified for this change. Existing mode-0600
`~/.codex/auth.json` is used by child processes and is never copied into the
repository or logs.

The two-packet live probe passed with two replies on 2026-07-19. A real Luna/low
web one-shot passed after correcting the CLI option placement and returned a
short current-source answer. The first smoke deliberately caught and removed
two unsupported placements (`-a` under `exec`, and `--search` after `exec`);
both failed before model execution and changed no files. A Terra/low
full-access one-shot in an isolated `/var/tmp/neko-terra-smoke` directory
reported `approval: never`, `sandbox: danger-full-access`, and returned the
exact requested readiness sentence without editing files. The repository tests
cover parsing, local-story noncapture, immediate transitions, transition event
deduplication, Luna/Plan/read-only/search argv, Terra/YOLO argv, concurrency,
and the exact offline speech.

The attended voice loop was restarted with this code and reported the immediate
online transition followed by ready in 5.365 seconds of ASR/model load. The
final restart after moving prompts from argv to stdin and closing the
cancellation race reported ready in 5.330 seconds and remained online. It is
still a manual test process rather than a boot unit. Production acceptance still
needs an end-to-end spoken search, spoken status
check, completion announcement, stop/cancellation test, offline probe failure,
and a real composed-story render/listening test.

A real Luna/low web smoke after the persona change answered why cats knead soft
blankets with contractions, cozy kitten/nest language, a playful claim-the-
fluffy-spot joke, an appropriate veterinary caveat, and one `[purr:tail]` cue.
This was materially less dry while preserving the factual/safety boundary. No
story was generated during this prompt-only smoke.
The attended assistant was then restarted; the persona-aware process reported
online immediately and ready after 5.246 seconds.

## Rollback

Stop the attended assistant, revert `neko/online_jobs.py` and its integration in
`scripts/neko_voice_assistant.py`, then restart the prior command. Remove
`/var/tmp/neko-online-jobs` only after verifying no Codex child is active.
Reverting the default ending-purr fallback in `scripts/build_story_recordings.py`
is safe only if no dynamically composed story remains approved. No systemd unit,
model, virtual environment, or credential needs removal.
