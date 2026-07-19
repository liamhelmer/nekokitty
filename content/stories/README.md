# Neko story shelf

This directory will contain owner-editable original stories and individually
ingested Creative Commons works. The assistant must retrieve only approved
manifest entries; it must not treat the directory as an unconstrained prompt.

Keep narrated versions under five minutes. Author them for speech: casual
contractions, short sentences, everyday words, playful rhythm, and dialogue that
sounds natural to children aged 5–7. The TTS boundary also applies conservative
contractions as a backstop, but it is not a substitute for editing the prose.
External works need exact source, licence, attribution, text-
extraction record, and owner child-tone review before their full text is stored.

`library.json` is the runtime authority. `neko.story_library.StoryLibrary` uses
small exact-token/tag retrieval, excludes metadata-only candidates, and avoids
immediate repeats. This shelf does not need a vector database or another
resident embedding model. The current owner-test path narrates selected approved
text and adds evenly spaced sentence-boundary cat sounds at a target of one per
75 spoken words. The final long purr counts toward that density; current stories
receive seven or eight total sounds. A hard ten-sound ceiling protects later
five-minute stories from becoming cluttered. That live-TTS treatment is now the
degraded fallback. The normal path uses the versioned Mini/Kiki recordings and
fixed cue/purr plan under `recordings/mini-kiki-v1`; see the 2026-07-19 plan.

Pre-recorded sections group whole adjacent paragraphs up to 380 characters so
Mini sees substantially more punctuation and narrative context than the live
120-character worker. Do not edit an approved story and manually suppress its
stale-audio error: Neko falls back live and queues a low-priority incremental
rebuild of changed sections. The recording manifest, not filenames alone, is the
integrity and playback authority.

During a story, ordinary VAD speech/noise does not stop narration. An utterance
must begin with `Neko` (or `Neko Neko`) to arm interruption; the resulting
request continues the same session. The same overlap rule applies while Neko is
speaking in ordinary conversation, so nearby cross-talk is ignored. Once spoken
output completes, unprefixed follow-ups are accepted within the active session,
including while a post-story tail purr continues. Cat-sound playback is tracked
separately from active synthesized narration. Conversation history stores
only each manifest entry’s curated title, summary, and essentials—not the full
narrated text.
