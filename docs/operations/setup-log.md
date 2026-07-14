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
| Pipecat/ASR/TTS | research only | no | no |
| Neko systemd units | Gemma source unit and installed copy match | wrapper/API/readiness/restart smoke passed | Gemma enabled/active; no cold reboot yet |

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

- Destination: British Columbia, postal code `V9G 1L8`; every critical line must
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
power/weather notes. Checkout arrival to `V9G 1L8` could not be guaranteed
without entering the cart/checkout flow, so no seven-day delivery claim was made.

The temporary image path `/tmp/neko-cart-drive` was removed and verified absent.
Repository policy remains: never commit raw owner/bystander media, recordings,
transcripts, street addresses, GPS coordinates, embedded media-location metadata,
credentials or model weights. The owner-supplied postal code is intentionally
retained in this private repository only for tax/delivery research.

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
