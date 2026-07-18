# Neko story shelf

This directory will contain owner-editable original stories and individually
ingested Creative Commons works. The assistant must retrieve only approved
manifest entries; it must not treat the directory as an unconstrained prompt.

Keep narrated versions under five minutes and apply the current three-sound-per-
story maximum. External works need exact source, licence, attribution, text-
extraction record, and owner child-tone review before their full text is stored.

`library.json` is the runtime authority. `neko.story_library.StoryLibrary` uses
small exact-token/tag retrieval, excludes metadata-only candidates, and avoids
immediate repeats. This shelf does not need a vector database or another
resident embedding model. The current owner-test path narrates selected approved
text and applies the shared maximum-three-sounds treatment.

During a story, ordinary VAD speech/noise does not stop narration. An utterance
must begin with `Neko` (or `Neko Neko`) to arm interruption; the resulting
request continues the same session. The same overlap rule applies while Neko is
speaking in ordinary conversation, so nearby cross-talk is ignored. Once spoken
output completes, unprefixed follow-ups are accepted within the active session,
including while a post-story tail purr continues. Cat-sound playback is tracked
separately from active synthesized narration. Conversation history stores
only each manifest entry’s curated title, summary, and essentials—not the full
narrated text.
