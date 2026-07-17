# Cat Sounds Master

Last updated: 2026-07-16

This is the maintained human catalog for Neko's cat recordings: what each sound
communicates, when to use it, where to play it, and what work remains. Update
this file whenever a source is added, a derived clip is created, an action is
mapped, or a listening/hardware decision changes.

The exact source/licence/hash ledger is
[`../../config/cat-sounds/curated-freesound.json`](../../config/cat-sounds/curated-freesound.json).
Owner review details and verbatim comments are in
[`../../config/cat-sounds/curated-freesound-listening-review.json`](../../config/cat-sounds/curated-freesound-listening-review.json).
The 20 checked-in originals are pinned by
[`../../assets/cat-sounds/manifest.json`](../../assets/cat-sounds/manifest.json).

## Operating rules

- `speaker` means audible character expression. `transducer` means body vibration;
  a sound listed for both may eventually receive two separately mastered copies.
- An LLM may request a semantic action, never a filename or arbitrary gain. The
  deterministic supervisor selects an approved asset, enforces cooldowns, and
  owns interruption/fade behavior.
- `keep` means source material worth preserving, not permission for unattended
  playback. Every runtime asset still needs excerpting/mastering, attribution,
  action mapping, and final speaker/transducer acceptance.
- Item 8 is always manual-only. Items 20 and 22 are not standalone runtime
  candidates. Items 2 and 12 are secondary maybes and are not checked into the
  repository.
- The recordings retain their per-file Creative Commons licences. `BY-NC`
  sources are restricted to the owner's personal/noncommercial deployment and
  are not covered by the root MIT licence.

## Maintained catalog

| # | Recording and licence | Owner decision | Character | How and where to use | Processing note |
| ---: | --- | --- | --- | --- | --- |
| 1 | [Cat Meow3](../../assets/cat-sounds/originals/262314__steffcaffrey__cat-meow3.wav), steffcaffrey, [CC0](https://freesound.org/s/262314/) | Keep; unscored | Plaintive, interrogatory, insistent; slightly fuzzy | Speaker: question or attention request | Light cleanup/EQ only if it improves fuzz without changing character |
| 2 | [Cat purring](https://freesound.org/s/273156/), lrocio44, CC0; external only | Maybe, 6/10 | Deep, active, playful purr; ambient noise | Possible transducer secondary after cleanup | Do not add unless it fills a gap left by cleaner purrs |
| 3 | [Cats Meow](../../assets/cat-sounds/originals/325199__psychopancake__cats-meow.wav), psychopancake, [CC BY-NC 3.0](https://freesound.org/s/325199/) | Keep, 7/10 | Very friendly, affectionate, happy meow/purr; feels loving | Speaker: affectionate greeting, bonding, happy acknowledgement | Reduce minor ambient noise if useful; retain noncommercial attribution |
| 4 | [Cat Meowing](../../assets/cat-sounds/originals/333916__lextrack__cat-meowing.mp3), lextrack, [CC0](https://freesound.org/s/333916/) | Keep, 7/10 | Friendly but pushy and insistent; asks the person to interact | Speaker: attention/interaction prompt with strict cooldown | Master cleanly; never repeat rapidly |
| 5 | [purring moo](../../assets/cat-sounds/originals/342547__snapper4298__purring-moo.wav), snapper4298, [CC BY-NC 4.0](https://freesound.org/s/342547/) | Keep, 8/10 | Long, warm, inviting, happy, cuddly, sleep-friendly | Speaker + transducer: calm, cuddle, rest or sleepy purr | Select a scratch-free loop; avoid movement noise; retain NC attribution |
| 6 | [Cat meow](../../assets/cat-sounds/originals/362652__trngle__cat-meow.wav), trngle, [CC0](https://freesound.org/s/362652/) | Keep, 7/10 | Inquisitive and curious; ending sounds cut off | Speaker: curious reaction, investigation, gentle question | Inspect/repair tail or add a short natural fade |
| 7 | [Cat meow](../../assets/cat-sounds/originals/365076__justiiiiin__cat-meow.wav), justiiiiin, [CC BY-NC 4.0](https://freesound.org/s/365076/) | Keep, 8/10 | Excited, impatient, expectant; wants a treat or food | Speaker: reward/treat anticipation or playful request only | Context and cooldown required; retain NC attribution |
| 8 | [alarm clock trippy cats](../../assets/cat-sounds/originals/428552__maleryberg__alarm-clock-trippy-cats.mp3), maleryberg, [CC0](https://freesound.org/s/428552/) | Keep, manual novelty only | Weird, trippy, otherworldly, very insistent and intentionally unnatural | Speaker: explicit special situation, rave/music singalong | Never autonomous; candidate for bounded musical remix only |
| 9 | [Kitten meows](../../assets/cat-sounds/originals/476918__luke100000__kitten-meows.wav), luke100000, [CC0](https://freesound.org/s/476918/) | Keep excerpts, 9/10 | Very insistent/almost begging; food anticipation; kitten or older-cat voice | Speaker: short kitten food/treat request | Split a short representative clip; full minute is too intense |
| 10 | [Meow](../../assets/cat-sounds/originals/491690__pizzapoes__meow.mp3), pizzapoes, [CC BY-NC 3.0](https://freesound.org/s/491690/) | Priority keep, 10/10; bench derivative built | Clean, standard, neutral-friendly, general-purpose meow | Speaker: default everyday meow or neutral acknowledgement | `meow_general.speaker.v1`; derived listen/hardware pending; retain noncommercial attribution |
| 11 | [SND CatPurring Loop 01](../../assets/cat-sounds/originals/508688__megrez7274__snd_catpurring_loop_01.wav), megrez7274, [CC0](https://freesound.org/s/508688/) | Keep, 8/10 | Strong short contented purr, no external noise | Transducer priority; speaker optional | Inspect apparent source clipping and verify loop seam |
| 12 | [Cat Meow](https://freesound.org/s/521665/), msalvado, CC0; external only | Maybe, 6/10 | Mixed meow/purr content, but microphone rubbing and heavy noise | Only a secondary excerpt source | Prefer cleaner alternatives; do not add without a clean isolated range |
| 13 | [Cat meow](../../assets/cat-sounds/originals/530341__wesleyextreme_gamer__cat-meow.wav), wesleyextreme_gamer, [CC BY-NC 4.0](https://freesound.org/s/530341/) | Keep, 8/10 | Questioning, expectant, patient and fairly neutral | Speaker: gentle question, patient expectation, neutral prompt | Master only; retain NC attribution |
| 14 | [Cat meow and purr](../../assets/cat-sounds/originals/536703__scousemousejb__cat-meow-and-purr.wav), scousemousejb, [CC BY 4.0](https://freesound.org/s/536703/) | Priority keep, 9/10; bench derivative built | Very friendly, affectionate, grateful—almost “thank you” | Speaker: gratitude, successful help, affectionate acknowledgement | `meow_thank_you.speaker.v1`; derived listen/hardware pending; retain attribution |
| 15 | [Cat meowing](../../assets/cat-sounds/originals/541951__didi0508__cat-meowing.wav), didi0508, [CC BY-NC 4.0](https://freesound.org/s/541951/) | Keep, 9/10 | Two friendly, active, alert cats chatting or telling a story | Speaker: explicit multi-cat conversation/story scene | Preserve multi-cat identity; not Neko's default solo voice; retain NC attribution |
| 16 | [Cat Perfect Purr](../../assets/cat-sounds/originals/546413__cristinaadrn__cat-perfect-purr.wav), cristinaadrn, [CC0](https://freesound.org/s/546413/) | Keep excerpts, 8/10 | Hypnotic, relaxed, sleep-friendly; minor clipping | Low-level speaker + transducer sleep/rest purr | Prefer clean middle/later range; remove final 0.5 s; inspect clipping |
| 17 | [purring cat 01](../../assets/cat-sounds/originals/550941__kadka_funkenflug__purring-cat_01.wav), kadka_funkenflug, [CC0](https://freesound.org/s/550941/) | Primary purr, 10/10; six bench derivatives built | Best clean, relaxed/contented purr | Primary transducer purr; speaker for contentment/rest | Speaker/transducer start/loop/stop candidates built; loop listening and hardware pending |
| 18 | [Kitty Purr](../../assets/cat-sounds/originals/553375__xoiziox__kitty-purr.aiff), xoiziox, [CC0](https://freesound.org/s/553375/) | Keep, 9/10; two bench derivatives built | Clean short purr with minimal background noise | Transducer + speaker: quick purr interjection/acknowledgement | Speaker/transducer short candidates built; derived listen/hardware pending |
| 19 | [Cat Purring long/clear/loud](../../assets/cat-sounds/originals/579898__jamesbradford__cat-purring-longclearloud.mp3), jamesbradford, [CC0](https://freesound.org/s/579898/) | Keep excerpts, 7/10 | Good contented purr with definite clipping and a microphone impact | Transducer + speaker secondary purr | Remove/avoid impact near 12 s and inspect clipping |
| 20 | [Cat Purr](https://freesound.org/s/621006/), uniuniversal, CC0; external only | Reject, 6/10 | Active, curious, snuffling purr with heavy breathing | No runtime use; cleaner alternatives cover it | Do not process unless requirements change |
| 21 | [Cats asking for attention](../../assets/cat-sounds/originals/655659__221316__cats-asking-for-attention.wav), 221316, [CC BY 4.0](https://freesound.org/s/655659/) | Priority split source, 9/10; nine bench excerpts built | Clean chorus of short curious, neutral-to-insistent attention meows; not distress | Speaker: separate neutral, curious and insistent attention actions | Nine candidates built; one preserves overlapping calls; owner intensity/multi-cat classification pending; retain attribution |
| 22 | [Deep Cat Purr](https://freesound.org/s/735589/), anhedonic_picture_show, CC0; external only | No standalone use; source material only | Breathy/wheezy, especially early; highly variable microphone distance | No standalone runtime use | Retain externally only in case a unique clean excerpt is later needed |
| 23 | [cat purring](../../assets/cat-sounds/originals/779220__scwambled__cat-purring.wav), scwambled, [CC0](https://freesound.org/s/779220/) | Priority keep, 9/10; two bench derivatives built | Very relaxing, high-quality, short/bass-forward purr | Transducer priority; speaker optional | Speaker/transducer candidates built; derived listen/hardware pending |
| 24 | [Purring/snoring kitty](../../assets/cat-sounds/originals/790281__dudeawesome__cat-pur-purring-snoring-sleeping-beautiful-real-sounds-of-my-kitty.flac), dudeawesome, [CC BY 4.0](https://freesound.org/s/790281/) | Priority keep, 10/10; four bench derivatives built | Snuffly, friendly, curious, interested, happy, relaxed and playful; affectionate rubbing/scent-marking | Transducer + speaker: playful purr, close affection, curious physical interaction | Short/sustained speaker/transducer candidates built; speaker copies are true-peak-limited below target; derived listen/hardware pending |

## Initial semantic action set

The first P0 build is recorded in `DERIVED_AUDIO_BENCH.md`. Its allowlist is
fail-closed and entirely disabled; names below are design intent, not enabled
runtime behavior. Item-21 intensity labels remain deliberately provisional.

The first soundboard should expose semantic actions such as:

- `meow_general` → item 10;
- `meow_thank_you` → item 14;
- `meow_question_patient` → item 13;
- `meow_attention_neutral|curious|insistent` → item 21 derivatives;
- `meow_treat_excited` → item 7, with cooldown;
- `purr_primary` → item 17 derivatives;
- `purr_short` → item 18 or 23;
- `purr_playful_affection` → item 24;
- `purr_sleep` → cleaned item 5 or 16;
- `novelty_trippy_cats` → item 8, manual-only.

The processing queue is maintained separately so this catalog remains the
stable description and usage reference.
