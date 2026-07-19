# What If offline schedule cache and lookup

Status: implemented and deployed on 2026-07-17 in America/Vancouver.

## Upstream contract and local interpretation

The public Dust API documentation is
<https://dust.events/docs/Integrations/api/>. Neko refreshes these event-owned
feeds:

- <https://data.dust.events/what-if/schedule.json>
- <https://data.dust.events/what-if/music.json>
- <https://data.dust.events/what-if/art.json>
- <https://data.dust.events/what-if/camps.json>

Dust says schedule and music occurrences are repeated for multiple occurrences,
sorted by start time, and use ISO-like local timestamps without timezone data.
Neko therefore assigns `America/Vancouver` to those wall-clock values. The July
event dates resolve to PDT (`UTC-07:00`). Spoken output always uses a 12-hour
clock and says Pacific time. The host independently reports
`America/Vancouver (PDT, -0700)` with synchronized NTP and a UTC hardware clock.
The API page does not state redistribution terms;
mutable upstream data stays in runtime state and is not committed to Git.

The first installed refresh at 2026-07-17 10:40:49 PM PDT cached 333 schedule
occurrences, 152 music occurrences, 70 art entries, and 67 camps. The raw JSON
snapshots and generated 1.2 MiB SQLite database are under
`/var/lib/neko/what-if`. SHA-256 values for every normalized feed payload and
the fetch time are stored in the database `metadata` table. The database
contains 622 source rows. It caches all published material for fidelity but
marks 124 rows as mature based on `Mature 19+`, `Mature Audiences`, or `19+`
metadata; the child-facing lookup excludes those rows with no model override.

## Retrieval design

`neko.event_schedule.EventSchedule` is a read-only local tool.
`scripts/neko_what_if_lookup.py` exposes the same tool for diagnostics. The live
assistant recognizes schedule/calendar/current-activity, music/DJ, art, camp,
and explicit event questions and routes them directly to this tool. Upstream
descriptions are search material only: they are not added to the LLM prompt and
cannot instruct the model. Answers render selected titles, performers, places,
days, and times deterministically. Schedule questions and answers are also never
appended to the six-turn LLM conversation history. A separate one-query tool
state retains only an unresolved schedule refinement, so `music` and then
`house` can refine `Saturday at 8 PM` without polluting general conversation.
It is cleared after a result, a topic change, stop, sleep, or session close.
Natural refinement scaffolding such as `how about music`, `maybe art`, and
`I'd like downtempo` is discarded before specific-term matching; meaningful
category/style terms remain.
`No preference`, `anything`, `list them all`, and `tell me all` bypass the
refinement threshold and enumerate the complete applicable window. If a genuine
category/style refinement has zero matches, Neko says so and lists every event
from the original time window instead of ending at an empty result. The original
base window is retained separately from the progressively refined tool query.

Immediate lookup is deliberately time-first. Relative to the requested/current
Pacific time, it retains only occurrences that start no later than 30 minutes
from that point and end more than 15 minutes after it. This means an event with
15 minutes or less remaining is excluded. Shorter-duration entries receive a
ranking bonus so a precise DJ set beats a broad all-day lineup when relevance is
otherwise similar.

After temporal filtering, the tool creates sparse TF-IDF vectors only for the
small candidate subset and cosine-ranks the request against them. Performer,
title, description, type, location, camp, and source are indexed text. Small
local expansions cover music/DJ/set, art/artist/installation, food, and
family/kids vocabulary. This is an on-demand vector map without a resident
embedding model, network call, vector server, or new Python dependency.
Music rows are enriched at database-build time with their matching camp
description, allowing style words such as house or downtempo to match even when
Dust's `musicType` field is blank.

When a generic time window has more than three matches, Neko does not read the
top arbitrary rows. She asks whether the child wants music, art, food, a
workshop, or something else. A music-only set above that threshold asks for a
style, performer, or sound camp; an art set asks what kind or name. The next
short answer is applied to the pending tool query, not LLM history.

Discovery phrasing uses a broader candidate set:

- `when is DJ Nix playing` searches remaining timed occurrences, preferring
  performer/source matches;
- `where is yoga happening` searches remaining occurrences and returns place,
  day, and time;
- `is there any cat art installation` searches static art records;
- a weekday with no clock searches that event day;
- a weekday and clock uses the immediate window around that point.

A bare `Saturday at 8` currently means 8 PM; explicit `8 AM` remains morning.
The parser also accepts a missing `at`, joined `8pm`, dotted `8 p.m.`, and the
ASR-style `Saturday eight p.m.` form. This prevents a missed preposition or
spoken-number transcript from silently widening an 8 PM request to the full day.
The first live retry revealed the exact Nemotron rendering `Nico, what's going
on Sat day at eight PM`. The KWS/policy layer now treats `Nico` (plus Niko,
Nikko, and Nekko) as removable Neko address aliases, and the time parser maps
`Sat day` to Saturday. That exact text is a regression fixture and resolves to
the seven-match refinement prompt. A second attended retry exposed the final
policy-boundary form: punctuation normalization changes `what's` to `what s`.
The orphan possessive token `s` is now a stopword; the regression runs the
normalized controller output as well as the raw ASR sentence.
The next acoustic retry varied again to `Neco Neko ... eight P`. Wake repair is
therefore now structural rather than another whole-phrase exception: after KWS
has independently accepted the utterance, it removes up to two leading
Neko-like ASR tokens and inserts one canonical `Neko`. Lone `P` and `A`
meridiem suffixes are interpreted as PM and AM. The complete raw-to-policy-to-
schedule path for that exact phrase returns the same seven-match refinement.
Common weekday abbreviations (`Sat`, `Fri`, `Thurs`, and peers) and joined
forms such as `at8 PM` are accepted as well.
This matches the expected event usage but should be revisited if field speech
shows ambiguity. Exact named discovery currently requires at least one specific
request token in a candidate. It is safer than returning unrelated material,
but spelling/fuzzy-name and richer semantic recall remain future improvements.
No dense embedding model is justified until field misses show that the sparse
subset vectors are insufficient.

## Refresh, failure behavior, and deployment

`scripts/neko_refresh_what_if.py` fetches all four arrays with a 20-second
per-request timeout and 5 MB per-feed bound. It validates JSON arrays, builds a
new SQLite file, and replaces runtime snapshots/database only after all four
downloads and the database build succeed. A network, HTTP, schema, JSON, disk,
or build failure returns nonzero and leaves the last good database available.

Installed units:

- `/etc/systemd/system/neko-what-if-refresh.service`
- `/etc/systemd/system/neko-what-if-refresh.timer`

The enabled timer runs two minutes after boot and once per hour thereafter. The
oneshot runs as `neko`, has a 128 MiB memory limit, low CPU weight/priority, no
capabilities, a read-only system/home view, and write access only through its
systemd state directory. The first run passed and the timer scheduled its next
run exactly one hour later. The service being inactive/dead between successful
oneshot runs is expected.

Useful checks:

```bash
systemctl list-timers --all neko-what-if-refresh.timer
systemctl status neko-what-if-refresh.service neko-what-if-refresh.timer
python scripts/neko_what_if_lookup.py "when is Nix playing"
python scripts/neko_what_if_lookup.py --now 2026-07-25T20:00:00 \
  "what music is happening now"
```

Remove only this deployment with:

```bash
sudo systemctl disable --now neko-what-if-refresh.timer
sudo rm /etc/systemd/system/neko-what-if-refresh.service \
  /etc/systemd/system/neko-what-if-refresh.timer
sudo systemctl daemon-reload
sudo rm -rf /var/lib/neko/what-if
```

Do not remove the cache during an offline event unless loss of schedule lookup
is intended. Disabling the timer alone retains the last local copy.

## Validation and remaining gates

The repository suite passed 139 tests after the live refinement correction. Schedule-specific
tests cover intent boundaries, current/+30/end-more-than-15 filtering, narrow
duration preference, music vector ranking, mature filtering, static art scope,
Saturday-at-8 numeric/spoken parsing, high-cardinality refinement, ephemeral
tool state/no LLM-history pollution, 12-hour Pacific speech, broad when/where
discovery, and offline refresh preservation. Real-data diagnostics show seven
generic matches at Saturday 8 PM and now ask for a category; music narrows to
five choices and asks for style/performer/camp. A named Nix query still returns
the correct Saturday set and location.

Still required before unattended passenger use: live microphone phrasing tests,
field correction of ASR-mangled performer/camp names, stale-cache wording,
French output localization, event organizer confirmation of the local-time
assumption, and observation of at least one failed/offline timer run followed by
a successful recovery. The attended assistant remains the current runtime; this
milestone does not boot-enable the complete voice loop.
