# Derived Cat-Audio Bench

Last updated: 2026-07-16

This is the reproducible record for Neko's first cleaned/mastered cat-sound
palette. It creates 25 lossless **bench candidates** from reviewed items 10, 14,
17, 18, 21, 23, and 24. It does not modify originals, enable runtime playback,
or claim production-speaker/transducer approval.

## Files and policy

- Recipes: `config/cat-sounds/derived-assets-recipes.json`
- Builder/verifier: `scripts/neko_master_cat_sounds.py`
- Audio and immutable measurement ledger: `assets/cat-sounds/derived/`
- Human credits/change notices: `assets/cat-sounds/ATTRIBUTION.md`
- Fail-closed action policy: `config/cat-sounds/runtime-allowlist.json`
- Integrity/policy tests: `tests/test_cat_sound_derived_assets.py`

Canonical outputs are mono 48 kHz signed 24-bit PCM WAV. The target is -23.0
LUFS-I within 0.5 LU and no more than -2.0 dBTP. Gain is linear and capped by
true peak; there is no compression, limiting, denoising, pitch shift, source
separation, or generative fill. FFmpeg's high-pass/low-pass filters are
provisional output protection, not final acoustic EQ:

- speaker: second-order 45 Hz high-pass;
- body transducer: second-order 25 Hz high-pass plus 350 Hz low-pass.

Every source is trimmed in FFmpeg's decoded timeline, downmixed by `0.5L+0.5R`
when stereo, resampled with SoXR precision 28, edge-faded or cyclically
crossfaded, linearly gained, and high-pass triangular-dithered to 24-bit PCM.
Compressed-source item 10 records the decoder/build because MP3 delay/padding
makes decoded time differ slightly from container metadata.

FFmpeg `loudnorm` supplies the build and verification measurements, with an
independent `ebur128=peak=sample+true` pass. The filters report true peak, but
this FFmpeg CLI does not expose the internal oversampling factor, so the manifest
does not invent one. It records the exact analyzer method, executable hash, and
build instead.

## Selected edits

| Source | Derived work |
| --- | --- |
| 10 | `0.030–0.900 s` general meow; 10/25 ms edges |
| 14 | `0.030–3.220 s` friendly thank-you meow/purr; 15/100 ms edges |
| 21 | Nine candidates: `0.030–0.826`, `0.826–1.470`, `1.760–2.700`, `3.060–3.837`, `3.837–4.487`, `4.487–5.234`, `5.234–7.139`, `7.139–7.821`, and `7.821–8.632 s` |
| 17 | start `0.400–3.725`; loop body `3.725–30.550` with 750 ms qsin/qsin cyclic crossfade; stop `30.550–33.500`; noisy tail excluded |
| 18 | `0.100–6.820 s` short purr interjection |
| 23 | full `0.000–8.906236 s` relaxing purr with mandatory edges |
| 24 | short playful excerpt `4.720–8.850`; sustained `0.980–60.950 s` |

Item 21's `5.234–7.139 s` candidate deliberately remains an overlapping group:
waveform/spectrogram analysis found two contours with no clean boundary. All
nine item-21 candidates still need owner classification as neutral, curious,
insistent, or multi-cat. The purr loop also needs continuous listening; small
amplitude/slope discontinuity is necessary but not sufficient for a natural
rhythm.

## Build results

The build produced 25 files and 34,009,384 audio bytes (about 32.4 MiB):

- 18 speaker candidates and seven body-transducer candidates;
- 11 meow/attention candidates and 14 purr phase/variant candidates;
- ten CC0 1.0 derivatives, fourteen CC BY 4.0 derivatives, and one
  CC BY-NC 3.0 derivative;
- zero clipped samples and no duplicate output hashes;
- all 25 at or below -2.0 dBTP;
- 23 within 0.03 LU of -23.0 LUFS-I.

The two item-24 speaker files are intentionally marked `target_reached: false`:
their snuffle transients reached -2.0 dBTP at -27.13 LUFS-I (short) and -28.76
LUFS-I (sustained). The builder retained natural dynamics instead of compressing
or limiting them. The body-transducer variants reach target. Reassess the
speaker copies with the real driver; they may stay optional, use a bounded lower
playback reference, or receive a reviewed device-specific treatment.

The two item-17 loop files have boundary amplitude/slope deltas below 0.001 full
scale and zero clipped samples. Neither metric constitutes listening approval.

## Rebuild and validation

Installed analyzer:

```text
Ubuntu package     ffmpeg 7:8.0.1-nvidia
FFmpeg build       n8.0.1-9-g90b8004959-1ubuntu0.1
/usr/bin/ffmpeg    SHA-256 3e74c1741e7e990aa3ae47f774a74baa2df57e27b08b1e0f3846d0d861e181c7
```

Commands:

```bash
python3 scripts/neko_master_cat_sounds.py
python3 scripts/neko_master_cat_sounds.py --check
python3 -m unittest tests.test_cat_sound_assets tests.test_cat_sound_derived_assets
```

`--check` rebuilds every candidate in a temporary directory and compares exact
bytes, manifest text, attribution text, and the output set. The fast tests check
hashes, WAV format/frames, loudness/peak bounds, no clipping, source ranges,
rights/TASL, loop metadata, and a fully disabled fail-closed allowlist.

## Remaining gates

1. Guided owner listening: classify all item-21 splits; approve/reject the
   item-17 start/loop/stop sequence; approve both item-24 excerpts and every
   remaining one-shot after mastering.
2. Repeat on the installed Visaton/amplifier and selected body transducer. Record
   physical volume, rattle/resonance, perceived balance, and safe gain/EQ.
3. Update approvals and replace provisional hardware profile values. Do not
   silently boost a peak-limited file or route a speaker master to a transducer.
4. Only enable actions whose exact file, output, child-facing review, cooldown,
   gain, and hardware acceptance all pass. Unknown action/path/output remains
   denied, and an LLM never selects filenames or amplitude.

Rollback is a Git revert of the derived WAVs, recipe/manifest/attribution,
allowlist, builder/tests, and related notes. To remove the host analyzer, after
confirming nothing else needs it, use `sudo apt-get remove ffmpeg`. Originals are
byte-identical and unaffected.
