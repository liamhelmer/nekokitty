# Main-branch auto-sync and assistant reload

## Owner decision

On 2026-07-19 the owner ended the feature-branch/PR phase for this project:
PR #6 was marked ready and merge-committed into `main` as
`cebe54d7f5649b6fa652f736f45b2190fe59d736`. The remote feature branch was
deleted, the local checkout was switched to `main`, and future project changes
are to be committed and pushed directly to `origin/main`.

The owner also authorized a five-minute bidirectional Git poll. This is a
deliberately state-changing unattended workflow: Git-visible local changes,
including dynamically composed stories and their rendered audio, are committed
and pushed. Remote `main` changes are fetched and integrated locally. A detected
remote revision change reloads the voice assistant.

## Serialization and safety boundary

`neko.repository_lock.repository_write_lock()` uses an exclusive advisory lock
at mode-0600 `%h/.local/state/neko/repository-write.lock`, inside a mode-0700
state directory. Three writers share it:

- Terra story composition holds it from pre-write inventory through validation
  and render-queue submission;
- the story recording worker holds it while the incremental Mini renderer writes
  FLAC sections and atomically publishes its manifest;
- Git sync requests it nonblocking and skips that five-minute cycle when either
  writer is active.

This prevents Git from committing a half-written story or partial recording
shelf. It cannot automatically coordinate an arbitrary human/editor/agent that
does not take this lock. Direct development on `main` therefore still requires
normal care around the timer.

Before each commit, the sync stages Git-visible changes with `git add -A` and
rejects secret-like basenames (`.env`, token/secret/credential/password/private-
recording patterns, and private-key suffixes). Ignored files remain ignored.
The gate is intentionally conservative and leaves rejected work local for a
human to resolve. It supplements rather than replaces `.gitignore` and GitHub
secret scanning.

## Five-minute algorithm

`scripts/neko_git_sync.py` requires the checked-out branch to be exactly `main`
and refuses merge, rebase, cherry-pick, or revert state. Under the repository
lock it:

1. stages and scans all Git-visible changes;
2. creates `Automated Neko sync YYYY-MM-DD HH:MM:SS TZ` when anything is staged;
3. fetches and prunes `origin main`;
4. fast-forwards when only remote is ahead, rebases local commits when histories
   diverge, and aborts without losing the local commit if rebase conflicts;
5. pushes `HEAD:main`;
6. atomically records the resulting revision in mode-0600
   `%h/.local/state/neko/git-sync-last-remote`;
7. when the fetched remote revision differs from the prior successful state,
   reloads user units and restarts `neko-voice-assistant.service`.

The timer uses `OnUnitActiveSec=5min`, `OnBootSec=2min`, `Persistent=true`, and
ten-second timer accuracy. The oneshot has nice 15, idle I/O priority, and a
four-minute systemd ceiling. Individual Git commands have a two-minute subprocess
ceiling. A conflict or authentication/network failure is logged and retried on a
later timer activation; it never resets, force-pushes, or deletes local work.

## Supervised assistant

The formerly terminal-owned attended command is now represented by the user unit
`deploy/systemd/user/neko-voice-assistant.service`. It starts after the user's
PipeWire service, uses the same PipeWire/English/attended-cat-sound command, and
restarts on unexpected failure. The Git units and assistant unit are installed
as symlinks in `%h/.config/systemd/user`, so a pulled unit change becomes visible
after the sync worker's `systemctl --user daemon-reload`.

This is still the attended/headphone audio policy, not production speaker/body-
transducer acceptance. Moving it under systemd improves ownership and reload
behavior; it does not waive the acoustic, AEC, weather, or passenger acceptance
gates.

## Validation

Four isolated temporary-repository tests cover local auto-commit/push, remote
fast-forward plus exactly one restart callback, secret-like path refusal, and a
busy story writer causing a clean skipped cycle. Existing online/story/voice
tests verify the shared writer integrations. All three user unit sources pass
`systemd-analyze --user verify`.

The three sources are installed as absolute symlinks under
`%h/.config/systemd/user` and enabled. The terminal-owned process was stopped;
the user service reached active and later logged online/ready after 5.433 seconds.
Two harmless initial syncs (an explicit start and the timer's already-due boot
trigger) both completed at revision `21f44f3` with no commit, remote change, or
restart. The next trigger was scheduled exactly five minutes after the last run.
The state and lock files are mode 0600, the tree remained clean/equal to remote,
and `loginctl` reports `Linger=yes`. The timer was briefly stopped—not disabled—
while recording deployment to avoid committing a half-written log. The final
documentation push is used below as the live remote-change/restart test.

## Rollback

Disable the timer and supervised assistant before reverting:

```bash
systemctl --user disable --now neko-git-sync.timer neko-voice-assistant.service
```

Remove only the three Neko symlinks under `%h/.config/systemd/user`, run
`systemctl --user daemon-reload`, and optionally return to the documented manual
assistant command. Do not delete the repository state directory until confirming
no composition, renderer, or sync worker holds the lock. Disabling linger is
optional and affects every user service, not only Neko:

```bash
loginctl disable-linger neko
```
