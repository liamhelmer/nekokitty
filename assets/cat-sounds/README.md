# Curated cat recordings

This directory distributes 20 owner-reviewed Freesound originals for Neko's
personal, noncommercial sound palette. They are intentionally kept byte-for-byte
identical to the downloaded sources. Their SHA-256 values, creators, titles,
source pages, review decisions, and exact licences are in `manifest.json`.

These recordings are **not covered by the repository's MIT licence**. Each file
retains the Creative Commons terms listed in the manifest:

- [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)
- [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- [CC BY-NC 3.0](https://creativecommons.org/licenses/by-nc/3.0/)
- [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

The six `BY-NC` recordings are limited to noncommercial use. Attribution must
travel with every `BY` or `BY-NC` copy or derivative. Keep provenance for CC0
files as a project policy even though attribution is not legally required.
Derived clips must identify that they were modified, retain the source entry and
licence, and receive their own checksum and mastering record.

Repository inclusion authorizes playback/remixing only within the applicable
licence. It is not model-training clearance; uploader AI preferences remain a
separate decision. Nothing in this directory is enabled for unattended playback
until the processing/mastering and final output-hardware gates pass.

`derived/` contains 25 deterministic P0 **bench candidates** made from seven of
the approved originals. They are mono 48 kHz/24-bit PCM WAV files with exact
cuts, ordered DSP, loudness/true-peak results, hashes, approvals, and rights in
`derived/manifest.json`. `ATTRIBUTION.md` is the human TASL/change-notice surface.
The recipes live in `../../config/cat-sounds/derived-assets-recipes.json`; rebuild
or verify them with `../../scripts/neko_master_cat_sounds.py`. The fail-closed
semantic map is `../../config/cat-sounds/runtime-allowlist.json` and every action
is deliberately disabled. Derived files still require owner listening and final
speaker/transducer testing.

Maintained human documentation:

- [`../../docs/cat-sounds/CAT_SOUNDS_MASTER.md`](../../docs/cat-sounds/CAT_SOUNDS_MASTER.md)
- [`../../docs/cat-sounds/PROCESSING_AND_REMIX_QUEUE.md`](../../docs/cat-sounds/PROCESSING_AND_REMIX_QUEUE.md)
- [`../../docs/cat-sounds/DERIVED_AUDIO_BENCH.md`](../../docs/cat-sounds/DERIVED_AUDIO_BENCH.md)

Machine review/normalization sources:

- [`../../config/cat-sounds/curated-freesound-listening-review.json`](../../config/cat-sounds/curated-freesound-listening-review.json)
- [`../../config/cat-sounds/curated-freesound-normalization.json`](../../config/cat-sounds/curated-freesound-normalization.json)
- [`../../config/cat-sounds/derived-assets-recipes.json`](../../config/cat-sounds/derived-assets-recipes.json)
- [`../../config/cat-sounds/runtime-allowlist.json`](../../config/cat-sounds/runtime-allowlist.json)
