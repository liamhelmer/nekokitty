# Setup and operations log

All dates are America/Vancouver unless marked UTC. Never add credentials or
private recordings to this file.

## 2026-07-12 — initial state

- Repository directory existed but was empty and was not a Git repository.
- Created `AGENTS.md` as the durable entry point, plus these research/operations
  notes.
- Host: Jetson Orin Nano Developer Kit, 8 GB class, Ubuntu 24.04.4/aarch64,
  L4T R39.2.0, kernel 6.8.12-1021-tegra, 15 W mode 0.
- Root NVMe had about 858 GiB available. A 500 GiB FAT volume was mounted at
  `/media/neko/disk`.
- No swap was active.
- No model server/runtime, TensorRT package, `nvcc`, `uv`, `pip`, Ollama, vLLM,
  or llama.cpp executable was initially found.
- Docker 29.1.3, containerd, NVIDIA Container Toolkit 1.19.1, and an NVIDIA
  runtime entry were installed. User `neko` was not in group `docker`; unprivileged
  Docker daemon access failed at `/var/run/docker.sock`.
- The default target was `graphical.target`; GDM/GNOME, Firefox and multiple
  desktop utilities were consuming substantial memory.
- Claude Code 2.1.207 was installed at `/home/neko/.local/bin/claude`, but
  `/home/neko/.local/bin` was absent from the non-interactive shell `PATH`.

## 2026-07-12 — skills

### Discovery workflow

Installed Vercel `find-skills` from
<https://github.com/vercel-labs/skills/tree/main/skills/find-skills>.

Initial Codex install:

```bash
python /home/neko/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/vercel-labs/skills/tree/main/skills/find-skills
```

Result: `/home/neko/.codex/skills/find-skills`.

Explicit Claude Code install:

```bash
npx -y skills add \
  https://github.com/vercel-labs/skills/tree/main/skills/find-skills \
  -g --agent claude-code -y
```

Result: `/home/neko/.claude/skills/find-skills` and the shared package location
under `/home/neko/.agents/skills/find-skills`.

### NVIDIA Jetson skills

The source <https://github.com/NVIDIA/skills> had approximately 2.45k stars,
was not archived, and showed upstream activity on 2026-07-10. The skills.sh
results showed roughly 726–736 installs for the selected initial skills. The
installer reported Gen “Safe”, zero Socket alerts, and Low/Medium Snyk risk; this
is an input to review, not a sandbox.

Installed and read in full:

- `jetson-diagnostic`
- `jetson-memory-audit`
- `jetson-headless-mode`
- `jetson-inference-mem-tune`
- `jetson-llm-serve`
- `jetson-llm-benchmark`

Codex/shared paths:

```text
/home/neko/.agents/skills/jetson-diagnostic
/home/neko/.agents/skills/jetson-memory-audit
/home/neko/.agents/skills/jetson-headless-mode
/home/neko/.agents/skills/jetson-inference-mem-tune
/home/neko/.agents/skills/jetson-llm-serve
/home/neko/.agents/skills/jetson-llm-benchmark
```

They were installed from direct GitHub skill URLs with the equivalent pattern:

```bash
npx -y skills add \
  https://github.com/NVIDIA/skills/tree/main/skills/NAME \
  -g -y
```

The skills installer initially detected only Codex because Claude was off PATH.
Each skill was therefore copied explicitly for Claude Code using:

```bash
npx -y skills add \
  https://github.com/NVIDIA/skills/tree/main/skills/NAME \
  -g --agent claude-code -y
```

Verified Claude paths:

```text
/home/neko/.claude/skills/jetson-diagnostic
/home/neko/.claude/skills/jetson-memory-audit
/home/neko/.claude/skills/jetson-headless-mode
/home/neko/.claude/skills/jetson-inference-mem-tune
/home/neko/.claude/skills/jetson-llm-serve
/home/neko/.claude/skills/jetson-llm-benchmark
```

One CLI help probe was parsed as an install command and also created a
project-local copy at `.agents/skills/jetson-diagnostic`. It is harmless and
provides a project-shared fallback, but it is an intentional item in the file
inventory now and must not be mistaken for application source.

Rollback: use `npx skills remove -g` with explicit skill/agent selections, or
remove only the documented copied directories after confirming no other agent
uses them. Do not delete the whole parent skills directory.

## 2026-07-12 — live Jetson audits

Ran the NVIDIA `jetson-diagnostic` structured snapshot and
`jetson-memory-audit` helpers. Representative baseline:

- variant detected as `orin-nano-8gb`, L4T 39.2.0;
- 7,665,092 KiB total RAM;
- 3,512,328 KiB available during the memory audit;
- no swap;
- default target `graphical.target`;
- GDM/display manager active;
- about 49–50 C during the short sample;
- 15 W mode 0, which is the highest mode in the active
  `/etc/nvpmodel/nvpmodel_p3767_0003.conf` (the other available mode is 7 W);
- NvMap per-process attribution was unavailable without root;
- largest PSS entries were Firefox/web-content and GNOME processes.

The generic NVIDIA memory recommender, using the live audit, selected llama.cpp
with 4-bit GGUF and `-ngl 28 -c 4096 --no-mmap` as its lowest-memory generic LLM
path. It offered vLLM with `--gpu-memory-utilization=0.5`, 4K context, and four
sequences as an alternative. Those are generic hints; Gemma 4's model-specific
LiteRT evidence takes precedence for the first benchmark.

## 2026-07-12 — headless plan and failed privileged apply

The owner explicitly approved completely shutting down X/GNOME/Firefox.

The NVIDIA headless planner proposed switching to `multi-user.target`, stopping
GDM/display-manager aliases, and also disabling Bluetooth, ModemManager,
kerneloops, and Avahi. Only the GUI recommendations were accepted; Bluetooth
and Avahi were deliberately retained pending audio/discovery decisions.

The plan's 1,480 MB total is not a trustworthy expected delta because it counts
`gdm3`, `gdm`, and `display-manager` aliases separately. The actual value must
come from a before/after memory audit.

The required dry run completed. A subsequent attempt to apply only:

```bash
sudo systemctl set-default multi-user.target
```

failed because the non-interactive session had no sudo credential/TTY. The
script continued after warning. Verification showed the host still used
`graphical.target`; no privileged headless change occurred.

Firefox was terminated after the owner confirmed that the graphical workload
could be shut down. This raised available RAM from roughly 3.35 GiB during the
initial GUI-heavy audit to approximately 5.0 GiB immediately afterward. A later
2026-07-13 check showed about 4.6 GiB available, but GDM, root-owned Xorg, GNOME
Shell, GNOME Terminal, and several session utilities were still active. Killing
the wrong user session from this Codex process could also have terminated the
setup session, so the session IDs and controlling terminals were inspected first.

The graphical login was isolated as `loginctl` session 2 on `seat0/tty2`, while
Codex was in session 10 on `pts/1`. The owner had explicitly authorized complete
GUI shutdown, so the graphical login and its final panel scope were stopped with:

```bash
loginctl terminate-session 2
systemctl --user stop app-gnome-nvpmodel_indicator-10043.scope
```

This removed Firefox, the owner's Xorg/GNOME Shell/GNOME Session/GNOME Terminal,
and the orphaned panel processes without disrupting Codex or the separate shell.
The NVIDIA memory audit immediately afterward reported 6,446,796 KiB available
of 7,665,092 KiB, 1,125/7,485 MB in the `tegrastats` sample, no swap, 0% GPU,
about 47.5 C maximum temperature, and roughly 4.87 W board input power. The
initial comparable audit had reported 3,512,328 KiB available, so terminating
the GUI session recovered about 2.80 GiB at those sample points.

GDM stayed active and later spawned greeter session `c2` as UID 122 on `tty1`,
including root-owned Xorg and a `gdm` GNOME Shell. A final check showed about
5.9 GiB available; Firefox and the owner's desktop remained absent. The default
also remains `graphical.target`. Stopping the greeter and making the state survive
reboot require the planned privileged commands below; use them and reboot for the
actual headless production baseline.

A final unprivileged `loginctl terminate-session c2` attempt was rejected with
`Interactive authentication required`; no greeter process was changed.

Planned owner/admin commands, after current graphical work is saved:

```bash
sudo systemctl set-default multi-user.target
sudo systemctl disable --now gdm3
```

If `gdm3` is an alias and the second command reports that, use the resolved
`display-manager` unit reported by `systemctl status display-manager`. A reboot
is the cleanest way to terminate all remaining user graphical processes and
measure a production baseline.

Rollback:

```bash
sudo systemctl set-default graphical.target
sudo systemctl enable gdm3
sudo reboot
```

After reboot, run:

```bash
bash /home/neko/.agents/skills/jetson-memory-audit/scripts/audit.sh
```

Record the available-memory delta and verify SSH/console access before treating
the headless conversion as complete.

## 2026-07-12 — Claude Code reviewer attempts

Claude Code was invoked twice by absolute path as a read-only, no-edit/no-install
independent architecture reviewer. Both attempts failed before producing a memo
with HTTP 529/1305 overload errors from the configured Z.AI inference gateway.
The first attempt also exposed a broken `SessionEnd` hook referring to missing
`/home/neko/.claude/helpers/hook-handler.cjs`; safe mode removed that hook error
on the second attempt, but the provider still returned 529.

No primary-source research claim from those failed attempts was used. Codex
parallel agents and direct primary-source inspection produced the research notes.
The Claude configuration was not modified.

On 2026-07-13, a broader high-effort read-only retry was stopped after about
23 minutes without provider output. Its `SessionEnd` hook again referenced the
missing `/home/neko/.claude/helpers/hook-handler.cjs`. A smaller retry succeeded
using the absolute binary and safe local-only tools:

```bash
/home/neko/.local/bin/claude -p --safe-mode --permission-mode plan \
  --tools 'Read,Glob,Grep' --effort medium '<local consistency-review prompt>'
```

It read the project files and reported five material deployment issues:

1. six Gemma threads oversubscribed all six host cores before real-time audio;
2. `Type=simple` did not make model readiness explicit to dependent units;
3. the 8 GB/no-swap host lacked cgroup bounds and OOM preference;
4. the development service still uses the repository-owning `neko` identity;
5. every local principal can access the unauthenticated loopback API.

The first three findings were acted on immediately: the deployed profile now
uses four threads, `Type=notify` with a real `READY=1` datagram, memory high/max
and no-swap controls, lower CPU weight/nice priority, positive OOM adjustment,
task limits, and empty capability sets. A dedicated production identity plus a
supervisor-owned credential or Unix socket remain pre-passenger hardening gates.
Inspection confirmed LiteRT-LM's server is the single-request `HTTPServer`, so
engine generations are already serialized rather than concurrent. Claude made
no file or system change.

## 2026-07-12 — uv and LiteRT-LM

The system Python did not have `pip`, so the first `python3 -m pip` command
failed before making changes.

Installed the pinned uv 0.11.28 ARM64 GNU release from:
<https://github.com/astral-sh/uv/releases/tag/0.11.28>.
The release tarball's published SHA-256 was checked before installation.

Installed files and local hashes:

| File | SHA-256 |
| --- | --- |
| `/home/neko/.local/bin/uv` | `b9f74e398b6b15826a4b68b5a83d039036d47df64013e7faf1a9974ec199c144` |
| `/home/neko/.local/bin/uvx` | `a5dee4970f3f1cea8d50d1ddecdf91f95f0f1e7a6e52336b15a95d8ab981b7e3` |

Installed LiteRT-LM with:

```bash
/home/neko/.local/bin/uv tool install 'litert-lm==0.14.0'
```

Verified CLI: `/home/neko/.local/bin/litert-lm`, version 0.14.0.

Resolved tool environment packages:

```text
absl-py==2.5.0
click==8.4.2
flatbuffers==25.12.19
litert-lm==0.14.0
litert-lm-api==0.14.0
litert-lm-builder==0.14.0
prompt-toolkit==3.0.52
protobuf==7.35.1
questionary==2.1.1
tomli==2.4.1
typing-extensions==4.16.0
wcwidth==0.8.2
```

The tool lives in uv's user tool environment under `/home/neko/.local/share/uv`
and exposes `run`, `benchmark`, `import`, `list`, `delete`, and an
OpenAI-compatible `serve` command. `/home/neko/.local/bin` is still not in the
non-interactive PATH, so systemd units must use absolute paths.

Rollback:

```bash
/home/neko/.local/bin/uv tool uninstall litert-lm
```

Remove `uv`/`uvx` manually only if no other user tools depend on them.

## 2026-07-12 — Gemma model artifact

Selected source:
<https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm>.

- Repository revision:
  `9262660a1676eed6d0c477ab1a86344430854664`.
- File: `gemma-4-E2B-it.litertlm`.
- Exact expected size: 2,588,147,712 bytes.
- Expected SHA-256:
  `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c`.
- Destination:
  `/home/neko/models/gemma-4-E2B-it-litert-lm/9262660a1676eed6d0c477ab1a86344430854664/`.

At the time this section was first written, the resumable, revision-pinned
download and checksum verification were still running. They subsequently
completed successfully on 2026-07-13.

Verified source artifact:

```text
/home/neko/models/gemma-4-E2B-it-litert-lm/9262660a1676eed6d0c477ab1a86344430854664/gemma-4-E2B-it.litertlm
size:   2588147712 bytes
sha256: 181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c
```

Imported it into LiteRT-LM as model ID `gemma-4-e2b-it`. LiteRT-LM made a
separate copy at:

```text
/home/neko/.litert-lm/models/gemma-4-e2b-it/model.litertlm
```

The imported copy is the same size and its SHA-256 was independently verified as
the same value. `litert-lm list` reports the ID successfully. The source tree is
about 2.5 GB; the imported model directory grew to about 4.2 GB after runtime
caches were generated. The two artifact copies are intentionally retained for
now: one is a provenance-pinned source and one is LiteRT-LM's managed copy.

Important generated caches in the managed directory after testing:

| Cache | Approximate bytes |
| --- | ---: |
| Main CPU/XNNPACK | 788,412,736 |
| GPU weight cache from failed GPU test | 778,365,184 |
| GPU program cache from failed GPU test | 12,308,656 |
| Vision encoder CPU/XNNPACK | 217,562,184 |
| Audio encoder CPU/XNNPACK | 91,462,280 |
| Audio adapter CPU/XNNPACK | 9,443,576 |
| Vision adapter CPU/XNNPACK | 4,724,984 |

### Gemma local validation

GPU text smoke test:

```bash
timeout 300 /home/neko/.local/bin/litert-lm run gemma-4-e2b-it \
  --backend gpu --cache disk --max-num-tokens 2048 \
  --temperature 0.2 --seed 1 --prompt 'Reply with exactly: meow'
```

The model emitted `meow`, proving that inference reached generation, but then
logged missing OpenCL, `NVVM compilation failed: 3`, Dawn Vulkan pipeline
creation errors, and `VK_ERROR_UNKNOWN`, before exiting 139 with a core dump.
`tegrastats` showed GPU activity, roughly 3.9/7.5 GB RAM used at the observed
peak, temperature below 49 C, and input power below about 6.9 W. This was not an
OOM or thermal failure. It matches the failure reported for the official Gemma
4 E2B LiteRT artifact on Jetson Orin/Thor in upstream issues
<https://github.com/google-ai-edge/LiteRT-LM/issues/2570> and
<https://github.com/google-ai-edge/LiteRT-LM/issues/2338>. Do not select the
prebuilt GPU backend for a boot service until upstream supplies a validated fix
or a locally built accelerator passes the benchmark and soak suite.

A first CPU smoke with only 512 cache tokens failed cleanly with a
`DynamicUpdateSlice` size error, showing that this artifact needs a larger cache
even for a tiny prompt. Repeating with 2,048 tokens succeeded and returned
`meow` with exit status 0.

Short CPU benchmark:

```bash
/home/neko/.local/bin/litert-lm benchmark gemma-4-e2b-it \
  --backend cpu --cache disk --max-num-tokens 2048 \
  --cpu-thread-count 6 --prefill-tokens 256 --decode-tokens 64
```

| Metric | Local result |
| --- | ---: |
| Prefill | 37.30 tokens/s |
| Decode | 14.51 tokens/s |
| Initialization | 1.1278 s |
| Time to first token | 6.9330 s |
| Peak RAM observed by short `tegrastats` sample | about 3,618/7,485 MB used |
| Maximum CPU temperature observed | about 49.6 C |
| Maximum input power observed | about 8.45 W |

This was a short warm synthetic run with the desktop still active, not an
acceptance benchmark. It nevertheless establishes a usable CPU fallback and
leaves the GPU available for perception work.

A same-parameter repeat after the GUI logout, but while a four-worker Audex
snapshot download and hashing job was active, was slower: 30.84 prefill tok/s,
11.45 decode tok/s, 1.2178 s initialization, and 8.3878 s TTFT. That run is
retained as contention evidence rather than called a clean headless result. It
shows that background provisioning/updates must be excluded from operation or
resource-limited and that final claims need multiple runs with P50/P95 values.

After Audex download/hashing finished and all transfer processes exited, a run
with the owner's desktop logged out used the same shape as the published LiteRT
model-card benchmark. The GDM greeter was still resident:

```bash
/home/neko/.local/bin/litert-lm benchmark gemma-4-e2b-it \
  --backend cpu --cache disk --max-num-tokens 2048 \
  --cpu-thread-count 6 --prefill-tokens 1024 --decode-tokens 256
```

| Metric | Local desktop-user-free CPU result |
| --- | ---: |
| Prefill | 142.28 tokens/s |
| Decode | 14.73 tokens/s |
| Initialization | 1.8600 s |
| Time to first token | 7.2651 s |
| Peak RAM in 1-second `tegrastats` samples | 2,249/7,485 MB used |
| Peak CPU/TJ temperature observed | about 50.2 C |
| Peak input power observed | about 8.51 W |
| GPU utilization | 0% throughout |

The pre-run sample was about 1,356/7,485 MB used, so the observed peak delta was
roughly 893 MB. This is one warm-cache synthetic run with Codex and normal
headless services still active, not a P50/P95 production claim. The much faster
1,024-token prefill than the 256-token runs reflects the artifact's optimized
prefill signature/batching and should not be extrapolated to short prompts.

CPU audio-input smoke test:

```bash
timeout 300 /home/neko/.local/bin/litert-lm run gemma-4-e2b-it \
  --backend cpu --audio-backend cpu --cache disk \
  --max-num-tokens 2048 --cpu-thread-count 6 \
  --temperature 0.1 --seed 1 \
  --attachment /usr/share/sounds/alsa/Front_Center.wav \
  --prompt 'Transcribe the attached audio. Return only the spoken words.'
```

It returned `front center` and exited 0 in about 3.2 seconds wall time. This is a
single functional check, not an ASR quality or streaming-latency evaluation.

LiteRT-LM 0.14.0's stock `serve` command exposes no CLI settings for backend,
thread count, or maximum cache tokens. Its inspected implementation initializes
the requested artifact lazily with its configured backend and
`max_num_tokens=None`. Do not boot-enable that command unchanged: Neko needs a
small wrapper or an upstream server option that explicitly pins CPU, six threads,
and a measured 2K/4K cache before a systemd service is safe.

Model rollback:

```bash
/home/neko/.local/bin/litert-lm delete gemma-4-e2b-it
```

Delete the pinned source directory separately only if provenance retention and
future re-import are no longer desired.

## 2026-07-13 — bounded Gemma API and service template

Added the project wrapper `scripts/serve_gemma_litert.py`. It uses the handler
implementation shipped with the pinned LiteRT-LM 0.14.0 tool but replaces its
lazy, artifact-default engine selection with one preloaded fixed engine:

- model ID `gemma-4-e2b-it` only;
- loopback bind by default;
- CPU main, vision, and audio backends;
- six main CPU threads;
- 2,048-token KV cache;
- persistent compiled-model caches;
- warning-level LiteRT logging by default (`--verbose` restores information logs);
- engine initialization before the API prints `READY` or starts listening.

The wrapper deliberately imports LiteRT-LM CLI private APIs. It must be retested
and, if necessary, updated before changing the pinned runtime version.

Validation used an unprivileged test port:

```bash
/home/neko/.local/share/uv/tools/litert-lm/bin/python \
  scripts/serve_gemma_litert.py --host 127.0.0.1 --port 19379 \
  --max-num-tokens 2048 --cpu-thread-count 6
```

The engine reported CPU/6 threads/2,048 tokens, reached `READY`, returned the
expected `gemma-4-e2b-it` object from `GET /v1/models`, and returned `meow` from
an OpenAI-compatible `POST /v1/chat/completions`. The HTTP request completed in
about 2.0 seconds after warm startup. SIGINT shut the engine down cleanly with
exit status 0.

Added the system unit source
`deploy/systemd/neko-gemma.service`. It binds only to `127.0.0.1:9379`, starts
the bounded wrapper as user/group `neko`, limits restart bursts, and applies
basic systemd filesystem/process hardening while allowing model-cache writes.
Its systemd IP policy denies all destinations except localhost, preventing this
offline model worker from fetching remote media even though the upstream HTTP
handler knows how to resolve image URLs.
`systemd-analyze verify` reports no warnings for this unit (the full verifier
still prints unrelated legacy warnings for two existing NVIDIA units).

After the owner approved permanent headless boot and service installation, the
unit was verified and installed with:

```bash
sudo install -o root -g root -m 0644 \
  /home/neko/repos/nekokitty/deploy/systemd/neko-gemma.service \
  /etc/systemd/system/neko-gemma.service
sudo systemctl daemon-reload
sudo systemctl enable --now neko-gemma.service
```

`systemd-analyze verify` reported no warning for this unit; it did surface two
unrelated legacy `StandardOutput=syslog` warnings in existing NVIDIA units.
The service reached `READY` in about two seconds, and these checks passed:

- `systemctl is-enabled neko-gemma.service` returned `enabled`;
- `systemctl is-active neko-gemma.service` returned `active`;
- `GET http://127.0.0.1:9379/v1/models` returned only
  `gemma-4-e2b-it`;
- a fixed-model chat request asking for exactly `meow` returned `meow`;
- ready memory settled near 1.5 GiB and `NRestarts=0`;
- the controlled GPU re-test stopped this service and started it again; it
  returned its model health response with no restart loop.

The unit is enabled for `multi-user.target`, but an actual cold reboot acceptance
test is still required before calling boot behavior fully validated. The service
is not ordered after network targets and its systemd IP policy denies all
destinations except localhost.

After the independent review, the source and installed unit were updated
byte-for-byte to the current normal profile:

- four main CPU threads, leaving two cores' worth of scheduling headroom;
- `Type=notify`/`NotifyAccess=main`, with the wrapper sending `READY=1` only after
  engine construction and publishing a detailed systemd status string;
- `MemoryHigh=2G`, `MemoryMax=2300M`, `MemorySwapMax=0`, and
  `OOMScoreAdjust=500`;
- `CPUWeight=40`, `Nice=5`, `TasksMax=128`, empty capability/ambient-capability
  sets, and the existing filesystem/network hardening.

The wrapper default also changed from six to four threads. `python -m py_compile`
and `systemd-analyze verify` passed; the only verifier messages were the same two
unrelated legacy NVIDIA-unit warnings. After daemon reload/restart, systemd
reported `Type=notify`, `StatusText=Serving gemma-4-e2b-it ... with 4 CPU
threads`, `NRestarts=0`, and active/running. `GET /v1/models` passed and a
deterministic chat request again returned exactly `meow`. Memory after that
request was about 1,591 MB with a 1,592 MB recorded peak, below the configured
high watermark. This is a restart/readiness result, not the still-outstanding
cold-reboot gate.

`systemd-analyze security --no-pager neko-gemma.service` rated the current
development unit `5.1 MEDIUM`. This is an improvement record, not a production
security claim; the same-user model/repository access and unauthenticated local
API account for important remaining exposure.

Rollback if later installed:

```bash
sudo systemctl disable --now neko-gemma.service
sudo rm /etc/systemd/system/neko-gemma.service
sudo systemctl daemon-reload
```

## 2026-07-13 — ZipDepth evaluation assets

Cloned only the official ZipDepth repository and checkpoint artifacts into:

```text
/home/neko/models/ZipDepth/a302e5437bc58f15c4efd41d3e8222bf24f7d470
```

Verified origin: `https://github.com/fabiotosi92/ZipDepth.git`. Remote `main`,
remote HEAD, and detached local HEAD were all
`a302e5437bc58f15c4efd41d3e8222bf24f7d470`; the worktree was clean.

| Checkpoint | Bytes | Verified SHA-256 |
| --- | ---: | --- |
| `checkpoints/zipdepth_base.pth` | 27,298,978 | `a55910bb0b99c8c5e641cb9206e810b269690ad94e8a2ef08c827c4679391a65` |
| `checkpoints/zipdepth_base_npu.pth` | 27,295,474 | `627c04fda584133ead4310074884a4a037061b4c01ba86e73e492ea30fab570d` |

Total disk use is about 123 MiB, including about 60 MiB of Git metadata. No
repository code was executed, no dependencies were installed, and no ONNX or
TensorRT engine was generated. The next step requires a JetPack/R39-compatible
TensorRT toolchain and a fixed camera input shape. It also depends on confirming
that ZipDepth is auxiliary relative depth rather than a metric or safety sensor.

The configured official Jetson R39.2 package repository offered
TensorRT `10.16.2.10-1+cuda13.2` (`tensorrt`, `libnvinfer10`, development and
Python packages) and CUDA compiler `cuda-nvcc-13-2` version `13.2.78-1`; the
minimal selected toolchain was subsequently installed as recorded below. No
ZipDepth Python/runtime dependency was installed and no repository code was run.

Rollback: remove only the exact model directory above after confirming that its
pinned source/checkpoints are no longer needed.

## 2026-07-13 — Audex evaluation snapshot

Downloaded the complete public `nvidia/Nemotron-Labs-Audex-2B` repository for
non-executed evaluation at exact revision:

```text
b13ccb2373764e01aa4e49311d34c9428c925138
```

Destination:

```text
/home/neko/models/Nemotron-Labs-Audex-2B/b13ccb2373764e01aa4e49311d34c9428c925138
```

Used Hugging Face Hub CLI/library 1.23.0 through `uvx`, rather than installing it
as a persistent uv tool. Its resolved ephemeral environment is cached under
`/home/neko/.cache/uv/archive-v0/SYjqpxLozhcDS2ay`. The initial resumable command
was equivalent to:

```bash
/home/neko/.local/bin/uvx --from huggingface_hub hf download \
  nvidia/Nemotron-Labs-Audex-2B \
  --revision b13ccb2373764e01aa4e49311d34c9428c925138 \
  --local-dir /home/neko/models/Nemotron-Labs-Audex-2B/b13ccb2373764e01aa4e49311d34c9428c925138 \
  --max-workers 4
```

Public unauthenticated access worked. The Xet transfer later stalled after a
temporary DNS failure to the Hugging Face CDN. Completed files were preserved;
only the two missing large files were retried with two workers and
`HF_HUB_DISABLE_XET=1`, which completed through standard HTTP. After verifying
the finished artifacts, six obsolete `.incomplete` transfer fragments totaling
5,499,346,058 bytes were deleted. No completed content or metadata was removed.

Final verification, excluding downloader metadata:

- 106 repository files;
- exactly 12,281,588,752 content bytes, matching the remote tree inventory;
- per-file local metadata records the exact requested commit;
- about 12 GB allocated on disk after stale-fragment cleanup.

Major weight hashes:

| Artifact | Bytes | Verified SHA-256 |
| --- | ---: | --- |
| `checkpoint_folder_full/model-00001-of-00002.safetensors` | 4,500,748,032 | `b5bc4d260f8ac97a71dab70a329b15c357dd9a63b7d77d3b7a5049ad059c0a26` |
| `checkpoint_folder_full/model-00002-of-00002.safetensors` | 1,301,260,840 | `399fe78c625a8dd55082187c870448c0bb44f2b73c9d3d93c398e77d5a3bb4fe` |
| `audex_causal_speech_decoder/model.safetensors` | 2,455,045,520 | `07cd590522869b042b893fea2cad98e854eef3f9cc395edcdb4b329ebd18a392` |
| `enhancement_VAE/XCodec_RVQ4_mono_causal_fp32.safetensors` | 2,622,247,900 | `3420c1628db153666ae344a4372b0d9849530040576e1f2c0edcbacb26deddc0` |
| `nv-whisper/model.safetensors` | 1,273,988,176 | `01fcbfa8ac3d3bc4c5ab97c439dfecfea2a9c2e061031280efed292fc37b4a44` |

This step puts Audex “on disk for evaluation” only. No repository Python or
shell code was executed, no `trust_remote_code` model was loaded, no vLLM/plugin
runtime was installed, and no service was created. The snapshot is governed by
NVIDIA's OneWay Noncommercial License and includes dependencies that also need
review. The full BF16 model plus FP32 causal speech decoder exceed this board's
usable memory before runtime overhead; do not try to preload them at boot.

Rollback: remove only the exact revision directory above. The generic uv/HF
cache may be pruned separately with uv's supported cache command only after
checking that no other uvx task needs it.

## 2026-07-13 — owner decisions and permanent headless state

The durable answer set is in
`docs/decisions/2026-07-13-owner-decisions.md`. It confirms noncommercial use,
sequential model residency, no remote Audex host, permanent headless boot,
system-package/service authority, private Git publication, manual-only motion,
local-first functionality, and text-only default cloud egress.

The previously planned headless change was applied outside the failed
unprivileged attempt. Verification on 2026-07-13 showed:

```text
systemctl get-default                 multi-user.target
systemctl is-active gdm3              inactive
systemctl is-active gdm               inactive
systemctl is-active display-manager   inactive/not-found
Xorg/gnome-shell/firefox processes    none
```

`gdm3` still reports `alias` and `gdm` reports `static`; the decisive persistent
state is that the default target is `multi-user.target` and no display-manager
unit is pulled into the boot transaction. Bluetooth and Avahi were retained.

The post-service NVIDIA memory audit reported:

- 7,665,092 KiB total and 5,951,504 KiB available, no swap;
- Gemma process 104127 at 1,539,996 KiB PSS, the largest process;
- `tegrastats`: 1,681/7,485 MB used, 0% GPU, approximately 44.9 C and 4.87 W;
- default `multi-user.target`, all display managers inactive.

The exact memory recovered by the privileged target change cannot be isolated
from the earlier session termination and later Gemma load without a matching
before/after pair; do not invent that delta. Graphical rollback remains:

```bash
sudo systemctl set-default graphical.target
sudo systemctl enable gdm3
sudo reboot
```

## 2026-07-13 — CUDA 13.2 and TensorRT 10.16.2

The owner authorized the host-matched compiler and inference toolchain. A dry
run showed that the full `cuda-toolkit-13-2` meta-package would add GUI-oriented
Nsight components. Installed only the required build/runtime closure:

```bash
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
  --no-install-recommends \
  build-essential cmake ninja-build pkg-config \
  cuda-nvcc-13-2 cuda-cudart-dev-13-2 libcublas-dev-13-2 \
  tensorrt python3-libnvinfer
```

APT resolved 49 new packages. The pre-install simulation estimated 6,031 MB of
archives and 10.6 GB installed. Important exact versions:

| Package/component | Version |
| --- | --- |
| `cuda-nvcc-13-2` | `13.2.78-1` |
| `cuda-cudart-dev-13-2` | `13.2.75-1` |
| `libcublas-dev-13-2` | `13.4.0.1-1` |
| `tensorrt` / `python3-libnvinfer` | `10.16.2.10-1+cuda13.2` |
| `build-essential` | `12.10ubuntu1` |
| CMake | `3.28.3-1build7` |
| Ninja | `1.11.1-2` |
| pkg-config | `1.8.1-2build1` |

The full dependency closure remains recoverable from the APT history entry
starting `2026-07-13 08:38:21` in `/var/log/apt/history.log`. Validation:

```text
/usr/local/cuda/bin/nvcc --version  CUDA 13.2, V13.2.78
import tensorrt                  TensorRT Python 10.16.2.10
command -v trtexec               /usr/bin/trtexec
dpkg -C                          no output/errors
apt-get check                    passed
ldconfig                         libcudart.so.13, libcublas.so.13,
                                 libnvinfer.so.10 resolved
root filesystem                  915G total, 45G used, 824G available
```

`nvcc` is deliberately invoked by absolute `/usr/local/cuda/bin/nvcc`; no shell
profile was changed. Removing this toolchain could break future model builds.
If rollback is required, first stop every dependent service/build, explicitly
review `apt-get remove --dry-run` for the nine requested packages above, and
review a separate `apt-get autoremove --dry-run`. Do not blindly autoremove
Jetson/NVIDIA packages.

## 2026-07-13 — current LiteRT GPU re-test and upstream report

After installing CUDA/NVVM and making the host headless, the CPU service was
stopped and the exact stock GPU smoke was repeated with core dumps disabled:

```bash
timeout 300 /home/neko/.local/bin/litert-lm run gemma-4-e2b-it \
  --backend gpu --cache disk --max-num-tokens 2048 \
  --temperature 0.2 --seed 1 --prompt 'Reply with exactly: meow'
```

It again printed `meow`, then segfaulted with exit 139. Installing the compiler
stack did not repair the prebuilt WebGPU delegate. The CPU service was
immediately restarted and returned a healthy model list with `NRestarts=0`.

With explicit owner authorization, a non-sensitive R39.2/LiteRT-LM 0.14.0
reproduction comment was posted to:
<https://github.com/google-ai-edge/LiteRT-LM/issues/2570#issuecomment-4959824784>.
The exact text is preserved in
`docs/research/2026-07-13-litert-upstream-report.md`.

## 2026-07-13 — official Gemma QAT GGUF alternate artifact

Current official repository:
<https://huggingface.co/google/gemma-4-E2B-it-qat-q4_0-gguf>.

- pinned revision: `69536a21d70340464240401ba38223d805f6a709`;
- selected language model: `gemma-4-E2B_q4_0-it.gguf`;
- exact bytes: 3,349,514,112;
- verified SHA-256:
  `3646b4c147cd235a44d91df1546d3b7d8e29b547dbe4e1f80856419aa455e6fd`;
- destination:
  `/home/neko/models/gemma-4-E2B-it-qat-q4_0-gguf/69536a21d70340464240401ba38223d805f6a709/`.

Downloaded by revision-pinned resumable HTTPS and checked locally. The optional
986,833,312-byte multimodal projector was not downloaded: the existing LiteRT
artifact already provides the evaluated audio/vision path, while this GGUF is a
text-only GPU/runtime fallback. Its completed Jetson benchmark is recorded below
and in `docs/research/2026-07-13-local-benchmarks.md`.

## 2026-07-13 — Git/GitHub project state

The top-level directory is the intended repository on branch `main`. Attached
remote:

```text
origin https://github.com/liamhelmer/nekokitty.git
```

The GitHub repository was verified private and empty before initial publication.
An accidental empty nested clone at `./nekokitty` was moved without deletion to
`/home/neko/repos/nekokitty-empty-clone-backup-20260713`. `.gitignore` excludes
weights, engines, caches, private media/transcripts, credentials, runtime state,
and ordinary build products. Model files remain outside the repository.

The repository had no base/default branch, so a draft pull request was impossible
for the initial publication. Repository-local Git identity was set to `Liam
Helmer <62965078+liamhelmer@users.noreply.github.com>`; no global Git setting was
changed. After full tests, service/package/artifact checks, Markdown-link audit,
`git diff --check`, and a secret-signature scan passed, the intentional 39-file
bootstrap commit was pushed directly to the private `main` branch:

```text
3a0c37fabfb5e6bbc4aa36eb0015e8b64ff91601
Bootstrap Neko local inference stack
```

GitHub now reports `main` as the default branch. Future work should use a topic
branch and draft pull request unless another explicit exception applies.

## 2026-07-13 — digest-pinned llama.cpp/CUDA alternate profile

Cloned upstream `ggerganov/llama.cpp` into
`/home/neko/.local/src/llama.cpp` at commit
`e920c523e3b8a0163fe498af5bf90df35ff51d25` (release label `b9987`) and began a
native architecture-87 CUDA build in `build-orin-cuda`. The compile was paused
safely while a large generated CUDA kernel set remained; that native runtime is
not complete and must not be represented as installed.

The official NVIDIA-AI-IOT Orin image was pulled by immutable digest:

```text
ghcr.io/nvidia-ai-iot/llama_cpp@sha256:ba196b9760fda683a84048916ec6666650cc4b05d3bfc05c02bf1917553e55f1
```

It is an 8,226,277,017-byte image containing llama.cpp build 8966 at commit
`7b8443ac7`. Its base labels/tags identify L4T R36.4, Ubuntu 22.04 and CUDA 12.9,
not this host's R39.2/Ubuntu 24.04/CUDA 13.2. The image also omitted
`/usr/local/lib` from `LD_LIBRARY_PATH`, so its executables initially failed to
load `libllama-common.so.0`. The project Dockerfile creates a digest-pinned
one-line derivative named locally as
`neko/llama_cpp:jetson-orin-8966-loaderfix`; no binaries or model content are
changed. With `--runtime nvidia`, it found the Orin compute-8.7 device and
reported 7,485 MiB GPU-visible shared memory.

The official NVIDIA `jetson-llm-benchmark` wrapper ran with the normal Gemma
service stopped, four CPU threads, all 99 layers offloaded, 1,024 prompt tokens,
and 256 generated tokens. It completed without OOM:

| Metric | Local 15 W result |
| --- | ---: |
| Generation | 18.63 tokens/s |
| Inter-token time | 53.68 ms |
| Derived 1,024-token prefill duration | 3,474.73 ms |
| Peak observed RAM | about 3,802/7,485 MB |
| Peak observed input power | about 11.07 W |
| Peak observed GPU temperature | about 52.1 C |

The wrapper calls the derived prompt duration TTFT, but it is calculated from
prompt throughput rather than instrumented interactive latency. This single run
proves a usable alternate text profile, not combined-workload or vendor support
for the older container on R39.2. The CPU LiteRT service was restarted and
returned healthy afterward.

Rollback: stop all containers using the derivative, remove that small image and
then the pinned NVIDIA base only if no other experiment needs it. Remove the
native source/build tree separately. Keep the official GGUF unless the alternate
profile is deliberately abandoned.

## 2026-07-13 — ZipDepth faithful export and target TensorRT plans

Created a CPU-only, purpose-specific exporter environment at:

```text
/home/neko/models/ZipDepth/export-env
```

`deploy/requirements/zipdepth-export.in` is the human input and the generated
`deploy/requirements/zipdepth-export.lock` contains hashes and the exact uv
compile command. The environment was created/synchronized with uv from the lock
using Python 3.12.3 and occupies about 759 MiB. Installed distributions are:

```bash
/home/neko/.local/bin/uv venv --python /usr/bin/python3 \
  /home/neko/models/ZipDepth/export-env
/home/neko/.local/bin/uv pip sync \
  --python /home/neko/models/ZipDepth/export-env/bin/python \
  --require-hashes deploy/requirements/zipdepth-export.lock
```

```text
filelock 3.29.7       fsspec 2026.6.0       Jinja2 3.1.6
MarkupSafe 3.0.3      mpmath 1.3.0          networkx 3.6.1
numpy 1.26.2          onnx 1.18.0           protobuf 7.35.1
setuptools 81.0.0     sympy 1.14.0          torch 2.12.1+cpu
typing_extensions 4.16.0
```

The direct PyTorch wheel is the official CPU-only aarch64 build pinned in the
input/lock. No system Python package was replaced. The project exporter and
tests are `scripts/export_zipdepth_onnx.py` and
`tests/test_export_zipdepth_onnx.py`. The exporter fails closed on source,
checkpoint, dependency, state-key, shape, domain, and operator drift; preserves
the learned GlobalContext implementation; uses static batch-one `384x672`,
opset 17, `dynamo=False`, and no `onnxsim`; and emits a provenance manifest.

Both system Python and the export environment passed all 11 unit tests. The real
CPU export then passed reference/fused/export-prepared parity, ONNX checker,
strict shape inference, standard-domain audit, and the post-export PyTorch
mutation check. Warnings only stated that the deliberately selected legacy
exporter is deprecated and that a negative-step Slice was not constant folded.

TensorRT 10.16.2 parsed the checked graph without custom/plugin nodes. With Gemma
stopped, optimization level 5, a 512 MiB workspace, zero auxiliary streams, and
a shared timing cache, local builds completed as follows:

| Artifact | Bytes | SHA-256 | Build result |
| --- | ---: | --- | --- |
| ONNX | 24,639,883 | `38a9cc74be691be98190fd460ac1bba2986c5a7c16e3f33f5404463d74d2cbd0` | checked |
| ONNX manifest | 6,428 | `343920624f72a518d2d0dc2d3eed1c505128e48620284540555a321e9a135655` | checked |
| FP32/no-TF32 plan | 40,725,116 | `c4c3e7fd67b8e9204e24d2981aab21d635266ead121a5fa203a074d5a72012ba` | 194.855 s, passed |
| mixed FP32/FP16 plan | 13,224,420 | `13ed532b2ce2fa3cbcf6ad4cfb1dcb9e2c1498705477a328171dc750da1a4b78` | 446.986 s, passed |
| timing cache | 1,653,363 | `35c79e6a973ff91684ba1f540e5a8fa7913143808f2605bb20ebdd462d260964` | 3,827 entries |

Three 30-second FP16 runs with a two-second warm-up, one stream, and CUDA Graph
averaged 114.485 qps/8.733 ms model-only and 114.208 qps/9.101 ms with synthetic
binding transfers. Mean P99 was 8.805/9.178 ms respectively. One diagnostic
FP32 run measured 47.799 qps/20.919 ms model-only and 47.728 qps/21.232 ms with
transfers. Captured FP16 system peaks were about 2,414/7,485 MB RAM, 55.44 C,
and 11.96 W input. Raw logs/JSON live outside Git under
`/home/neko/models/ZipDepth/benchmarks`.

Added the one-shot validator `scripts/validate_zipdepth_tensorrt.py` and
`tests/test_validate_zipdepth_tensorrt.py`. It recreates the exact deterministic
fused PyTorch reference attested by the export manifest; pins/checks the exporter,
ONNX, plans, TensorRT binding, and libcudart; requires static contiguous FP32 I/O;
uses TensorRT 10 `execute_async_v3` with checked stdlib-`ctypes` CUDA calls and
pinned host staging; and writes a pass-only atomic JSON record. Final source
hashes were:

```text
validator  6a4150f33310008ae6fc7aa3cf3ed4a1e8d95cc385dc9ef17d9131388879e81e
tests      d69bd363f1bae18215b088239f1ef5456f3b2cd60259511b252d0843bfa36488
```

The initial live attempt failed closed before execution because TensorRT 10.16
returns paired `-1/-1` not-applicable component metadata for non-vectorized
LINEAR tensors rather than the explicit `1/4` pair used by the mock. Inspection
confirmed both engines had `LINEAR`, vectorized dimension `-1`, row-major FP32,
the exact static shapes, and contiguous strides. The guard was corrected to
accept exactly `(-1,-1)` or `(1,dtype.itemsize)` and reject mixed/other/vectorized
forms; tests increased from 14 to 16.

A second run passed every numerical gate but an optional metadata probe emitted
TensorRT API-error logging by reading `weight_streaming_budget_v2` on plans not
built with weight streaming. The result itself was valid, but the probe was
removed, a property-that-raises regression was added, and the 18-test suite
passed. The final forced run was clean and published:

```text
/home/neko/models/ZipDepth/engines/
  zipdepth_base_trt10.16.2_sm87_b1_384x672.validation.json
bytes:   13,091
sha256:  db2709054d61866aabeff56557bf7fcb30de7142ccbaa6ad4c25eadc0f58333a
status:  passed
```

| Comparison | MAE | Max abs | Max relative away from zero | Cosine | Spearman |
| --- | ---: | ---: | ---: | ---: | ---: |
| fused PyTorch vs FP32/no-TF32 | `7.129e-8` | `1.937e-7` | `4.644e-6` | `0.9999999999998` | `0.9999999999918` |
| fused PyTorch vs FP16 | `7.547e-5` | `4.811e-4` | `0.0160432` | `0.9999991529` | `0.9999955855` |
| TensorRT FP32 vs FP16 | `7.553e-5` | `4.811e-4` | `0.0160431` | `0.9999991529` | `0.9999955857` |

These results accept the exact deterministic tensor and engine path. Local
imagery, camera preprocessing, person tracking, and combined audio/LLM scheduling
remain required. ZipDepth remains non-metric auxiliary relative depth and is not
boot-enabled.

Rollback: stop any future ZipDepth unit, remove `engines`, `benchmarks`, and
`export-env` under `/home/neko/models/ZipDepth`, and retain the pinned source and
checkpoints unless their provenance is deliberately discarded. Removing CUDA or
TensorRT is the separate, higher-risk APT rollback documented above.

## 2026-07-13 — power, weather, geometry, and story constraint update

The owner supplied the following new design facts; no system package, service,
model, electrical wiring, or hardware was changed:

- LiFePO4 traction system described as 48 V, four 270 Ah batteries;
- existing DC/DC outputs at 24 V for lights/accessories and 19 V for the Jetson;
- 24 V is preferred for new accessories over adding a general 12 V rail;
- roof approximately 4 ft by 8 ft, with solar panels on top;
- rain, dirt/dust, temperature, and direct sun are in scope;
- target audience ages 5–10, with stories centered on cats of all kinds.

The four-battery topology remains ambiguous and the converter labels/wiring have
not been inspected. Documentation now explicitly prohibits midpoint accessory
loads, retains the separate 19 V Jetson branch, treats 24 V as the accessory
standard only after full-pack/protection/noise verification, and records the
required electrical/thermal/ingress survey in
`docs/research/2026-07-13-power-weather.md`.

Because NVIDIA requires an orderly OS shutdown before power removal, the plan
now distinguishes a normal off/offline control with hardware-delayed converter
cutoff from an immediate DC-rated service/emergency disconnect. The present
switch behavior has not been inspected; no shutdown controller was installed.

Manufacturer-source research also refreshed the current OAK-D W ingress options,
the PoE/M12 alternative, S2L startup/temperature limits, Jetson 9–20 V/3.5 A
barrel input and 0–35 C developer-kit range, LiFePO4 fuse interrupt/voltage
requirements, and candidate full-pack-to-24 V converters. The story plan now
starts with a 30-work cat-only pilot split into 5–7 and 8–10 presentation lanes.
No story blobs were downloaded.

The current English S2L v2.3 data sheet was retrieved through Slamtec's official
support page rather than depending on an unstable direct-download URL. It was
not installed or committed. The reviewed file's SHA-256 is:

```text
3e0432252f0b55ece4ba792de6e2eccaaff4a880d6c8545884a73f063d745bd2
```

It documents the 4.9–5.2 V supply window, no more than 150 mV ripple, 500 mA
typical/600 mA maximum running current, 1.5 A startup current, -10–50 C operation,
-20–60 C storage, typical +/-50 mm range accuracy, and bottom M3 screw depth no
greater than 4 mm. A 3 A local regulator is only integration margin, not a claim
that the lidar requires 3 A.

### Read-only validation after the update

The installed `jetson-diagnostic` snapshot and direct service probes observed:

- `multi-user.target` remained the default; GDM/display-manager was inactive,
  and no Xorg, GNOME Shell, or Firefox process was present;
- 5,415,284 KiB available of 7,665,092 KiB RAM, no swap, and 9% root-filesystem
  use at the sample point;
- hottest reported thermal zone 47.4 C, 15 W nvpmodel, 0% GR3D activity, and a
  4.556 W instantaneous `VDD_IN` sample;
- `neko-gemma.service` enabled and active with `READY` status, four CPU threads,
  loopback listener `127.0.0.1:9379`, about 1.2 GiB current/1.3 GiB peak service
  memory, and a successful `GET /v1/models` response.

This was a live warm-state check, not the still-pending real cold-reboot
acceptance. Unprivileged NvMap attribution remained unavailable.

Both the system Python and pinned ZipDepth export environment passed all 29 unit
tests. `git diff --check`, the internal relative-Markdown-link audit, and the
secret-signature scan passed. Of 41 newly added or changed external documentation
URLs, 37 returned HTTP 200; all three StoryWeaver pages and the DigiKey product
page returned HTTP 403 to the automated client. Their URLs were retained because
the block is bot protection rather than evidence of a missing page, and the
StoryWeaver references were separately reviewed through browser results.

## Installed model/service status

| Item | Disk state | Runnable | Configured/enabled |
| --- | --- | --- | --- |
| Gemma 4 E2B LiteRT | pinned source and managed copy verified; caches generated | bounded CPU text/audio API passes; prebuilt GPU backend crashes | enabled/active with readiness and limits; cold reboot pending |
| Gemma 4 E2B GGUF | official Q4_0 artifact and digest-pinned container verified | all-layer CUDA benchmark passed at 18.63 tokens/s | on-demand alternate only |
| Audex 2B | complete exact-revision snapshot and major hashes verified | no runtime; full path cannot fit unquantized | no |
| ZipDepth | source/checkpoints, locked export env, checked ONNX, FP32/FP16 plans and hashes verified | build, deterministic numerical gates, and model-only timing pass; camera/scene/combined gates pending | no; on-demand experiment only |
| ASR/Supertonic | exact isolated runtimes/models pinned | standalone EN/FR/ES smokes pass | on demand; no service |
| KittenTTS | 0.8.1 patched runtime plus exact Mini/Micro/Nano INT8 models | Micro/Kiki resident synthesis and PipeWire playback pass | `neko-tts.service` enabled/active; cold boot pending |
| Neko systemd units | Gemma and TTS source/installed units match | readiness/restart/API-or-PCM smokes pass | Gemma and TTS enabled/active; no cold reboot yet |

This table must be updated after every installation. “Enabled” states systemd
configuration only; “boot-validated” additionally requires a real reboot and
health/readiness validation.

## 2026-07-13 — Canadian one-week BOM and interaction-policy update

This was a research and documentation update only. No part was ordered, installed,
wired, configured, or powered; no package, model, service, firewall, camera,
network, or system setting changed.

The owner supplied or confirmed these controlling revision-one constraints:

- the four 270 Ah LiFePO4 traction batteries are connected in series, while exact
  labels, BMS rules, charge/loaded limits, interconnects, and protection remain
  unverified;
- added hardware must fit a CAD 2,000 landed cap including tax and shipping and
  arrive within one week; existing Jetson, storage, and C922 are excluded;
- the Jetson, cameras/radar, microphone, speaker, and transducer must remain at or
  below 200 W running, and speaker plus transducer ratings at or below 100 W;
- the roof underside is about 7 ft high with open sides, representative children
  are about 3.5–4.5 ft tall, and the one-week build must tolerate outdoor exposure;
- every story is no longer than five minutes and defaults to light/non-scary;
  `Neko Neko` is approved and `Hello Kitty` retired;
- LLM French/Spanish review is provisionally accepted only as a labelled lower-
  assurance prototype state with deterministic checks and local fallback; and
- optional cloud use is an authenticated-adult, text-only session through a
  separately billed API, never an embedded consumer credential or unattended
  child-cloud/media path.

The new controlling purchase record is
`docs/research/2026-07-13-canadian-one-week-bom.md`. It supersedes conflicting
US-dollar OAK/lidar and overseas audio purchase recommendations while preserving
their longer research and acceptance-test notes. `AGENTS.md` and
`docs/decisions/2026-07-13-owner-decisions.md` carry the durable summary.

The installed Vercel `find-skills` workflow was rerun for outdoor perception,
lidar/camera selection, robotics hardware, and BOM/procurement support. No
credible mature result covered this weather, geometry, Canadian-stock, and
one-week purchasing problem closely enough to install; no new skill or package
was added. The shared Codex/Claude Jetson skills and `find-skills` copies remain
at the paths recorded earlier in this log.

The revision-one recommendation is two opposing Reolink Duo 3V PoE outdoor
180-degree cameras, four DFRobot C4001 radar sectors, and the Canadian-stocked
Seeed reSpeaker USB four-mic/XVF3000, Soberton XPCB-12BT amplifier, Visaton FR 8
WP speaker, and protected Dayton TT25-8 puck. A roof-level planar 2D lidar is
deferred because it scans above the child-height band; an inverted hemispherical
3D lidar remains a later experiment.

Using the explicitly provisional British Columbia 5% GST plus 7% PST assumption,
the researched complete addition is CAD 1,144.60–1,364.60 landed. Its conservative
simultaneous planning allocation is 129 W, with a measured 200 W hard acceptance
cap and provisional 180 W software load-shedding threshold. Checkout destination,
stock, delivery date, exact camera power/network hardware, converter capacity,
mount geometry, weather assembly, and simultaneous power testing remain gates.

A final live distributor refresh found intraday inventory/price changes and the
documentation was recalculated rather than retaining the earlier scrape: OAK-D W
showed 32 units, the Soberton amplifier CAD 36.35/357 units, and the Visaton
speaker CAD 43.95/708 units. The opaque CAD 35.11 Hammond enclosure was linked
directly, and an out-of-stock 3 A fuse suffix was replaced with the in-stock
`0287003.H`. The 32 V fuse and holder are candidates only downstream of a verified
24 V rail, never on the 48 V pack side.

The owner-invited Claude Code reviewer was also attempted in read-only `plan`
mode using `/home/neko/.local/bin/claude` with only Read/Grep/Glob/WebSearch/
WebFetch tools. It emitted a connector-precedence warning and returned no review
after roughly two minutes, so it was interrupted rather than allowed to block the
work. Its `SessionEnd` hook then failed because
`/home/neko/.claude/helpers/hook-handler.cjs` is missing. It made no file or
system changes. A second, smaller `--safe-mode` local-only audit also produced no
result within one minute and was interrupted; safe mode avoided the broken hook
but did not resolve the provider stall. The independent Codex/subagent audits
continued normally.

The final independent documentation audit found and corrected four issues: the
shared 24 V lights would have polluted the scoped 200 W measurement, one current
audio criterion still said 4 ohms instead of the selected 8 ohms, an OAK/RVC2
implementation section needed an explicit historical label, and the procurement
claim needed to remain conditional on checkout ETA. The accepted power test now
isolates non-Neko 24 V loads or uses a dedicated metered Neko sub-feed plus
measured incremental conversion loss; lights-on operation is a separate shared-
rail interference test.

Post-edit validation:

- all 29 unit tests passed under system Python;
- all 29 unit tests passed under the pinned ZipDepth export environment;
- `git diff --check`, the internal relative-Markdown-link audit, the BOM
  arithmetic reproduction, and a credential-signature scan passed;
- all ten primary/vendor pages that permit automated checks returned HTTP 200;
  RobotShop and DigiKey returned bot-protection HTTP 403, the Unitree/RoboSense
  stores rate-limited at HTTP 429, and Best Buy/Mouser rejected or timed out in
  `curl`; the latter distributor pages were independently opened through the
  browser research path and supplied the recorded live stock/price evidence.

## 2026-07-13 — converter safety, cart geometry, and direct-DC network refresh

This was a read-only physical-design research pass plus repository documentation
edits. No hardware was ordered, opened, rewired, disconnected, configured or
powered. No package, model, service, firewall or operating-system setting changed.

### New owner facts

- Destination: owner-supplied British Columbia delivery region; every critical line must
  still show checkout arrival within seven days.
- Both installed adjustable modules are described by the marketplace title
  `[2 Pack] DC-DC 5A Buck Converter 4-38V to 1.25-36V Step-Down Voltage
  Regulator High Power Module with LED Display`. Each is advertised as 4–38 V
  input and 5 A, with one set to 24 V and one to 19 V.
- Reported present loads are approximately 1–2 A on the lighting output and
  approximately 1 A on the Jetson output. Their exact input connections are
  still unknown: complete string, two-battery midpoint or another regulated rail.
- Camera cable style is secondary to power. The Jetson has one onboard Ethernet
  port; an additional USB NIC is possible but not preferred.
- Proactive greeting is parked-only, with an interaction radius no greater than
  10 ft.
- Intended ambient is 0–40 C, no salt, possible moisture/rain/dirt, key
  components sheltered from direct rain, and cloth cleaning only.
- One voice speaker is sufficient. French is the second language priority and
  Spanish the third.
- Age-appropriate conflict and reviewed folklore/religion are allowed in the
  light/non-scary five-minute story policy; serious grief and extreme bathroom
  humour are excluded.
- Adult mode may use a physical key/button or authenticated remote enablement.
  The documented design treats a keyed switch or locked-compartment control as
  local authentication; a plain exposed button alone is not authentication.

### Immediate converter finding

A nominal 48 V source already exceeds the modules' advertised 38 V maximum.
Changing their outputs to 19 or 24 V and observing modest load current cannot
make their inputs safe. If four conventional 12.8 V LiFePO4 batteries were used,
the illustrative string values would be roughly 51.2 V nominal and 58.4 V at
14.6 V per battery, but battery labels and charger/BMS configuration—not this
example—control Neko's design.

The modules are therefore prohibited across the full series string. A
two-battery midpoint is not an alternative because unequal accessory draw
unbalances the series bank. Both inputs must be traced and isolated before
further operation. A matching marketplace page showed the same 4–38 V,
1.25–36 V and 5 A claims but no manufacturer-grade continuous/thermal,
isolation, ingress or protection data; its “5 A” was not accepted as a field
continuous rating. No attempt was made to inspect or alter the live wiring.

### Conditional replacement research

The controlling candidate architecture, still gated on battery labels, maximum
charge/transient voltage, BMS rules and qualified pack-side protection, is:

```text
complete pack output
  -> protected Mean Well DDR-240C-24 -> fused 24 V lights/audio/radar domain
  -> protected Mean Well RSD-60L-12 -> dedicated 12 V Jetson barrel input
  -> protected Mean Well DDR-60L-12 -> two fused camera runs + SW-005

Jetson onboard Ethernet -> Brainboxes SW-005 -> both cameras
Jetson Wi-Fi -> optional policy-controlled Internet uplink
```

Current evidence recorded in the BOM:

| Candidate | Manufacturer facts | Canadian price/stock observed |
| --- | --- | --- |
| Mean Well `DDR-240C-24` | 33.6–67.2 V input, 24 V/10 A/240 W, 91% typical, 4 kV DC isolation, remote on/off/DC-OK, -40–70 C with derating; no outdoor IP rating | Mouser CAD 145.01, 130 able to ship immediately |
| Mean Well `RSD-60L-12` | 18–72 V input, 12 V/5 A/60 W, 93% typical, 4 kV isolation, full output through 55 C; no outdoor IP rating or remote enable | Mouser CAD 61.34, 906 able to ship immediately |
| Mean Well `DDR-60L-12` | 18–75 V input, 12 V/5 A/60 W, 91% typical, 4 kV isolation; protected-bay device | DigiKey CAD 49.96, 662 stocked |
| Brainboxes `SW-005` | Five 10/100 ports, 5–30 V input, 1.1 W maximum, -10–60 C, IP30 | DigiKey CAD 81.31, 616 stocked |

The four core lines total CAD 337.62 before tax/CAD 378.13 at the assumed 12%
BC rate. With the existing camera/radar/audio/transducer lines and a revised
CAD 250–450 protection/weather/mechanical allowance, the complete planning range
is CAD 1,522.73–1,742.73, leaving CAD 257.27–477.27 below the CAD 2,000 ceiling.
The pack-side simultaneous planning allocation is now 135 W; the measured Neko-
only acceptance cap remains 200 W and lights remain a separate coexistence test.

The direct camera path is approximately 25.1 W downstream at both camera
nameplates plus the switch maximum, or about 27.6 W at the pack using the
DDR-60L-12's published 91% typical efficiency before wiring loss. A Teltonika
TSW101 plus DDR-60L-24 active-PoE fallback was recorded at approximately
CAD 201.05 taxed and roughly 1 W higher; passive PoE is prohibited. A retained
StarTech USB NIC is the cheaper fallback, but vibration, USB autosuspend/device
ordering and split-subnet complexity make it less reliable than the switch.

The Jetson carrier-board specification permits 9–20 V on its center-positive
5.5 x 2.5 mm DC jack and limits it to 3.5 A, so a dedicated documented 12 V
supply is valid. The same official specification rates the developer kit only
0–35 C. The requested 35–40 C ambient band therefore requires monitored worker
shedding and orderly shutdown unless an industrial thermal platform replaces the
developer kit; fans cannot make enclosure ambient colder than outdoor ambient.

### Cart-photo privacy and geometry

The owner-provided Drive image was downloaded to a temporary path only after the
web viewer failed, visually inspected, and deleted in the same work session. It
showed identifiable people and contained embedded location metadata.
No coordinates were read into project notes, and neither the image nor its raw
link was committed.

The side/rear view shows many posts/slats and occupied seats under the solar
roof. Cameras or radars inside that plane would be strongly occluded. The plan
now places front/rear panorama optical faces a few centimetres below and outside
the post plane on short structural roof-frame brackets, and all four radar faces
outside the slats in RF-tested pods. Nothing mounts to solar panels/panel glass
or the LED strip. Complete empty and occupied front/rear/both-side survey images
or a dimensioned drawing remain required before drilling.

The C4001's documented ranging floor is about 1.2 m/4 ft, so revision-one spoken
greeting begins with camera-confirmed approach/dwell in the approximate 4–10 ft
annulus. Inside about 4 ft, the policy suppresses repeat solicitation and retains
the `Neko Neko`/camera interaction path. Proactive greeting is parked-only.

### Evidence and privacy handling

Primary technical evidence was refreshed from current Mean Well data sheets and
installation instructions, NVIDIA's carrier-board specification, Reolink's
camera/power documentation, Brainboxes specifications, DFRobot documentation,
and the already-recorded Victron series-bank guidance. Canadian price/stock came
from Mouser and DigiKey product pages. Exact links are in the controlling BOM and
power/weather notes. Checkout arrival to the owner-supplied destination could not be guaranteed
without entering the cart/checkout flow, so no seven-day delivery claim was made.

The temporary image path `/tmp/neko-cart-drive` was removed and verified absent.
Repository policy remains: never commit raw owner/bystander media, recordings,
transcripts, street addresses, GPS coordinates, embedded media-location metadata,
credentials or model weights. The exact owner-supplied postal code was removed
before public-release preparation; it is not required for durable research notes.

### Final electrical/document consistency review

Independent read-only audits caught several integration details before commit:

- Mean Well publishes typical input inrush of 30 A for the DDR-240C-24 and 20 A
  for each 60 W candidate. If applied together, the pulses could briefly approach
  70 A. The 200 W requirement is now explicitly the post-start running cap;
  startup has a separate sequencing/precharge or limiting, oscilloscope/current-
  probe, BMS, switching, conductor, and fuse time-current acceptance gate.
- The DDR-240 installation manual requires vertical input-down mounting, dry
  Pollution Degree 2 conditions, and FG connected to PE. The RSD-60 also exposes
  FG. Because a mobile cart chassis is not automatically PE, the candidate now
  remains blocked on a qualified manufacturer-compliant bonding/fault-clearing
  design or replacement.
- The Soberton amplifier accepts no more than 25 V, while the DDR-240 adjusts to
  28 V and does not begin its own overvoltage shutdown until 28.8 V. A fuse and a
  nominal 24 V label are insufficient. The BOM now requires a selected regulated
  downstream audio supply with coordinated OVP, or a wider-margin amplifier.
- The still-unselected protected 24-to-5 V radar/aggregator stage and isolated
  runtime power-measurement path are explicit BOM gates. The 34 W reserve now
  means all conversion loss, controls, and unallocated measurement contingency,
  rather than a claimed measured value.
- Those added safety/integration items widened the unpriced installation
  allowance from CAD 250–450 to CAD 350–650. The current range remains provisional
  rather than evidence-backed. Applying the full 12% planning tax
  conservatively to the estimated Solen shipping produces CAD
  1,625.13–1,947.53, leaving only CAD 52.47–374.87 under the fixed ceiling. The
  earlier ranges in this same chronological entry are superseded; checkout and
  itemized safety lines still control budget compliance.
- The adjustable camera converter must be set/tamper-marked at 12.0 V and checked
  at both cameras under load; the SW-005 gets its own protected output branch.
- The current generic 24 V converter was removed from a skimmable historical
  audio recommendation, one obsolete US-dollar budget statement was relabelled,
  and story acceptance is duration-based at no more than 300 seconds.
- Displayed taxed line items are rounded individually, while controlling order
  totals tax the unrounded subtotals; a one-cent display-sum difference is now
  documented.

### Post-edit validation

- All 29 unit tests passed under system Python, and all 29 passed again under
  `/home/neko/models/ZipDepth/export-env`.
- `git diff --check`, all internal relative Markdown targets, the revised BOM/
  headroom/135 W arithmetic, a credential-signature scan, and a raw-photo-link/
  coordinate-pattern scan passed.
- The default boot target remains `multi-user.target`; the display manager is
  inactive, and exact process-name checks found no Xorg, GNOME Shell, or Firefox.
- `neko-gemma.service` remains enabled and active with zero restarts. Its
  loopback-only `/v1/models` endpoint returned only `gemma-4-e2b-it`, and a
  bounded chat request returned exactly `meow`. No service setting was changed.

## 2026-07-13 — supplied power-interface scope correction

The owner clarified that this project is recommending hardware, not designing or
approving the cart's upstream wiring. The controlling interfaces are now:

- regulated 24 V, up to 3 A; existing lights draw 1–2 A;
- regulated 19 V, up to 3 A; the Jetson currently draws about 1 A; and
- 12–14 V, up to 20 A, for accessories.

Battery labels, BMS/charger details, a wiring diagram, generic-converter input
tracing, full-pack protection, grounding, fusing, disconnect design, and upstream
wiring are owner scope and no longer block hardware recommendations. The owner
also approved orderly optional-worker shedding and shutdown at 35 C. Earlier
full-pack analysis is preserved as chronological research but labelled
superseded in current guidance.

### Revised downstream hardware recommendation

Current manufacturer and Canadian distributor evidence was refreshed on
2026-07-13:

| Item | Current role and evidence | Price/stock observed |
| --- | --- | --- |
| RECOM `REC30K-2412SZ` | Feed from 12–14 V; nominal 12 V/2.5 A/30 W for both Reolink cameras; 9–36 V input, 88% typical full-load efficiency at nominal input, 20 ms typical/50 ms maximum startup, silicone-potted aluminium case, and MIL-STD-810F shock/vibration claims | DigiKey CAD 36.29, 141 stocked |
| RECOM `R-78B5.0-2.0` | Feed from 12–14 V; 5 V/2 A/10 W for four C4001 radars and their aggregator; 6.5–32 V input, published full-load efficiency of 94% at minimum input/90% at maximum input, 2 A typical inrush and 10 ms typical startup at the stated nominal-input test condition, silicone potting, and 2 G vibration qualification; those startup figures are not maximums at 12–14 V | DigiKey CAD 18.72, 5,943 stocked |
| Brainboxes `SW-005` | Feed directly from 12–14 V; five 10/100 ports, 5–30 V input, 1.1 W maximum | DigiKey CAD 81.31, previously observed 616 stocked |
| Soberton `XPCB-12BT` | Feed directly from 12–14 V; official board range is 10–25 V | Existing selected DigiKey line |

The Jetson remains directly on regulated 19 V. The 24 V interface carries only
the existing lights. Cameras are not powered directly from 12–14 V because
Reolink specifies 12.0 V rather than a 12–14 V range. Both new converter modules,
the SW-005 and Soberton instead use the higher-current 12–14 V interface.

The originally considered Mean Well RSD pair was rejected as the primary path
after checking startup: both data sheets publish 20 A typical inrush at 24 V.
That is a poor fit beside lights on a 24 V/3 A interface, and the RSD-60's value
at 12–14 V is not specified. The REC30K does not publish a separate capacitive-
inrush maximum, so its 20–50 ms startup figure is not a soft-start guarantee. The
R-78B's 2 A inrush and 10 ms startup values are typical at the stated nominal-
input condition, not maximums at 12–14 V. Repeated cold-start tests remain an
acceptance gate. Both active RECOM parts are board-level modules and require
mechanically supported carriers with retained connections in protected space.

Soberton's 2 x 25 W claim is at 20 V and 10% THD. The underlying TDA7492P
specifies 7.2 W per 8-ohm channel at 12 V/1% THD and 9.5 W at 10% THD. The
12–14 V choice therefore safely de-rates the two 15 W drivers but needs an actual
SPL/vibration bench test. Target about 7 W clean per channel at 12 V, treat
8–10 W as a 14 V bench target rather than a guarantee, and never exceed either
15 W driver.

### Revised rail and budget arithmetic

The deliberately conservative interface allocation remains 135 W:

```text
19 V: Jetson/NVMe/cooling, USB mic/data, reserve          45 W / 2.37 A
24 V: no new Neko load; existing lights only               0 W new load
12-14 V: cameras/network, radar/control, audio, reserve    90 W / 7.50 A at 12 V
--------------------------------------------------------------------------
Neko simultaneous supplied-interface planning total     135 W
```

At the reported 2 A maximum lighting load, the 24 V/3 A interface retains 1 A of
stated headroom because Neko adds no new load there. Neko retains 65 W of planning
margin below its required, to-be-measured 200 W running cap.

The active REC30K, R-78B and SW-005 lines total CAD 136.32 pre-tax/CAD 152.68
after assumed 12% BC tax. Retaining the conservative CAD 350–650 weather,
mounting, cable, downstream-protection, and fabrication allowance yields:

```text
provisional landed hardware addition     CAD 1,399.68..1,722.08
headroom below CAD 2,000                  CAD   277.92..600.32
```

No part was ordered, installed, wired, disconnected, or powered during this
scope correction. No package, service, model, firewall, or operating-system state
was changed.

### Post-correction validation

- System Python and the pinned ZipDepth export environment each passed all 29
  unit tests.
- `git diff --check` passed. The CommonMark parser accepted all eight changed
  Markdown files without literal unmatched emphasis markers. An internal-link
  audit covered 23 Markdown files and 56 relative links with no missing or
  repository-escaping target.
- Independent arithmetic reproduced CAD 136.32 pre-tax/CAD 152.68 taxed for the
  active REC30K/R-78B/SW-005 lines, CAD 1,399.68–1,722.08 for the provisional
  landed build, CAD 277.92–600.32 headroom, and 45 + 0 + 90 = 135 W with 65 W
  below the required 200 W acceptance limit.
- Credential-signature, raw private-photo link/identifier, and tracked-media
  scans were clean. The exact owner-provided postal code has since been removed
  for public-release preparation.
- Headless state still matched the recorded configuration: `multi-user.target`,
  inactive display manager, and no exact Xorg, GNOME Shell, or Firefox process.
  `neko-gemma.service` remained enabled/active with zero restarts; its loopback
  model list contained only `gemma-4-e2b-it`, and a bounded health prompt returned
  exactly `meow`.

These checks were read-only except for the bounded local inference request. They
did not change any service setting, package, model, network rule, or hardware.

## 2026-07-14 — pre-hardware USB camera/audio and Gemma smoke path

The owner reported that the production parts were ordered and authorized using
on-hand USB equipment before they arrive. No new package, model, service, system
unit, or boot setting was installed or changed. The existing host tools used by
the new harness were:

```text
Python 3.12.3
GStreamer 1.24.2
ALSA arecord/aplay 1.2.9
PipeWire client/library 1.0.5
```

Added `scripts/smoke_test_devices.py`, its standard-library unit tests, and
`docs/operations/2026-07-14-pre-hardware-smoke-tests.md`. The harness enumerates
V4L2, ALSA and PipeWire endpoints, runs synthetic audio/video, decodes live UVC
frames to ZipDepth's `672x384 RGB` geometry, measures 16 kHz mono microphone RMS,
and calls the fixed loopback Gemma API. Camera and microphone streams end at
GStreamer `fakesink`; playback requires an explicit flag/command and is capped at
0.1 software amplitude. The harness never retains media by default.

The first C922 video run exposed a real compatibility issue: generic `decodebin`
selected Jetson `nvjpegdec` for the camera's default MJPEG output and the pipeline
failed negotiation. The final test path pins the C922's supported uncompressed
`640x360 YUY2 @ 30 fps` source, centre-crops to 7:4, then performs colour
conversion and resize. Validations:

```text
synthetic: 60 video/audio buffers, pass
C922 camera: 60 frames in 2.866 s, 20.94 wall fps, pass
C922 camera longer run: 180 frames in 12.647 s, 14.23 wall fps, pass
C922 microphone: 3.024 s, 27 level samples, -44.43..-32.38 dBFS, pass
combined safe suite: synthetic + 60 camera frames + 29 mic samples + Gemma, pass
combined Gemma persona response: 2.177 s, pass
audible USB playback: not run; no USB playback peripheral was connected
media/results retained: none
```

The camera rate includes process/device setup and teardown and varied materially;
it is an integration observation, not an accepted real-time rate or a proxy for
Reolink RTSP latency. The temporary C922/headphone path cannot accept production
AEC, far-field, panoramic coverage, radar, amplifier, SPL/vibration, ingress,
power, or thermal requirements. Rollback is only removal of the added script,
test, runbook, and corresponding documentation entries; host runtime state is
unchanged.

Final repository validation passed 38 system-Python unit tests, Python
byte-compilation, `git diff --check`, and an internal Markdown-link audit. A
deliberately missing explicit
playback selector failed closed with exit status 1. The post-crop live C922 path
also passed 30 frames without retaining media, and a final one-second C922
microphone run produced seven RMS samples without retaining audio. Gemma remained
active with zero service restarts. Re-run the full unit suite after any
subsequent edit.

## 2026-07-14 — temporary Ora GQ Bluetooth headset

The owner put an unidentified headset into pairing mode and authorized pairing.
A 20-second scan found one unambiguous audio-headphone candidate, `Ora GQ
Headphone`, advertising A2DP Audio Sink plus headset/hands-free services. The
device's unique Bluetooth address is omitted from committed documentation. The
equivalent commands were:

```bash
bluetoothctl --timeout 20 scan on
bluetoothctl info <headphone-address>
bluetoothctl pairable on
bluetoothctl --timeout 35 pair <headphone-address>
bluetoothctl trust <headphone-address>
bluetoothctl connect <headphone-address>
bluetoothctl pairable off
```

Pairing produced a bonded, trusted connection. After one spontaneous disconnect
during profile inspection, an explicit reconnect succeeded. The controller was
left powered, non-discoverable, non-pairable, and not scanning. PipeWire 1.0.5 /
WirePlumber 0.4.17 created an Ora sink and source and selected the
`headset-head-unit-msbc` HSP/HFP profile. The owner reported that it was working.
No controlled PCM tone was played and A2DP did not appear in the current
PipeWire profile enumeration, so high-quality playback remains an investigation,
not a passed gate. The C922 remains available as the higher-quality temporary
capture source.

No package, service, global PipeWire/WirePlumber setting, or boot setting was
changed. To undo the persistent device state, run `bluetoothctl remove
<headphone-address>` while the adapter is available. Pairing can be repeated from
the same procedure if needed.

## 2026-07-14 — conversation/proximity integration readiness audit

Ran the installed Jetson memory-audit and inference-memory-tuning skills before
selecting a combined audio/vision sequence. The audit was read-only; its temporary
JSON was deleted after summarization:

```text
board/profile: Orin Nano 8 GB, L4T R39.2, 15 W
RAM total: 7,665,220 KiB
RAM available: 6,065,396 KiB
RAM free: 3,141,236 KiB
cache: 2,955,248 KiB
swap: none
leading process: deployed Gemma Python service, 1,669,854 KiB PSS
quiet sample: 1,435/7,486 MB RAM, GPU 0%, about 4.50 W, hottest zone 46.16 C
NvMap per-process attribution: unavailable without privileged debugfs
```

The generic tuner recommended llama.cpp Q4 with `-ngl 28 -c 4096 --no-mmap` as
the lowest-memory new LLM server. That did not supersede the project's already
measured CPU LiteRT service: retaining LiteRT avoids an unnecessary runtime
change and reserves GPU capacity for the first detector/ZipDepth experiments.

Refreshed official sources for NVIDIA Nemotron 3.5 streaming ASR, sherpa-onnx's
June 11 INT8 exports, Supertonic 3, Pipecat, openWakeWord, RF-DETR, Ultralytics
YOLO26/TensorRT, and current Ultralytics licensing. The resulting architecture,
source URLs, model sizes, licensing boundary, ground-plane calibration method,
service order, and gates are in
`docs/plan/2026-07-14-conversation-proximity-mvp.md`.

No ASR, TTS, Pipecat, wake-word, detector, tracker, model weight, service, or
system package was installed in this step. Rollback is removal of the new plan
and its documentation-map/conclusion/changelog entries; host state is unchanged.

## 2026-07-14 — local streaming ASR installation and benchmark

Installed sherpa-onnx 1.13.4 into the dedicated user environment
`/home/neko/.local/share/neko/venvs/asr`; no system Python package changed. The
source input and generated ARM64/hash-locked dependency set are
`deploy/requirements/neko-asr.in` and `neko-asr.lock`. The installed ARM64
sherpa wheels were 1.13.4; the selected wheel hashes are
`f709e6dd02ebf7d37dcb02d5eadc5fb66c9922dd5809df770c1ef5d625ae7a44`
for `sherpa-onnx` and
`b4e4d17eb0d5c569bf4c9effcbc3daef57cf7e2b8418e07ae90f90c9b60b35d5`
for `sherpa-onnx-core`. sherpa-onnx is Apache-2.0.

Downloaded the official k2-fsa June 11, 2026 Nemotron 3.5 0.6B 560 ms INT8
streaming bundle to `/home/neko/models/sherpa-onnx-nemotron`. The archive is
475,271,763 bytes with SHA-256
`c6bf5e0df765f9d5b43bc9e0536d4b4b3e7d40bdf5ecf13e45f134c51c05ae3a`.
The archive path list was checked for absolute and parent-traversal paths before
extraction. Extracted model files include a 657,601,403-byte INT8 encoder,
14,978,075-byte decoder, 9,504,438-byte joiner, and 131,440-byte token table.
The archive only links its source model and does not map itself to an exact
Hugging Face commit; that is a provenance gap. NVIDIA's source weights are
OpenMDW-1.1, not Apache-2.0.

Exact installation/download commands were:

```bash
/home/neko/.local/bin/uv venv --python /usr/bin/python3 \
  /home/neko/.local/share/neko/venvs/asr
/home/neko/.local/bin/uv pip install \
  --python /home/neko/.local/share/neko/venvs/asr/bin/python \
  'sherpa-onnx==1.13.4'
curl --fail --location --continue-at - --output \
  /home/neko/models/sherpa-onnx-nemotron/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-560ms-int8-2026-06-11.tar.bz2 \
  https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-560ms-int8-2026-06-11.tar.bz2
```

With four CPU threads and the deployed Gemma service still resident, cold ASR
construction took 3.533 s. The bundled 22.05 kHz French clip decoded in 1.952 s
for 4.969 s of audio (RTF 0.393); Spanish decoded in 2.036 s for 5.329 s (RTF
0.382). Peak process `ru_maxrss` was 1,414,756 KiB. Both produced intelligible
language-correct transcripts, with small word/punctuation errors. These are
publisher clips, not a C922 accuracy acceptance set.

Added `scripts/neko_asr_transcribe.py`. A bounded live ALSA capture is raw PCM
held only in process memory and never written to disk; file and microphone runs
emit timing plus the final text. No ASR service is enabled. Complete rollback:
remove `/home/neko/.local/share/neko/venvs/asr` and
`/home/neko/models/sherpa-onnx-nemotron`, then remove the two ASR requirement
files and integration script if reverting project code.

## 2026-07-14 — Supertonic 3 local TTS installation and benchmark

Installed `supertonic==1.3.1` into
`/home/neko/.local/share/neko/venvs/tts`. The exact source/tag commit is
`908a56486e821e833a80530ff0cae3ad0b046fce`; its universal wheel is 51,871
bytes with SHA-256
`0079c9d4166008b8a6eeae95f20c092148786b7232192dd3dd9f358960c6c077`.
The SDK code is MIT. The generated ARM64/hash-locked dependency set is recorded
in `deploy/requirements/neko-tts.in` and `neko-tts.lock`; notable installed
packages are ONNX Runtime 1.27.0, NumPy 2.5.1, SoundFile 0.14.0, and Hugging Face
Hub 1.23.0.

The SDK downloaded `Supertone/supertonic-3` at its internally pinned revision
`724fb5abbf5502583fb520898d45929e62f02c0b` to
`/home/neko/models/supertonic-3`. The four major ONNX SHA-256 values are:

```text
duration_predictor  c3eb91414d5ff8a7a239b7fe9e34e7e2bf8a8140d8375ffb14718b1c639325db
text_encoder        c7befd5ea8c3119769e8a6c1486c4edc6a3bc8365c67621c881bbb774b9902ff
vector_estimator    883ac868ea0275ef0e991524dc64f16b3c0376efd7c320af6b53f5b780d7c61c
vocoder             085de76dd8e8d5836d6ca66826601f615939218f90e519f70ee8a36ed2a4c4ba
```

The weights are BigScience OpenRAIL-M and are not relicensed by the repository.
With four intra-op threads, one inter-op thread, F1 voice, six synthesis steps,
and Gemma resident, model load took 1.406 s and peak process `ru_maxrss` was
503,752 KiB. English produced 3.831 s of audio in 2.538 s (RTF 0.662), French
4.807 s in 3.239 s (RTF 0.674), and Spanish 4.319 s in 2.830 s (RTF 0.655).
Outputs were generated in memory for timing and were not retained or auditioned;
voice/persona quality remains an owner acceptance test.

Added `neko/gemma_client.py` and `scripts/neko_text_conversation.py`. The latter
routes typed wake/session events through the fixed loopback Gemma service and
can opt in to transient Supertonic WAV generation and local playback. Its normal
test does not save a transcript or audio. A real local request, `Neko Neko,
introduce yourself in one short sentence`, passed and returned an in-persona
one-sentence reply. No TTS or conversation service is boot-enabled. Complete
runtime rollback is removal of `/home/neko/.local/share/neko/venvs/tts` and
`/home/neko/models/supertonic-3`; remove the TTS lock/input and integration files
only when reverting source changes.

## 2026-07-14 — Claude review retries

Two read-only Claude Code review attempts were made with the absolute executable
`/home/neko/.local/bin/claude`. Both reached the configured z.ai gateway and
failed with HTTP 529 overload before producing review findings. Both also
reproduced the previously known broken local `SessionEnd` hook fallback to
`/home/neko/.claude/helpers/hook-handler.cjs`. Claude made no edits. Dependency
research and implementation review therefore used local tests, official-source
checks, and a separate read-only Codex sub-agent; do not attribute findings to
Claude for this run.

## 2026-07-14 — detector comparison, camera worker, and combined smoke

Installed two export-only environments without modifying system Python:

```text
/home/neko/.local/share/neko/venvs/rfdetr-export  RF-DETR 1.8.3
/home/neko/.local/share/neko/venvs/yolo26-export  Ultralytics 8.4.95
```

Their exact dependency inputs and ARM64/hash-locked resolutions are in
`deploy/requirements/rfdetr-export.in`, `rfdetr-export.lock`,
`yolo26-export.in`, and `yolo26-export.lock`. RF-DETR tag 1.8.3 resolves to
commit `3bd6bffbcb13cac3a5b1c37da5a0fd5453b50c86`; Ultralytics tag v8.4.95
resolves to `de2f6061c7efd65c33b0fc41c2f6c2af87a7044a`. The generic torchvision
ARM64 wheel attempted to resolve CUDA packages, so both isolated environments
use the official CPU wheel for torchvision 0.27.1 with CPU torch 2.12.1 during
export only. Neither export environment is a boot dependency.

RF-DETR Nano artifacts are under `/home/neko/models/rfdetr-nano`:

```text
rf-detr-nano.pth                         d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d
export-384/rfdetr-nano.onnx              c71a399cf163eb212a9a8e7831c1409014887bd25f71528c76b7275e21e12304
export-384/rfdetr-nano-b1-384-fp16.plan  4b61a08b03cc63889ec590414c3b4d5fef696b4da33ede6bfb2b675a7b656c00
```

The checkpoint is 350 MiB, ONNX is 115,276,721 bytes, and the TensorRT plan is
57 MiB. Export reported an absent `_kp_active_mask` key and initialized that
keypoint-only value; detection outputs still require a larger field-quality set
before acceptance. The locally built TensorRT 10.16.2 engine has static FP32 I/O
`input (1,3,384,384)`, `dets (1,300,4)`, and `labels (1,300,91)`. FP16 build took
190.20 s. It measured 9.478 ms model-only (105.48 qps) and 9.631 ms including
synthetic host transfers. A live C922 PyTorch reference run detected one person
at 0.898 confidence; the transient frame was not retained.

YOLO26n external comparison artifacts are under `/home/neko/models/yolo26`:

```text
yolo26n.pt                     9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef
yolo26n-b1-384-fp16.plan       13087e69c4fb61d092c04c066b4784b140fd5b27830479c45aa16dcd8b65ef95
```

The 7.4 MiB FP16 plan built in 401.57 s and measured 3.191 ms model-only and
3.367 ms with transfers. This speed advantage is unnecessary at Neko's bounded
5–10 fps and does not outweigh licensing. Ultralytics states that its code and
models are AGPL-3.0 unless an Enterprise licence applies; making the Neko GitHub
repository public and MIT does not relicense an integrated YOLO dependency.
YOLO26 remains an uncommitted, external lab artifact and must not be imported by
the Neko runtime or represented as MIT.

Added `neko/rfdetr.py`, `neko/tensorrt_engine.py`, and
`scripts/neko_camera_proximity.py`. The camera loop verifies the exact board-
built engine hash before loading, decodes C922 YUY2 to RGB through GStreamer,
matches RF-DETR's bilinear/ImageNet preprocessing, runs at a bounded requested
rate, tracks only centroids in memory, and emits JSON metadata. It never writes
a frame. Metric distance remains `null` unless explicit measured camera
calibration points are supplied; therefore the spoken-greeting distance gate
fails closed until the production camera poses are calibrated.

The first live TensorRT loop ran for eight seconds at 5 Hz. No person occupied
the current view; the maximum person confidence was 0.087, while the most likely
non-person class scored 0.673. This is a valid empty-scene smoke, not a positive
quality set. The prior live PyTorch result supplies the positive C922 semantic
check.

The first memory-only live ASR attempt exposed two integration errors: the ALSA
card short name is `Webcam`, not the earlier assumed `C922`, and this arecord
version accepts `--file-type`, not `--type`. The script now reports capture
stderr clearly. A five-second C922 capture then passed, decoded an intentionally
silent interval at RTF 0.386, produced an empty transcript, and retained no
audio. A concurrent run kept the deployed Gemma service, 5 Hz RF-DETR camera
worker, and four-thread Nemotron ASR active together. `tegrastats` observed a
peak of 3,618/7,486 MB RAM, 8.266 W input, and 48.718 C. ASR remained RTF 0.399;
the detector loop completed normally. This is a short bench result, not the
required thermal/power soak or production-device acceptance.

All 63 system-Python unit tests passed, including RF-DETR preprocessing/decoding,
ephemeral tracking, social policy, Gemma, ASR helpers, device smoke tests, and
ZipDepth export/validation logic. Python byte-compilation and `git diff --check`
also passed. No new systemd unit was installed or enabled. Complete runtime
rollback is removal of the two export venvs and `/home/neko/models/rfdetr-nano`
plus `/home/neko/models/yolo26`; source rollback removes the corresponding
requirements, RF-DETR/runtime modules, camera script, tests, and these notes.

## 2026-07-14 — MIT public release

Committed the complete local conversation/proximity bench as `7cac2be`, pushed
`agent/local-conversation-proximity`, opened GitHub PR 2, and merged it to
`main` as `ae63d3b6cee10b0f82467d5cecdaaa55f3e300a6`:

<https://github.com/liamhelmer/nekokitty/pull/2>

The PR was mergeable and GitHub reported no configured checks; the local 63-test
and integration gates above were therefore controlling. After merge, changed
`liamhelmer/nekokitty` visibility from private to public. Both authenticated
GitHub metadata and an unauthenticated request to
`https://api.github.com/repos/liamhelmer/nekokitty` reported `private: false`,
default branch `main`, and SPDX licence `MIT`.

Before publication, scans found no current-tree credential signatures, raw
media, model/engine files, or tracked blob larger than 5 MB. The exact delivery
postal code was removed from the current tree. It remains in an older Git commit;
the owner explicitly authorized public release and the history was deliberately
preserved rather than destructively rewritten. Rollback of repository visibility
is `gh repo edit liamhelmer/nekokitty --visibility private`; that does not retract
copies already fetched while public. Reverting the merge is a separate Git
operation and does not remove the external NVMe model/runtime artifacts.

## 2026-07-16 — C922/Ora hardware-in-the-loop continuation

No package, model, systemd unit, boot target, audio daemon setting, or Bluetooth
pairing state was added or changed. All camera/audio captures remained in memory;
no raw frame, image, audio file, or video was retained. The Ora Bluetooth address
is deliberately omitted.

The read-only Jetson diagnostic baseline reported 5,570,724 KiB available of
7,665,220 KiB, no swap, 15 W mode, 46.8 C hottest reported zone, and a 4.534–
4.807 W `VDD_IN` sample. Gemma remained active. The safe combined command was:

```bash
python3 scripts/smoke_test_devices.py all \
  --camera-match C922 \
  --capture-match Webcam \
  --frames 90 \
  --duration 5
```

It passed synthetic processing, 90 C922 frames at 25.79 wall fps, 49 webcam-mic
level samples (-41.31 to -26.98 dBFS), and Gemma in 2.739 s. Gemma replied:
`Mrow! Hello there, little one! Do you like cats?`

The first positive `scripts/neko_camera_proximity.py` run exposed an
`AttributeError`: the serializer requested `PersonObservation.bottom_y_normalized`
although only the detector-side track carried it. `PersonObservation` now carries
that optional, ephemeral, non-image field and `ProximityEstimator` populates it;
the serializer handles `None`. After targeted tests, the repeated 18-second,
5 Hz, threshold-0.60 TensorRT run held one anonymous `person-1` track for the
whole run at 0.926–0.969 confidence. Its box bottom was 0.995–1.000 normalized,
so the temporary pose was too close/cropped for calibration. With no calibration
argument, distance stayed `null` and approach stayed false as required.

Ora was the default PipeWire mSBC sink/source. A two-second low-volume 523.25 Hz
tone was sent through `pipewiresink` after temporarily lowering the sink to 30%;
the bounded timeout ended the continuous source as expected, and the prior 67%
sink volume was restored. A six-second non-retaining
`pipewiresrc` level run returned 59 samples, a -31.83 dBFS maximum, and no stream
error. The full deterministic text path also passed:

```bash
python3 scripts/neko_text_conversation.py \
  --utterance "Neko Neko, say hello and ask whether I want to hear a cat story, in one short sentence." \
  --language en \
  --speak \
  --voice F1
```

It produced the local acknowledgement, a short Gemma reply, transient
Supertonic synthesis, and PipeWire playback; the temporary WAV was deleted when
the command exited.

`scripts/neko_asr_transcribe.py` now supports `--pipewire-seconds` and optional
`--pipewire-target`. It runs `/usr/bin/pw-record` in its own process group,
requests 16 kHz mono signed-16 PCM, bounds capture with SIGINT, checks the
observed PipeWire 1.0.5 clean-interrupt contract, validates/minimum-bounds/trims
PCM, and never writes it. It also reports privacy-safe whole-buffer RMS and peak
dBFS. PipeWire inspection while recording proved that `pw-record` linked to the
Ora capture node. Eight-second trials captured 7.977 seconds and decoded at
0.370 RTF, but produced empty transcripts. A later three-second diagnostic
exited 0 with 2.985 seconds of audio, -67.60 dBFS RMS and -31.38 dBFS peak, 1.161
seconds decode/0.389 RTF, and an empty transcript. This contains no sustained
speech and therefore validates transport/silence handling, not live ASR accuracy.
One 20-second attempt emitted no result line; a subsequent short run passed and
kernel logs showed no OOM. Long bounded capture remains part of the soak gate.

Validation after the code changes:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q neko scripts/neko_camera_proximity.py \
  scripts/neko_asr_transcribe.py
git diff --check
```

All 65 tests passed. Rollback is a source revert of the event/proximity adapter,
PipeWire ASR helper, tests, and these notes; there is no installed runtime or
service state to undo. Do not remove the prior ALSA path when reverting only the
Bluetooth experiment.

## 2026-07-16 — MeowLLM text-to-Supertonic audition

The owner requested a TTS sample using <https://github.com/phanii9/MeowLLM>.
Current upstream documentation was checked first. MeowLLM is not TTS: it is a
3.45M-parameter, English-only, single-character text model with a 256-token
context. Its official model card explicitly excludes general assistance,
factual tasks, translation, and production use. The repository and Hugging Face
model card identify the source/checkpoint as MIT. It was therefore evaluated
only as an optional non-factual cat-quip source feeding the existing Supertonic
TTS path.

Pinned source:

```text
repository  https://github.com/phanii9/MeowLLM
path        /home/neko/models/MeowLLM
commit      d267a6c89bd978150ff9760ba77a37e7cee6601a
date        2026-04-07T02:11:08+04:00
licence     MIT; LICENSE SHA-256 c7721a4b1d3b5d07daa9752c1ed48036e1800bf927e8630936aae7ca0e92f0c4
disk        4.2M including Git metadata
```

Pinned model artifacts:

```text
repository  https://huggingface.co/hunt3rx99/meowllm
revision    f3a3f6ef7e2697e1346729f65d1e44bb3df31de8
path        /home/neko/models/meowllm-artifacts/f3a3f6ef7e2697e1346729f65d1e44bb3df31de8
best.pt     13,799,709 bytes; SHA-256 0b80e1328c454fe7ee94150adcd54bae79a92d8a1c8fc339d2b67e6c957c1327
tokenizer   100,761 bytes; SHA-256 874f76a917ca3ccba0fe7253bb08688df0d977a5e1a423ccc27c419c093a4332
disk        14M
```

The source was cloned without installing a package. The audition reused
`/home/neko/.local/share/neko/venvs/rfdetr-export`, already pinned with Python
3.12.3, CPU Torch 2.12.1, and tokenizers 0.22.2. No dependency changed. The
upstream loader calls `torch.load(..., weights_only=False)`, which permits pickle
code execution and was not used. The checkpoint instead passed restricted
`weights_only=True` loading: it contained primitive metadata plus 30 tensors,
13,790,208 tensor bytes, and no non-tensor state entries. The small imported
`model.py`, `tokenizer.py`, and generation helper were inspected for executable
I/O/network/subprocess behavior before use.

With two CPU threads and deterministic seeds, restricted load plus model/tokenizer
construction took 0.1483 s. The exact model had 3,447,552 parameters and a 1,682-
token vocabulary. Three prompts generated in 0.2802, 0.4156, and 0.3046 s; peak
process RSS was 290,396 KiB. The first output was:

```text
i was pretending to sleep. you may pet my head briefly.
```

The bundled dependency-free rule smoke test passed 34/34 cases. The advertised
68-test pytest suite was not run because the pinned export environment does not
contain pytest; its dependency lock was deliberately left unchanged. Restricted
load, real inference, tokenizer use, and the portable smoke test are the local
validation evidence.

The selected text was then synthesized with pinned Supertonic 3, F1 English,
six steps, and played through the already-verified PipeWire/Ora sink. Supertonic
loaded in 1.43 s, generated 4.14 s of audio in 2.83 s, and wrote a transient
368,684-byte WAV. Playback exited successfully and the temporary directory was
removed immediately; owner quality confirmation is pending. The ONNX runtime's
expected unavailable-DRM-device warnings appeared and did not affect CPU output.

No MeowLLM code, weight, tokenizer, generated text/audio file, package, systemd
unit, or boot dependency was added to the Neko repository/runtime. It remains an
on-demand lab profile. Complete rollback:

```bash
rm -rf /home/neko/models/MeowLLM
rm -rf /home/neko/models/meowllm-artifacts
```

Then revert only this documentation/notice entry. Do not remove the shared
`rfdetr-export` environment because RF-DETR export provenance still depends on
it. Any future integration must implement a Neko-owned restricted loader and
complete-text policy gate rather than calling the upstream unsafe loader.

## 2026-07-16 — KittenTTS Kiki audition and CatMeows candidate library

The owner selected KittenTTS's Kiki voice at 1.2x for evaluation. Official
KittenML sources were checked on 2026-07-16. KittenTTS 0.8.1 is an Apache-2.0,
ONNX/CPU developer preview with 24 kHz output and native speed control. Source
`main` was `9f3e0d8b6600b56ebe1b4d7b6d8e1e020077d1f2`; release tag `0.8.1` was
`f0282f0198d497b7256535b755f9f3e339c1baa7`. No source checkout was needed.

Pinned wheel:

```text
URL       https://github.com/KittenML/KittenTTS/releases/download/0.8.1/kittentts-0.8.1-py3-none-any.whl
path      /home/neko/models/kittentts/artifacts/kittentts-0.8.1-py3-none-any.whl
size      22,210 bytes
SHA-256   482a436c4f1f3192153710376e459ff3689517ebcda7c2b051e2fd4187b41851
license   Apache-2.0 in wheel metadata and official repository
```

Pinned `KittenML/kitten-tts-mini-0.8` revision
`c02725660cea441db4c383af69f1f26f5cd00947`:

```text
directory /home/neko/models/kittentts/mini-0.8/c02725660cea441db4c383af69f1f26f5cd00947
config    470 bytes; SHA-256 6b160bc9b19e24ecb21e84bc14f8a7da21fdf47ec72d42450bc5cf514b61804a
ONNX      78,268,016 bytes; SHA-256 0f5bbae4fc4800c98dbc544a87ecfa79510de2fb8222db30d12e5bfe9177df91
voices    3,278,902 bytes; SHA-256 40ad2638952b77b7b2f30127e2608e169fc69dd256b53bd8aaa3409a33193c42
model dir 78 MiB on disk
```

The exact wheel was inspected before execution. Its local ONNX inference class
does not use its imported Misaki objects, but that declared path pulls in spaCy,
spaCy Curated Transformers, and Torch. Its package initializer also eagerly
imports an unpinned Hugging Face downloader. The first generated lock exposed
107 packages and was replaced before installation. The installed path uses the
32-package closure in `deploy/requirements/kittentts.in` and its hash-generated
aarch64 lock. The direct packages installed were NumPy 2.5.1, ONNX Runtime
1.27.0, SoundFile 0.14.0, espeakng-loader 0.2.4, and phonemizer-fork 3.3.2;
every actual transitive dependency is explicit in the lock.

Installation commands, using the already recorded uv 0.11.28:

```bash
/home/neko/.local/bin/uv venv --python /usr/bin/python3 \
  /home/neko/.local/share/neko/venvs/kittentts
/home/neko/.local/bin/uv pip install \
  --python /home/neko/.local/share/neko/venvs/kittentts/bin/python \
  numpy==2.5.1 onnxruntime==1.27.0 soundfile==0.14.0 \
  espeakng-loader==0.2.4 phonemizer-fork==3.3.2
/home/neko/.local/bin/uv pip install \
  --python /home/neko/.local/share/neko/venvs/kittentts/bin/python \
  --no-deps \
  /home/neko/models/kittentts/artifacts/kittentts-0.8.1-py3-none-any.whl
patch -d /home/neko/.local/share/neko/venvs/kittentts/lib/python3.12/site-packages \
  -p1 < deploy/patches/kittentts-0.8.1-minimal-offline.patch
```

The initial environment was patched with the same two exact edits using
`apply_patch`. `onnx_model.py` changed from SHA-256
`76013a72a0a2411f710472ec4d3a4e8088447bee0b6c2c6f726a383cb33fef35`
to `06d82b09ec6a90f0a016136893d1b2a98132102dbca2d43133489a19d34cc46e`.
`__init__.py` changed from
`2da252fac0b3d201bc5578b961a0f92304ea352a619c70add933dd41f61153cc`
to `21e9cbdaff454f3fd99c44c31fbdc60504eca102859f3cd9c29f82573cf94531`.
The environment occupies 177 MiB. No global package or PATH changed.

`deploy/requirements/kittentts.lock` was regenerated with:

```bash
/home/neko/.local/bin/uv pip compile deploy/requirements/kittentts.in \
  --output-file deploy/requirements/kittentts.lock \
  --python /usr/bin/python3 \
  --python-platform aarch64-manylinux_2_28 \
  --generate-hashes --only-binary :all: \
  --exclude-newer 2026-07-16T23:59:59Z --no-deps
```

A clean-room `/tmp` venv then installed all 32 packages using
`--require-hashes --no-deps`, accepted the recorded patch, and imported
`KittenTTS_1_Onnx` as version 0.8.1. The temporary environment was deleted.

The first exact Kiki/1.2x sample used the sentence `Hello, little kitten! I'm
Neko. Shall we curl up together and hear a cat story?`. Cold load took 1.629 s;
generation took 8.238 s for 6.150 s of audio (1.339 real-time factor) with
278.9 MiB peak process RSS. It produced mono, signed 16-bit, 24 kHz PCM, played
successfully over PipeWire sink 61 (`Ora GQ Headphone`, then default at 67%),
and was deleted immediately. A second short cold-process smoke measured 1.577 s
load, 3.787 s generation for 2.792 s audio, 1.356 real-time factor, and 276.3
MiB peak RSS. ONNX Runtime's unavailable `/sys/class/drm/card*` discovery
warnings did not affect CPU inference. `scripts/neko_kittentts_speak.py` now
provides exact offline artifact verification and repeatable sample generation.
No service is installed or enabled.

The same research found CatMeows version 1.0.2, Zenodo record 4008297. Zenodo
labels it CC BY 4.0; the authors additionally state research/non-commercial use
and an acknowledgement requirement. This matches the owner's personal,
non-commercial setting, but the dataset remains external to Git. It was fetched
and verified with:

```bash
mkdir -p /home/neko/models/cat-sounds/catmeows/4008297
curl --fail --location --retry 3 \
  --output /home/neko/models/cat-sounds/catmeows/4008297/dataset.zip \
  'https://zenodo.org/records/4008297/files/dataset.zip?download=1'
md5sum /home/neko/models/cat-sounds/catmeows/4008297/dataset.zip
sha256sum /home/neko/models/cat-sounds/catmeows/4008297/dataset.zip
```

The archive MD5 is `b5fa911bcd6514e39dfef6876f747df4`, matching Zenodo;
SHA-256 is
`214000280e6ef33b10e39ef063ccc1f2f83d789ab57f2a5d111da63b06f659ae`.
Its 441 ZIP entries passed a traversal-path check before extraction. The 440
actual WAVs are all mono/16-bit/8 kHz, total 805.684 seconds: 127 brushing, 92
waiting-for-food, and 221 isolation recordings. The extracted directory plus
archive occupy 24 MiB. No dataset sound was played or selected. Isolation calls
are excluded by default pending a human friendly/distress review.

Current generative research also identified the gated May 2026 Stability AI
`stable-audio-3-small-sfx` model as the first strong later experiment: 433M,
CPU/edge-oriented SAME-S, text-to-SFX and audio editing. It is not installed.
It requires owner acceptance of the Stability AI Community License and Gemma
terms, and its publisher provides no Jetson result. Test only as a stopped,
sequential profile after acceptance.

Rollback:

```bash
rm -rf /home/neko/.local/share/neko/venvs/kittentts
rm -rf /home/neko/models/kittentts
rm -rf /home/neko/models/cat-sounds/catmeows/4008297
```

Then revert the KittenTTS input/lock/patch/helper and related documentation.
Supertonic, Gemma, boot targets, and system packages are independent.

## 2026-07-16 — Stable Audio 3 Small SFX optimized local audition

The owner accepted the Stability AI/Gemma gated terms and supplied a Hugging
Face token at a private home-directory path. Commands read it into an ephemeral
`HF_TOKEN`/authorization value only. The secret value was never printed, copied,
committed, or written to these notes.

Official source was pinned without running its bootstrap installer:

```text
repository  https://github.com/Stability-AI/stable-audio-3
path        /home/neko/models/stable-audio-3
commit      0385302ea26522f00c80392c4b708df5ebf1adf5
LICENSE     SHA-256 16bd922f0deee6f11a76f5582258fdc3abdf67c6b8719dbcafbc34dee31979a6
disk        49 MiB including Git metadata before model symlinks
```

The generic source requires Torch/Torchaudio 2.7.1 and was not executed. The
official `optimized/tflite` backend explicitly supports Linux ARM with
LiteRT/XNNPACK and needs no Torch or Transformers at runtime. A dedicated Python
3.12.3 environment was created from the project-controlled input and aarch64
hash lock:

```bash
/home/neko/.local/bin/uv pip compile \
  deploy/requirements/stable-audio-3-tflite.in \
  --output-file deploy/requirements/stable-audio-3-tflite.lock \
  --python /usr/bin/python3 --python-platform aarch64-manylinux_2_28 \
  --generate-hashes --only-binary :all: \
  --exclude-newer 2026-07-16T23:59:59Z
/home/neko/.local/bin/uv venv --python /usr/bin/python3 \
  /home/neko/.local/share/neko/venvs/stable-audio-3-tflite
/home/neko/.local/bin/uv pip install \
  --python /home/neko/.local/share/neko/venvs/stable-audio-3-tflite/bin/python \
  --require-hashes -r deploy/requirements/stable-audio-3-tflite.lock
```

All 24 packages installed. Key versions are ai-edge-litert 2.1.6,
huggingface-hub 1.23.0, NumPy 2.5.1, SentencePiece 0.2.2, and SoundFile 0.14.0.
Imports passed on aarch64; the environment occupies 125 MiB. No system package,
global PATH, existing LiteRT-LM environment, or service unit changed.

The optimized weights repository was pinned at revision
`08c64b96b1e59942aade69759f60fb88c58c90c4` under
`/home/neko/models/stable-audio-3-optimized/<revision>`. Exact files initially
downloaded and linked into the pinned source runtime:

| Relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `tflite/sa3-sm-sfx/dit_w8a8-dyn.tflite` | 467,069,712 | `9bae6401e925e9dc0f721955f2d92549e07d7c54e43070b779d2f35750ec42b2` |
| `tflite/same-s/dec_fp32.tflite` | 218,377,156 | `cd87fa6686b24a56dc3497e05fbb26a34cf9604afe49c6631e829c9e70fccf21` |
| `tflite/t5gemma/encoder_fp16.tflite` | 563,818,608 | `8530d0b3e6b9b9dcf1239145c2a853fb749708eaddbb472ff8f0802b50059372` |

The model API's published sizes and SHA-256 values matched every local file.
This initial set occupies about 1.2 GiB. It implements the official fastest CPU
DiT plus reference decoder recommendation. The SAME-S encoder was not needed or
downloaded because only text-to-audio was tested.

Before generation, `neko-gemma.service` was stopped with `sudo systemctl stop`.
Available memory rose from about 5.8 to 6.4 GiB. Baseline telemetry was about
4.50–4.54 W and 47 C. Two 20-second, eight-step, six-thread, CFG-off runs passed:

| Prompt | Seed | Model wall | Realtime | Peak RSS | Peak input | Peak temp | Raw SHA-256 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Friendly meows/trill | 12016 | 15.04 s | 1.33x | 2,106.8 MiB | 9.409 W | 49.75 C | `5297570f785c6236ed264e2758071a7e8e95385c3e5e544bd137865753450bc3` |
| Soft steady purr | 22016 | 14.37 s | 1.39x | 2,107.0 MiB | 9.409 W | 50.38 C | `08762cac226fe5f2dd15507335a888697c44e2038f298dcdc42543e4065933aa` |

Both were 44.1 kHz stereo. Only transient peak-normalized copies were played
through Ora at the existing 67% sink volume; all four WAVs were deleted. Owner
review rejected the pair for unattended use: the first few cat sounds were very
distressed, most of the latter half was good, and all of it was somewhat choppy.

To test the publisher's next-higher precision, this exact artifact was added:

```text
tflite/sa3-sm-sfx/dit_w8a32.tflite
467,132,768 bytes
SHA-256 7a6c8c48233b31b0f5482236d2681aa3690ba7ea71c87ec1870c9ceaab653de7
```

The optimized revision directory then occupied 1.6 GiB. A contented-cat prompt,
explicit negative prompt, CFG 2.0, and seed 32016 were tried with batched and
sequential CFG. Both processes were killed before the first sampling step at
6,501.7 and 6,466.1 MiB observed RSS, after 10.121 and 9.060 seconds. No WAV was
produced. The w8a32 profile is unsupported on this 8 GB host.

The same guided prompts were then run on the viable w8a8-dyn DiT with sequential
CFG to avoid batch memory amplification. The guided contented-meow sample took
21.75 seconds model wall for 20 seconds, 2,108.2 MiB peak RSS, seed 32016. Its
reported raw peak was 1.085, so the official writer clipped the over-range
transient. The guided continuous-purr sample took 21.29 seconds, 2,108.5 MiB,
seed 42016, with raw peak 0.624. Raw hashes were:

```text
b9da5dfd756d79e45100a6bfb3cc7648b23aca882fa239677ee7437b384e01a9  guided meow
b9588a196d3345c5af7bdbafdd6b2778ceaacba9d0a962dc830e0cfd56d42978  guided purr
```

Audition copies were attenuated by 6 and 3 dB respectively, played through Ora,
and deleted together with the raw files. The owner found the quality not much
better and selected pre-generated library sounds instead. Stable Audio raw
generation is closed for revision one. The installed profile is retained only
as a stopped research tool; it is not an assistant dependency. Generated output
remains forbidden from unattended child-facing use.

Gemma was restored after each evaluation. The final correct health check passed
at `http://127.0.0.1:9379/v1/models` with the fixed `gemma-4-e2b-it` ID. An
earlier immediate check accidentally used port 8765 and failed; the service log
showed that readiness had completed normally on 9379. No model/service failure
occurred. No Stable Audio unit is installed or enabled.

Rollback:

```bash
rm -rf /home/neko/.local/share/neko/venvs/stable-audio-3-tflite
rm -rf /home/neko/models/stable-audio-3
rm -rf /home/neko/models/stable-audio-3-optimized
```

Then revert `deploy/requirements/stable-audio-3-tflite.in`, its lock, and the
related documentation. This does not affect Gemma, KittenTTS, Supertonic, or the
curated CatMeows source.

## 2026-07-16 — Owner-curated Freesound library inventory

The owner supplied `/home/neko/curated-cat-sounds`. A read-only inventory found
24 audio files totaling 127 MiB and 812.226 seconds: 17 WAV, five MP3, one AIFF,
and one FLAC. The names use Freesound's downloaded
`<sound-id>__<uploader>__<title>` convention. The directory contained no license,
URL, or descriptive sidecars.

Each `https://freesound.org/s/<sound-id>/` page was retrieved on 2026-07-16 and
checked against the local ID/uploader/title. Every page resolved. Publisher page
metadata supplied title, description, duration, sample rate, creator, and exact
license link. Local originals were hashed with `sha256sum`; no duplicate SHA-256
was found. SoX inspected supported lossless containers. Its build cannot decode
the five MP3s, and `ffprobe` is not installed, so no package was added merely for
this inventory; the Freesound source metadata and `file(1)` container report were
used for those files.

The checked manifest is `config/cat-sounds/curated-freesound.json`. It records
all 24 filenames/checksums and does not copy media into Git. License totals are
15 CC0 1.0, three CC BY 4.0, two CC BY-NC 3.0, and four CC BY-NC 4.0. The six NC
items fit the owner's current personal/noncommercial use only and must remain
visibly separate from the repository's MIT license. The source pages and license
URLs are the attribution ledger; publisher AI-training preferences have not been
cleared, so this inventory authorizes no training use.

Title/description-only triage assigned provisional tags to 10 meow-led, 11
purr-led, two mixed meow/purr, and one processed novelty/alarm source. No audio
was played, edited, normalized, copied, or enabled. All 24 entries remain
`pending_listening_review`; the novelty alarm is additionally manual-only, and
the kitten-attention and multi-cat/vet items explicitly require distress review.
The next pass must record usable time ranges, emotional classification,
background noise, speaker/transducer role, and safe gain before making derived
delivery assets.

No service, package, model, device configuration, or boot state changed. The
temporary public HTML page cache used for the inventory was deleted after the
manifest was validated. Removing the repository manifest and these notes fully
rolls back this metadata-only step; it does not alter the owner's source files.

## 2026-07-16 — Guided cat-sound normalization and review start

The first item-1 playback used fixed GStreamer volume 0.25 and was reported as
extremely quiet. A continuous-library attempt was interrupted during item 2 as
soon as the owner requested one-source-at-a-time review; no label was inferred.
The initial sub-second replays could also finish before Bluetooth output woke.

No package was installed. Existing GStreamer 1.24.2 `rganalysis` measured all 24
originals with forced track ReplayGain at reference level 89 dB. Results are in
`config/cat-sounds/curated-freesound-normalization.json`: a 0.35 common digital
review master, per-track gain, and -1 dBFS sample-peak ceiling. Originals were
not rewritten. `neko/cat_audio.py` implements the gain/peak math and
`scripts/neko_cat_sound_review.py` verifies the selected source hash, holds one
PipeWire stream open through a two-second silent pre-roll, plays one complete
normalized source, and exits. `tests/test_cat_audio.py` covers the calculations.

Validation passed: four unit tests; Python compilation; 24/24 manifest-to-analysis
joins; 24/24 source hashes; 24 listed playback calculations; JSON parsing; and
`git diff --check`. Item 1 measured +12.28 dB, used multiplier 1.439, and had
predicted sample peak 0.080. After silent pre-roll it was audible. The owner
recorded it as a keep candidate: plaintive, interrogatory, insistent, slightly
fuzzy, but good. The structured result is
`config/cat-sounds/curated-freesound-listening-review.json`.

This review level is not calibrated cart SPL. Final speaker and body-transducer
paths require separate masters and an oversampled true-peak delivery pass. No
source audio, package, service, model, PipeWire default, Bluetooth profile, or
boot state changed. Rollback is to remove the new normalization/review configs,
`neko/cat_audio.py`, `scripts/neko_cat_sound_review.py`, and
`tests/test_cat_audio.py`, then revert these notes; the external source library
is unaffected.

### Review completion and outcome

The guided pass then classified all 24 entries. Twenty-three played completely.
The owner stopped item 22 after hearing enough of its long breathy/wheezy,
distance-variable recording to decide it was unnecessary as a standalone asset;
the playback process was confirmed closed. No other playback was left running.

The first version of the new pre-roll pipeline failed before audio with a
GStreamer caps parse error caused by quoting caps inside `Gst.parse_launch`.
The caps were corrected, item 2 passed a `fakesink` parse/decode check, and its
full audible replay then succeeded. This produced no partial output file or
system change. All subsequent one-item playbacks used the corrected code.

Final classification counts in
`config/cat-sounds/curated-freesound-listening-review.json`:

| Classification | Count |
| --- | ---: |
| Primary/keep candidates, including excerpt/split candidates | 19 |
| Secondary maybe candidates | 2 |
| Manual-only novelty | 1 |
| Not selected for standalone runtime | 2 |

Priority results are item 10's clean general meow (10/10), item 14's friendly
thank-you meow/purr (9/10), item 21's clean split-meow source (9/10), item 17's
primary transducer purr after removing the last 0.5 second (10/10), item 23's
relaxing transducer purr (9/10), and item 24's snuffly/playful affectionate purr
(10/10). The ledger also records all owner-reported emotional roles, scores,
background noise, clipping/impact/tail defects, speaker/transducer choices,
excerpt requirements, and runtime constraints. Items 9 and 21 did not sound
distressed to the owner; item 8 remains manual-only because it is an unnatural
processed alarm/remix.

Completion validation:

```bash
jq -e '.review_status == "complete" and (.entries | length) == 24' \
  config/cat-sounds/curated-freesound-listening-review.json
# true

python3 -m unittest discover -s tests
# Ran 69 tests ... OK
git diff --check
# pass
```

All 69 repository tests passed in 0.101 seconds. All reviewed sounds remain
disabled: the next phase creates lossless excerpts/loops, performs
integrated-loudness and oversampled-true-peak mastering, emits attribution, and
bench-tests separate speaker/transducer masters. Review approval alone does not
authorize unattended child-facing playback.

## 2026-07-16 — Versioned curated cat-audio milestone

At the owner's request, every review decision beginning with `keep_` was copied
byte-for-byte from `/home/neko/curated-cat-sounds` into
`assets/cat-sounds/originals`. This includes the manual-only novelty item 8 and
excludes secondary maybe items 2/12 plus non-standalone items 20/22. The result
is 20 files, 74,496,458 content bytes (about 71 MiB); the largest is 14,049,324
bytes, below GitHub's per-file limit. Git LFS was neither installed nor needed.

The selection was performed by joining the source and owner-review JSON, then
copying only matching filenames. `assets/cat-sounds/manifest.json` independently
pins repository path, source ID/URL, creator/title, exact Creative Commons
licence/URL, decision, and original SHA-256. The distribution is 11 CC0 1.0,
three CC BY 4.0, two CC BY-NC 3.0, and four CC BY-NC 4.0. The root MIT licence
does not cover these recordings. The six BY-NC sources are limited to the
owner's personal/noncommercial deployment. `.gitignore` has narrow exceptions
only for audio under this reviewed originals directory; generated/private audio
remains ignored elsewhere.

Human maintenance documents were added:

- `docs/cat-sounds/CAT_SOUNDS_MASTER.md` covers all 24 sources, including the
  four not distributed, with annotations, emotional/action meaning, output role,
  decision/score, licence, and use/processing constraints;
- `docs/cat-sounds/PROCESSING_AND_REMIX_QUEUE.md` separates first-delivery
  trimming/splitting/mastering, later cleanup, explicit manual remix work, and
  deferred external sources.

The source manifest now points to both the completed listening ledger and the
distribution manifest. `THIRD_PARTY_NOTICES.md`, `README.md`, and `AGENTS.md`
state the asset-level licence boundary. Originals remain runtime-disabled.

Validation and publication checks for this milestone include:

```bash
python3 -m unittest tests.test_cat_sound_assets
# Ran 2 tests ... OK; verifies selection, paths, hashes, bytes and licence totals

python3 -m unittest discover -s tests
# Ran 71 tests ... OK
git diff --check
# pass
git status --short
```

No package, model, service, audio device, default sink, or boot state changed.
Rollback is to remove `assets/cat-sounds`, the two cat-sound documents, and the
narrow `.gitignore` exceptions, then revert source-manifest, notice, README,
AGENTS, plan/research, and setup-log references. The owner's external originals
are not changed by rollback.

## 2026-07-16 — Deterministic P0 cat-audio cleanup and mastering

The P0 plan required decoded MP3 support, integrated loudness, and true-peak
analysis that the installed SoX/GStreamer tool set did not provide together.
Installed the single NVIDIA Jetson repository package:

```bash
sudo -n apt-get install --simulate ffmpeg
sudo -n apt-get install -y ffmpeg
dpkg-query -W -f='${Package}\t${Version}\t${Installed-Size}\n' ffmpeg
sha256sum /usr/bin/ffmpeg
```

Exact result:

```text
package             ffmpeg 7:8.0.1-nvidia
installed size      81,845 KiB (APT reported 83.8 MB additional disk)
download            22.9 MB from repo.download.nvidia.com/jetson/ffmpeg r39.2
FFmpeg build         n8.0.1-9-g90b8004959-1ubuntu0.1
/usr/bin/ffmpeg      3e74c1741e7e990aa3ae47f774a74baa2df57e27b08b1e0f3846d0d861e181c7
```

No other package was installed or upgraded. The command did not run
`apt autoremove`. No systemd unit, model, audio device, PipeWire route, default
sink, or boot dependency changed.

Added `config/cat-sounds/derived-assets-recipes.json` and
`scripts/neko_master_cat_sounds.py`. The builder verifies original SHA-256s,
uses absolute `/usr/bin/ffmpeg` and `/usr/bin/ffprobe`, and never rewrites an
original. It produces mono 48 kHz signed 24-bit PCM WAV with:

- exact decoded-timeline trims and qsin edge fades;
- conservative `0.5L+0.5R` stereo downmix;
- SoXR 48 kHz resampling at precision 28;
- provisional second-order 45 Hz speaker high-pass or 25–350 Hz transducer
  band-pass;
- a 750 ms qsin/qsin cyclic crossfade for item 17's loop;
- linear gain to -23 LUFS-I, capped at -2 dBTP without compression/limiting;
- high-pass triangular dither for 24-bit integer delivery;
- FFmpeg `loudnorm` measurement plus an independent
  `ebur128=peak=sample+true` verification.

The FFmpeg filters report true peak but expose no oversampling-factor field in
their CLI output, so the manifest records the exact method/build/hash and does
not fabricate a factor. Recipes include source 10 `0.030–0.900 s`, source 14
`0.030–3.220 s`, nine source-21 candidate ranges, source-17 contiguous
start/loop/stop regions through `33.500 s`, source 18 `0.100–6.820 s`, full
source 23 with fades, and source-24 short `4.720–8.850 s` plus sustained
`0.980–60.950 s`. Source-21 range `5.234–7.139 s` retains overlapping calls
because the candidate split point risked an audible cut.

Build command and results:

```bash
python3 scripts/neko_master_cat_sounds.py
# built 25 assets, 34009384 bytes, runtime remains disabled
```

Outputs are under `assets/cat-sounds/derived`; their manifest records exact
hashes/bytes/frames, source decode ranges, ordered processing, measured LUFS/LRA/
true peak/sample peak/DC/clipped samples, loop seam metrics, rights, and pending
approvals. `assets/cat-sounds/ATTRIBUTION.md` provides human TASL/change notices.
The rights distribution is ten CC0 1.0, fourteen CC BY 4.0, and one CC BY-NC
3.0 derivative; the root MIT licence applies to none. The NC file remains
personal/noncommercial.

All 25 have zero clipped samples and are <= -2.0 dBTP. Twenty-three are within
0.03 LU of -23 LUFS-I. The two item-24 speaker files are peak-limited at -2.0
dBTP and remain at -27.13/-28.76 LUFS-I; preserving natural snuffle dynamics was
preferred to compression/limiting. Their transducer copies reach target. The two
item-17 loop boundary amplitude/slope deltas are below 0.001 full scale, but
continuous listening is still mandatory.

`config/cat-sounds/runtime-allowlist.json` names only semantic actions, bounds
gain/cooldown/duration/output, denies raw paths/unknown actions, and prevents an
LLM from choosing path/gain/output. Every action and autonomous flag is false.
The builder marks every derivative `bench_candidate` with derived listen,
hardware acceptance, and child-facing review pending.

Validation:

```bash
python3 scripts/neko_master_cat_sounds.py --check
python3 -m unittest tests.test_cat_sound_assets tests.test_cat_sound_derived_assets
python3 -m unittest discover -s tests
git diff --check
```

The deterministic rebuild compares exact audio bytes, manifest/attribution text,
and file set. Unit tests cover hashes/media format/frames, mastering bounds/no
clipping, source ranges, TASL/NC rights, loop bounds/seams, and the fail-closed
allowlist. The deterministic rebuild reported 25 verified assets; the complete
repository suite ran 76 tests successfully. Derived owner listening and final Visaton/transducer hardware tests
remain outstanding; no file is eligible for unattended playback.

Rollback is a Git revert of the derived files, recipe, manifest, attribution,
allowlist, builder/tests, and documentation. After confirming no other workflow
needs the analyzer, remove it with `sudo apt-get remove ffmpeg`; do not use
`autoremove` without a separate audit. Originals remain byte-identical.

## 2026-07-16 — KittenTTS Micro voice selection and resident service

The owner accepted a more informal Neko delivery style—contractions, shorter
words, short clauses, and gentle silliness—and selected Kiki at 1.2x. In a
back-to-back Ora headphone comparison, the owner found virtually no audible
difference between the 80M Mini reference and the faster 40M Micro profile.
Micro is therefore the revision-one English default. KittenTTS remains English-
only; Supertonic stays installed for French and Spanish.

### Artifacts and runtime

Official KittenML model repositories were downloaded at exact Hugging Face
revisions with the existing `uvx`/`huggingface-hub==1.23.0` workflow:

| Profile | Exact revision/path | Important SHA-256 |
| --- | --- | --- |
| Mini 0.8 | `c02725660cea441db4c383af69f1f26f5cd00947` under `/home/neko/models/kittentts/mini-0.8` | ONNX `0f5bbae4fc4800c98dbc544a87ecfa79510de2fb8222db30d12e5bfe9177df91`; voices `40ad2638952b77b7b2f30127e2608e169fc69dd256b53bd8aaa3409a33193c42` |
| Micro 0.8 | `1ccf72b2c2048fd17efac7de2fab32d10e225084` under `/home/neko/models/kittentts/micro-0.8` | ONNX `95481626fee1ba70ce683e69c534fc7cb38433c46ce42d3abbeafb4b9f1a4123`; voices `112710c1be8ad0e967c190fb0fd95cbe5848ec4791b93209f20b28b7da20dac1` |
| Nano 0.8 INT8 | `84781d74e29ee25217551556398b42f80593a813` under `/home/neko/models/kittentts/nano-0.8-int8` | ONNX `f7b0afcbee92870b32b8e0276d855b954dc25470c9f051b376ac7eee537c76fc`; voices `8aa7cee235abb0739cb51e6559685f65a4dacd95568833d05699b1633f519b3f` |

The corresponding config hashes are, in the same order,
`6b160bc9b19e24ecb21e84bc14f8a7da21fdf47ec72d42450bc5cf514b61804a`,
`1f0bd2208348f9211cb0da64fcd1536eb28228571cc6b09e767eb6e203a0a532`,
and `b66006ccbeccd4de5fc3c9272059c47f5725df7215fd889785c03602652fab64`.
The model directories occupy about 78, 43, and 27 MiB. The isolated environment
occupies about 177 MiB and contains KittenTTS 0.8.1, ONNX Runtime 1.27.0, NumPy
2.5.1, phonemizer-fork 3.3.2, and SoundFile 0.14.0. The locally retained wheel is:

```text
/home/neko/models/kittentts/artifacts/kittentts-0.8.1-py3-none-any.whl
SHA-256 482a436c4f1f3192153710376e459ff3689517ebcda7c2b051e2fd4187b41851
```

The first local patch inherited uv's hardlink into its unpack cache. To prevent a
site-package patch from modifying cached package content, the package was
reinstalled in copy mode after cleaning only KittenTTS's uv cache, then patched
with the recorded forward-only patch:

```bash
/home/neko/.local/bin/uv cache clean kittentts
UV_LINK_MODE=copy /home/neko/.local/bin/uv pip install \
  --python /home/neko/.local/share/neko/venvs/kittentts/bin/python \
  --reinstall --no-deps \
  /home/neko/models/kittentts/artifacts/kittentts-0.8.1-py3-none-any.whl
patch --batch --forward \
  -d /home/neko/.local/share/neko/venvs/kittentts/lib/python3.12/site-packages \
  -p1 < deploy/patches/kittentts-0.8.1-minimal-offline.patch
```

The resulting installed `onnx_model.py` hash is
`f1ac67a13e0dba6ddb902e8d1106e0e21512324a7cfafa2f164723a23f8bc661`;
`kittentts/__init__.py` is
`21e9cbdaff454f3fd99c44c31fbdc60504eca102859f3cd9c29f82573cf94531`.
The pristine cache inode is distinct from the deployed file. A dry-run of the
repository patch against that pristine cache passed.

### Integration changes

Released KittenTTS 0.8.1 removes `.?!` while chunking and appends commas, which
flattened question/exclamation prosody. `neko/tts_chunking.py` narrowly backports
the punctuation/abbreviation behavior from official upstream commit
`9f3e0d8b6600b56ebe1b4d7b6d8e1e020077d1f2`; tests cover questions,
exclamations, `Dr.`, `p.m.`, decimals, long word-safe splits, and unpunctuated
tails. The local wheel patch also accepts explicit ONNX Runtime session options
and providers. Neko fixes the CPU profile at four intra-op threads, one inter-op
thread, sequential execution, and full graph optimization.

`scripts/serve_kittentts.py` verifies every selected model artifact before load,
warms the model, signals systemd readiness, and accepts one bounded request at a
time through `/run/neko/tts.sock`. It emits length-prefixed, sentence-sized,
24 kHz mono signed-16-bit PCM frames. This is early sentence delivery, not
model-native frame streaming. The protocol caps a request at 4,000 characters,
headers at 64 KiB, and individual audio frames at 32 MiB. It has no Internet
listener. `scripts/neko_tts_client.py` can save a WAV, feed the frames directly
to one persistent `pw-cat` process, or do both. English `--speak` conversation
now uses this worker; French/Spanish still use Supertonic.

The source unit was verified, installed, enabled, and started:

```bash
systemd-analyze verify deploy/systemd/neko-tts.service
sudo install -o root -g root -m 0644 deploy/systemd/neko-tts.service \
  /etc/systemd/system/neko-tts.service
sudo systemctl daemon-reload
sudo systemctl enable --now neko-tts.service
```

The unit runs as `neko`, uses only `AF_UNIX`, a private network/device namespace,
read-only home/system views, no capabilities, no swap, 400/512 MiB memory
high/max, four inference threads, bounded tasks/restarts, and a private runtime
directory. `PULSE_SERVER=unix:/dev/null` suppresses Pulse autospawn attempts in
the synthesis-only worker; actual playback remains in the caller's PipeWire
session. `systemd-analyze security` rates the installed source-matching unit 2.2
`OK`. It is enabled and active with zero restarts. A real power-cycle boot check
is still pending.

### Measurements and acceptance

The common audition was:

```text
Hi, kitten! I'm Neko. Wanna go find something silly?
```

Both profiles used Kiki, 1.2x, four CPU threads, punctuation-preserving chunks,
and 120 ms inter-sentence gaps. Mini took 7.225–7.570 seconds to generate about
5.3–5.6 seconds (RTF 1.34–1.36); Micro took 3.800–4.024 seconds for about
5.4–5.8 seconds (RTF 0.70). The owner selected Micro after back-to-back playback.
Nano INT8 was retained as an emergency comparison, not selected; in the earlier
same-sentence sweep Micro was also slightly faster than Nano.

With Micro resident and warmed, three accepted-line runs reported first sentence
data at 1.103, 1.111, and 1.127 seconds and total synthesis at 3.763, 3.768, and
3.809 seconds for 5.415 seconds of audio. A later systemd run reported 1.092 and
3.672 seconds. The emitted WAV was PCM S16LE, mono, 24 kHz, 5.415 seconds. One
generated audition measured -21.4 LUFS-I and -1.7 dBFS true peak; no mastering
was applied. The model contains stochastic operations, so exact waveform hashes
are not reproducible and quality must be tested semantically/subjectively.

During one request, the service reported about 170–190 MiB current/peak cgroup
memory. `tegrastats` observed up to 7.068 W `VDD_IN`, 47.812 C, and 0% GPU use;
this was a short warm request with Gemma also active, not a full combined soak.
Service stop/start, readiness, socket ownership/mode, saved-WAV validation,
streamed Ora playback, source/installed-unit equality, patch dry-run, and all 85
repository tests passed. Production Visaton listening, amplifier/limiter tuning,
cancel/barge-in behavior, audio arbitration, cold boot, and the full concurrent
ASR/Gemma/perception/TTS soak remain acceptance gates.

### Rollback

Disable the worker before removing any artifacts:

```bash
sudo systemctl disable --now neko-tts.service
sudo rm /etc/systemd/system/neko-tts.service
sudo systemctl daemon-reload
rm -rf /home/neko/.local/share/neko/venvs/kittentts
rm -rf /home/neko/models/kittentts
```

Then revert the TTS service/client/config/chunker/tests, wheel patch, conversation
route, persona contract, and documentation. Supertonic, Gemma, cat sounds, ASR,
and perception are independent and remain usable.

## 2026-07-16 — Continuous buffered voice, keyword wake, and barge-in bench

This milestone built an attended integration bench, not a production or boot
service. It joins the existing Nemotron ASR, loopback Gemma service, and private
KittenTTS socket with continuous memory-only capture, speech segmentation,
dedicated keyword spotting, bounded context, and interruptible playback. The
complete behavior and test record is in
`docs/plan/2026-07-16-interruptible-voice.md`.

### External VAD and keyword artifacts

The existing sherpa-onnx 1.13.4 ASR environment was reused; no second runtime was
installed. Two official k2-fsa/sherpa-onnx release artifacts were downloaded to
NVMe:

| Artifact | Official URL | Local artifact | Bytes / SHA-256 |
| --- | --- | --- | --- |
| Silero VAD ONNX | `https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx` | `/home/neko/models/sherpa-onnx-vad/silero_vad.onnx` | 643,854 / `9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6` |
| sherpa bilingual 3M open-vocabulary KWS, 2025-12-20 | `https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2` | `/home/neko/models/sherpa-onnx-kws/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2` | 32,885,699 / `68447f4fbc67e70eee3a93961f36e81e98f47aef73ce7e7ca00885c6cd3616a6` |

The VAD directory occupies 636 KiB. The KWS archive plus extracted model occupy
71 MiB; the extracted model alone is about 39 MiB. The files actually selected
by Neko are:

| KWS file | SHA-256 |
| --- | --- |
| `encoder-epoch-13-avg-2-chunk-16-left-64.int8.onnx` | `408bbd740838c42d5bf6d1c5b80b3c88b616c7860b92d980328b5b068c76ae48` |
| `decoder-epoch-13-avg-2-chunk-16-left-64.onnx` | `63a22dd60f40fff082ac3e09afa507f6787da36df76ded2fbe145fa233e22c21` |
| `joiner-epoch-13-avg-2-chunk-16-left-64.int8.onnx` | `190d4067b4cc20b72a42a1916e69d92052000fb7051a427ebb1bc72a69207dc1` |
| `tokens.txt` | `2d3f32311f9b692b964da3c90e830258d3e78e013cb0c992dbfb15cd5a1a71b0` |
| `en.phone` | `f7000ec3a90544c0c7c16090d8951779c2b322e14dad5006290f498567d439ea` |

Equivalent reproducible provisioning commands are:

```bash
install -d /home/neko/models/sherpa-onnx-vad /home/neko/models/sherpa-onnx-kws
curl --fail --location --output \
  /home/neko/models/sherpa-onnx-vad/silero_vad.onnx \
  https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx
curl --fail --location --output \
  /home/neko/models/sherpa-onnx-kws/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2 \
  https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2
tar -xjf \
  /home/neko/models/sherpa-onnx-kws/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2 \
  -C /home/neko/models/sherpa-onnx-kws
sha256sum /home/neko/models/sherpa-onnx-vad/silero_vad.onnx \
  /home/neko/models/sherpa-onnx-kws/sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2
```

Silero VAD upstream is MIT. sherpa-onnx code/runtime is Apache-2.0. The KWS
archive remains an external, non-distributed evaluation artifact; verify its
model-specific redistribution terms before packaging it.

### Runtime and policy changes

`scripts/neko_voice_assistant.py` captures C922 audio by default from stable ALSA
name `plughw:CARD=Webcam,DEV=0` as 16 kHz mono signed-16-bit PCM. It never writes
live microphone audio. Silero runs on CPU with a 512-sample window, threshold
0.25, 0.6-second end silence, 0.2-second minimum speech, 20-second maximum speech,
and a 30-second in-memory buffer. KWS runs on CPU with one thread, four active
paths, score 1.5, threshold 0.1, and one trailing blank. The checked-in
`config/asr/neko-keywords.txt` includes three full `Neko Neko` pronunciations,
three single-`Neko` fallbacks, `bye bye`, and `goodbye`.

Nemotron text is now a best-effort hint, not the activation authority. On real
owner speech it rendered the activation inconsistently as variants including
`Eko Neko`, a single `Neko`, `Echo Necho`, `Echo necko`, `Go`, or nothing. The
dedicated KWS event opens the deterministic session. At VAD end, the exact same
bounded samples are serialized to an in-memory mono 16 kHz WAV and sent to local
Gemma using OpenAI-compatible `input_audio`. No media leaves the loopback host.

`neko/gemma_client.py` adds the in-memory WAV encoder and a six-turn,
2,400-character default conversation history. The client request field was
corrected from the ignored `max_tokens` spelling to `max_completion_tokens=96`.
`neko/tts_protocol.py` adds caller-owned cancellation: it terminates the active
`pw-cat`, shuts the TTS socket to unblock a read, and reports cancellation even
when the resulting player exit code is nonzero. `neko/behavior.py` adds observed
wake aliases and deterministic `bye bye`/`goodbye`/`good bye` sleep handling.

Capture and VAD continue during Neko's speech. New speech cancels audible output;
if it begins while Gemma is working, that stale reply is discarded before it can
play. Sleep closes the session and clears history without a Gemma request. Normal
execution does not print transcripts or replies; `--verbose-transcripts` is an
attended diagnostic opt-in.

No assistant systemd unit was created, installed, or enabled. The resident
`neko-gemma.service` and `neko-tts.service` remain independent. The live bench
command is:

```bash
/home/neko/.local/share/neko/venvs/asr/bin/python \
  scripts/neko_voice_assistant.py --verbose-transcripts --max-dialogues 2
```

### Private replay fixtures and validation

The owner authorized six spoken fixtures covering wake/request, interruption,
follow-up, negative/no-wake control, stop, and sleep. They remain in an
owner-readable directory outside the repository: parent mode 0700, files 0600.
Their names, path, hashes, audio metadata, and contents are intentionally absent
from the public repository because a voice recording is biometric media. Longer
raw capture files were deleted after Silero trimming. The replay code paces each
file in real time through the real VAD/KWS/ASR path; later inputs wait for the TTS
`speaking` event, then begin 350 ms later to make barge-in deterministic.

Observed accepted cases:

- Wake: models loaded in 5.228 seconds; dedicated keyword detection opened the
  session despite ASR `Echo, necko, tell me something silly`; buffered-audio
  Gemma response took 11.804 seconds.
- Negative control: no keyword event, session, Gemma call, or playback occurred.
- Full barge-in: first response took 11.733 seconds; timed owner speech emitted
  `barge_in_detected`, playback returned `cancelled`, the new request transcribed
  correctly, and a replacement response took 12.378 seconds and played fully.
- Sleep: the first response took 11.752 seconds and was cancelled; ASR was empty,
  but KWS emitted keyword-only sleep, policy emitted `audio_cancelled` with
  `sleep-word`, and no second Gemma request occurred.
- A deterministic non-microphone cancellation timer set at 1.500 seconds returned
  `cancelled` at 1.755 seconds. Production speech-onset-to-audible-silence remains
  unmeasured.
- Fixture ASR took approximately 0.79-1.59 seconds for about 2.1-4.0 seconds of
  VAD-selected audio. Repeated buffered-audio Gemma requests took 11.73-12.38
  seconds. A separate 2.942-second synthetic inline-audio request took 16.057
  seconds and answered correctly. Earlier text requests took 10.29-11.82 seconds.

Bluetooth headphones isolate playback from the webcam microphone and therefore
do not validate production acoustic echo cancellation. Remaining gates are
multi-speaker/angle/noise false- and missed-wake tests, production reSpeaker AEC
reference testing, routing/latency choice, simultaneous resident-memory and
power/thermal measurements, unplug/crash/network behavior, two-hour soak, cold
boot, and a resource-bounded user-session unit with PipeWire readiness.

### 64K context experiment

Gemma 4 E2B advertises a 128K architecture, but the enabled LiteRT service remains
bounded to 2,048 total tokens. A stopped, isolated experiment requested
`--max-num-tokens 65536` with a 5.5 GiB memory cgroup instead of changing the
normal service. The transient worker initialized in about 1.278 seconds and used
about 512 MiB before inference. LiteRT warned that 65,536 exceeded its internal
target/magic number 32,003 and substituted 32,000. Its first tiny request reached
5,617,280 KiB anonymous RSS and the isolated cgroup OOM-killed it. The normal 2K
Gemma service was immediately restored and passed its loopback health request.

This result must not be described as 64K support. Even the silent 32K substitute
cannot coexist safely with Neko's stack on 8 GB. The next honest 64K experiment
is the already pinned QAT Q4_0 GGUF through llama.cpp with quantized KV cache,
probably under sequential model residency.

### Rollback

Ensure no attended voice process or `arecord` child remains, then revert
`scripts/neko_voice_assistant.py`, `config/asr/neko-keywords.txt`, the behavior,
Gemma-client and TTS-protocol changes, their tests, and this documentation. The
external detector artifacts can be removed independently:

```bash
rm -rf /home/neko/models/sherpa-onnx-vad
rm -rf /home/neko/models/sherpa-onnx-kws
```

Do not delete private owner fixtures without explicit owner direction. Gemma,
KittenTTS, Nemotron ASR, Supertonic, cat sounds, and perception are otherwise
independent of this attended integration bench.

Final milestone verification compiled `neko`, `scripts`, and `tests`, ran all 95
repository tests successfully, and passed `git diff --check`. Both enabled
dependencies were active/running with zero restarts; no attended voice assistant
or `arecord` process remained.
