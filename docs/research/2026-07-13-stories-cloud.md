# Offline-first story library and optional cloud enhancement

> **Owner-policy update — 2026-07-13:** current one-week system decisions are
> summarized in
> [`2026-07-13-canadian-one-week-bom.md`](2026-07-13-canadian-one-week-bom.md).
> For the first release, every story is **five minutes or shorter**, light, and
> non-scary. Age-appropriate conflict and reviewed folklore/religion are allowed;
> serious grief and extreme bathroom humour are excluded. Earlier longer,
> frightening, predation-heavy, or violent seed leads below are retained as
> research but are not approved first-release assets.

Research and planning date: 2026-07-13, America/Vancouver. Source catalog
counts and provider terms were checked against the linked official sources on
that date. Catalog counts and service terms can change and must be rechecked
before an ingestion release or cloud deployment.

## Scope and owner decisions already incorporated

This memo covers the story-library portion of Neko: sourcing legally reusable
children's stories, storing and indexing them locally, allowing a child to choose
whether a story is remixed, using the installed Gemma 4 E2B candidate within its
measured limits, and adding an optional text-only online enhancement without
making any story behavior depend on Internet access.

The plan incorporates these owner decisions:

- The cart is strictly personal and noncommercial in this revision.
- Internet-independent behavior is mandatory. A cloud-only story feature is not
  worth building.
- English is required; French is the second priority and Spanish the third.
- The audience is ages 5–10. The UI/content system should expose separate 5–7
  and 8–10 presentation lanes without assuming age equals reading level.
- Stories are about cats of all kinds, not only domestic cats. A feline must be
  central to every enabled work.
- First-release tellings are at most five minutes and use light, non-scary
  content. Longer or frightening leads are held for a later explicit policy
  change rather than silently edited into compliance.
- Age-appropriate conflict and reviewed folklore/religion are permitted. Serious
  grief and extreme bathroom humour are excluded.
- A child decides whether a story is altered.
- Text may leave the cart under policy. Audio and images may leave only with
  explicit human-in-the-loop consent.
- Existing Z.AI and Codex subscriptions may be used for development, but their
  suitability for an embedded runtime must be evaluated separately.
- The owner accepts LLM-only French/Spanish review for a clearly labeled
  prototype as a lower-assurance bridge when no fluent reviewer is available.
  This is not represented as fluent-human validation.
- A separately billed, text-only API may be enabled by an authorized adult after
  authentication, visible online-mode indication, provider/destination
  allowlisting, redaction, spend/rate limits, timeouts, and local fallback exist.
- Local adult enablement may use a physical control, preferably a keyed switch or
  one inside a locked compartment. Remote enablement is acceptable through an
  authenticated administration channel with expiry, visible cart-side state and
  immediate local revoke. A plain exposed button is not authentication.
- Neko should be cute, motherly, playful, and a little mischievous, without
  presenting itself as a human caregiver.
- A few seconds of interaction latency is acceptable, but a child should receive
  immediate acknowledgment while a longer response is prepared.

No story corpus, ingestion software, safety model, cloud API, or related service
was installed as part of this research.

## Recommendation

Start with a **30-work cat-only pilot**, then expand toward 60–100 only after the
review, ingestion, narration, and remix workflow is proven. Target 16 works in
the ages 5–7 presentation lane and 14 in ages 8–10. At least 18 should center
wild, extinct, or mythical cats so the collection does not collapse into only
domestic-cat stories. Use the Global Digital Library as the main machine-readable
source, then supplement it with selected StoryWeaver, African Storybook, and
dual-jurisdiction-cleared public-domain titles. Do not expose an upstream catalog
wholesale merely because a title has an acceptable license; every runtime-visible
item also needs rights, attribution, age/content, factual, and cultural review.

Provisional pilot balance:

| Primary shelf | Works | Editorial intent |
| --- | ---: | --- |
| Domestic/community cats | 8 | Friendship, mischief, care, purring, and Neko's cart-cat identity |
| Wild-cat science and conservation | 9 | Tigers, lions, leopards, snow leopards, and small wildcats; scientific facts stay immutable |
| Big-cat fables and folktales | 6 | Preserve cultural attribution and default to original-only |
| Magical/mythical cats | 4 | Tricksters and fantasy felines with explicit moral/content review |
| Interactive sound/guessing stories | 3 | Meows, purrs, roars, tracks, and alarm calls for participatory telling |

The age lanes are narration/presentation defaults, not diagnoses of ability.
StoryWeaver's current [reading-level guide](https://storyweaver.org.in/reading-levels)
explicitly says age/grade does not determine reading level. Use roughly 2–5
minutes and 100–600 words for the 5–7 lane, generally Levels 1–2. The 8–10 lane
also remains at or below five minutes, generally using roughly 300–750 words from
Levels 2–3. Treat a longer Level 4 work as separately reviewed episodes, each
with its own complete, non-scary stopping point and five-minute cap. Let an
adult/child choose a different lane per session and store no developmental
profile.

Every story should offer three clearly distinct modes, chosen by the child:

1. **Original:** tell the approved text without generative rewriting.
2. **Change a few things:** make deterministic substitutions only in
   curator-defined slots such as character names, setting, or a harmless object.
3. **Surprise-safe remix:** use Gemma to rewrite one bounded scene at a time from
   an approved story card, then check the entire scene before sending it to TTS.

Neko must never silently convert an original telling into a remix. If adaptation
is not permitted for a particular story, it should offer the original or another
adaptable story instead.

Keep content blobs outside the project Git repository, provisionally under
`/var/lib/neko/stories`. The project repository should contain ingestion code,
schemas, manifests, hashes, review records, and deployment configuration, but not
source content unless its redistribution rights have been individually verified.

### Seed inventory for human review

These are leads, not approved runtime assets. The light/non-scary five-minute
policy supersedes their earlier age-lane placement. Ingestion must retrieve and verify
the per-item license, contributor credits, text/edition hash, translation rights,
content, and the underlying publisher record.

| Lane | Candidate | Why it belongs / initial restriction |
| --- | --- | --- |
| 5–7 | [Wild Cat! Wild Cat!](https://content.digitallibrary.io/en/book/wild-cat-wild-cat/) and [French version](https://content.digitallibrary.io/fr/book/chat-sauvage-chat-sauvage-2/) | Survey of Indian wildcats. Candidate is marked CC BY 4.0; species, place, and facts are immutable, while the conversational frame may use slots. |
| 5–7 | [Watch Out! The Tiger is Here!](https://content.digitallibrary.io/book/watch-out-the-tiger-is-here/?topic=level-1) and [French version](https://content.digitallibrary.io/fr/book/attention-le-tigre-est-la/) | Forest alarm-call participation. Candidate Level 1/CC BY; retain the ecology and calls. |
| 5–7 | [Sani and Suri](https://content.digitallibrary.io/en/book/sani-and-suri/) and [French version](https://content.digitallibrary.io/fr/book/sani-et-suri/) | A missing pet leads to encounters with different cats; useful domestic/wild bridge. |
| 5–7 | [The Three Little Kittens](https://content.digitallibrary.io/en/book/the-three-little-kittens/) and [French version](https://content.digitallibrary.io/fr/book/les-trois-petits-chatons-2/) | Historical lead only until review confirms the dog/fear framing is non-scary under the current policy. |
| 5–7 | [Tiger's Delicious Treats](https://content.digitallibrary.io/en/book/tigers-delicious-treats/) | Playful anthropomorphic tiger; candidate for bounded fictional remix after item verification. |
| 5–7 | [Clever Cat](https://africanstorybook.org/newviewer/index.php?bt=3&dual=false&id=8878) | First-sentences story with a purr moment. Accept only if the item is returned by the current ASb-approved filter and remains CC BY 4.0. |
| 5–7 | [Manu and the Lion](https://www.africanstorybook.org/newviewer/index.php?bt=2&dual=false&id=18332) | Historical lead; hold from the first release because its comic-fright content conflicts with the current non-scary gate. |
| 8–10 | [The Cat in the Ghat!](https://content.digitallibrary.io/book/the-cat-in-the-ghat/?topic=level-4) | Western Ghats wildlife-photographer story. Keep location/ecology immutable; do not genericize it into a jungle. |
| 8–10 | [Gyalmo, the Queen of the Mountains](https://storyweaver.org.in/en/v0/blog_posts/481-storyweaver-celebrates-wildlife-week-2021) | Snow-leopard conservation work by a conservation scientist. Retain Spiti, local names, prey species, and conservation context. |
| 8–10 | [Our Encounter With a Snow Leopard](https://storyweaver.org.in/en/v0/blog_posts/474-new-book-by-the-nature-conservation-foundation-our-encounter-with-a-snow-leopard) | Nature Conservation Foundation story based on a Ladakh childhood; local context is immutable. |
| 5–7 | [Who is the Bravest?](https://content.digitallibrary.io/en/book/who-is-the-bravest/) | Lion-centered waterhole/counting story; verify the per-item CC BY record and keep animal facts distinct from anthropomorphic action. |
| 8–10 | [Lion and Warthog](https://www.africanstorybook.org/read/downloadbook.php?a=1&d=0&id=10201&layout=landscape) | Historical lead; betrayal and predation threat exclude it from the light/non-scary first release. |
| 8–10 | [Millions of Cats](https://www.gutenberg.org/ebooks/74181) | Historical lead; the mass cat fight excludes it from the light/non-scary first release, independent of its still-required jurisdiction/edition rights review. |
| 8–10 | [The Master Cat; or, Puss in Boots](https://www.gutenberg.org/ebooks/503) | Magical trickster lead; discuss deception/moral ambiguity rather than silently sanitizing it. Clear the exact translation/edition in both jurisdictions. |

Hold Kipling's cat/leopard tales for colonial/gender review. Reject graphic or
poor-fit first-release leads involving poisoning, attempted animal killing,
cannibalism, child-death threats, beating, or outdated circus captivity even
when their copyright status would permit use. Legal adaptability is not the same
as child-facing suitability.

Add these fields to every story manifest in addition to the rights/provenance
schema below: `felids[]` objects with nullable common/scientific names, living
context (`domestic`, `community`, `wild`, or `mixed`), and optional conservation
status plus `biological_status` (`extant`, `extinct`, or `unknown`); a separate
`fictional_feline_mode` (`none`, `anthropomorphic`, `mythic`, or `fantasy`);
plus `genre`, `cultural_origin`, `pronunciation_notes`,
`predation`, `fear`, `death`, `age_lane`, `duration_seconds`, and
`immutable_elements`. Keeping biological status separate from fiction prevents
a conservation story from being remixed into false zoology or a specific
cultural story into generic fantasy.

## Candidate content sources

### Global Digital Library

The [Global Digital Library content API](https://content.digitallibrary.io/api/)
is the strongest initial source. Its official API is intended for cross-platform
reuse, requires no authentication, exposes language catalogs and search, and can
provide H5P JSON and generated EPUB content. The API documentation says that each
content element carries item-specific Creative Commons metadata; ingestion must
still validate that metadata rather than assigning a catalog-wide license.

Live catalog queries on 2026-07-13 returned:

| API catalog | Records | Records labeled CC BY 4.0 |
| --- | ---: | ---: |
| [`/books/en`](https://content.digitallibrary.io/wp-json/content-api/v1/books/en) | 1,313 | 912 |
| [`/books/fr`](https://content.digitallibrary.io/wp-json/content-api/v1/books/fr) | 88 | 84 |
| [`/books/es-ni`](https://content.digitallibrary.io/wp-json/content-api/v1/books/es-ni) | 80 | 79 |
| [`/books/es-es`](https://content.digitallibrary.io/wp-json/content-api/v1/books/es-es) | 36 | 34 |

This yields 1,109 CC BY 4.0 candidate records across the requested languages,
before deduplicating translations, editions, and repeated works. These counts are
an inventory observation, not an approval list. Reject records with a missing or
ambiguous license, creator, publisher, or required attribution.

Treat all H5P and EPUB downloads as untrusted archives. Neko only needs validated,
allowlisted metadata and normalized text for the audio-first release. It should
not execute upstream JavaScript, render active H5P content, or fetch embedded
remote resources at runtime.

### StoryWeaver

[StoryWeaver](https://storyweaver.org.in/en/about), operated by Pratham Books, is
a strong source of multilingual children's material. Its
[terms](https://storyweaver.org.in/en/terms_and_conditions) and
[attribution guidance](https://storyweaver.org.in/en/attributions) permit reading,
downloading, translating, and making versions of the main CC BY 4.0 stories and
illustrations, subject to attribution and change notices.

Important boundaries:

- Preserve publisher, author, illustrator, translator, donor, and funder credits
  where the item requires them.
- The Read-Along feature and associated videos are described as CC BY-NC-ND 4.0;
  they must not be remixed.
- Prefer institutionally published or editor-recommended material. A community
  story being publicly visible is not equivalent to editorial approval.
- EPUB/PDF download is suitable for a curated workflow. No stable, documented
  public bulk catalog API was found. Do not scrape the site; request an approved
  data workflow from `storyweaveropen@prathambooks.org` if bulk access becomes
  necessary.
- StoryWeaver's web-platform code being open source does not set the license for
  its content. Running its full Rails/React platform would add unnecessary
  complexity to the Jetson.

Pratham Books' official program description is available on its
[Our Work page](https://prathambooks.org/our-work/).

### African Storybook

[African Storybook](https://www.africanstorybook.org/) is particularly relevant
because its workflow explicitly supports culturally grounded adaptation. Its
[terms](https://www.africanstorybook.org/terms.html) distinguish ASb-approved
stories from unchecked stories uploaded to the site. Neko should ingest only
ASb-approved or recognized partner-approved titles and should still check every
item's license.

The collection contains both attribution and noncommercial licenses. Limit the
first release to individually verified CC BY 4.0 titles. The official
[translation and adaptation guide](https://help.africanstorybook.org/documents/howto/Translate_and_Adapt.pdf)
expressly discusses changing names, places, reading level, scenarios, and endings,
making it a close match for Neko's requested remix behavior. Source encouragement
does not replace cultural review for any specific adaptation.

Convenient third-party Git mirrors can help discovery, but the official item page
must remain the source of truth for approval status, contributors, and license.

### Later sources for public-domain classics

These sources should be a later, separately reviewed phase rather than part of the
initial ingestion:

- [Faded Page / Distributed Proofreaders Canada](https://www.fadedpage.com/mission.php)
  offers Canadian public-domain books in text, EPUB, and PDF. Its approximately
  9,002-title catalog was Canada-oriented at review time. Canadian status does not
  guarantee US or worldwide public-domain status, and the catalog is not
  specifically child-curated.
- [Project Gutenberg offline catalogs](https://www.gutenberg.org/ebooks/offline_catalogs.html)
  provide RDF, CSV, OPDS, and mirror options for more than 75,000 ebooks. Its
  [terms](https://www.gutenberg.org/policy/terms_of_use.html) describe US-focused
  copyright clearance and warn users outside the US to check local law. Do not
  scrape the main website; use an official catalog or mirror and follow its
  User-Agent/contact guidance. Gutenberg metadata is insufficient by itself to
  establish all edition, translation, or illustration rights.
- [LibriVox](https://librivox.org/pages/about-librivox/) has a documented
  [XML/JSON API](https://librivox.org/api/info) for title, author, language, and
  track metadata. Its [public-domain notice](https://librivox.org/pages/public-domain/)
  is explicitly US-centered. Canada-clear each work and recording. Do not use a
  volunteer's voice for cloning or imitation without separate affirmative consent,
  regardless of the recording's asserted copyright status.
- [Bloom Library](https://docs.bloomlibrary.org/bloom-platform/) has more than
  22,000 free books in over 1,000 languages and supports manual EPUB/BloomPUB
  download. Its [OPDS integration](https://docs.bloomlibrary.org/opds/) generally
  requires an Enterprise arrangement, account, or partnership. It is worth
  revisiting if the initial sources leave a language or reading-level gap.

Old public-domain books require the same age, stereotype, violence, and cultural
review as contemporary stories. Age alone is not an editorial safety signal.

## Licensing and rights gate

> **Not legal advice:** This section is a conservative engineering policy for
> reducing rights risk. It is not a legal opinion. Recheck licenses, provider
> terms, applicable law, and intended distribution before publishing a corpus or
> materially changing the use.

The recommended per-item policy is:

| Rights status | Original telling | Remix | First-release policy |
| --- | --- | --- | --- |
| CC0 1.0 | Yes | Yes | Accept after content/provenance review |
| CC BY 4.0 | Yes, with attribution | Yes, with attribution and change notice | Accept after content/provenance review |
| CC BY-SA | Yes, subject to terms | Only if derivatives and distribution comply with ShareAlike | Quarantine until propagation is implemented |
| Any NC license | Possibly within current personal use | Depends on other terms | Quarantine; avoid future event/distribution ambiguity |
| Any ND license | Unmodified sharing only | No | Reject from remix pipeline |
| Missing, custom, or ambiguous license | Unclear | Unclear | Reject until manually resolved |
| Public-domain assertion | Possibly | Possibly | Require work, edition, translation, illustration, narration, and jurisdiction review |

The [CC BY 4.0 deed](https://creativecommons.org/licenses/by/4.0/) permits sharing
and adaptation, including commercially, but requires appropriate credit, a link
to the license, and an indication of changes. It does not guarantee clearance of
privacy, publicity, moral, trademark, cultural, or other rights. The
[CC0 deed](https://creativecommons.org/publicdomain/zero/1.0/) waives copyright to
the extent legally possible but provides no warranty and does not necessarily
clear other rights.

Do not infer that a folktale is unrestricted. A modern translation, retelling,
illustration, edited edition, or narration can have independent rights even when
the underlying tale is old.

Traditional, Indigenous, sacred, or culturally sensitive works should default to
`remix_allowed=false` unless the source and a culturally appropriate human review
support adaptation. Formal legal permission is a floor, not the complete decision.

### Canada and US public-domain handling

The cart operates in Canada and the GitHub repository is currently private, but
downloadable artifacts may still cross borders or later be redistributed. A
conservative classics policy should require both Canadian and US clearance, or
an explicit worldwide license, before content is committed or redistributed.

- Canada's current [Copyright Act section 6](https://laws-lois.justice.gc.ca/eng/acts/C-42/section-6.html)
  generally provides life of the author plus the remainder of the death year and
  70 years. The [CIPO copyright guide](https://ised-isde.canada.ca/site/canadian-intellectual-property-office/en/guide-copyright)
  explains that the extension effective 2022-12-30 did not revive works whose
  Canadian copyright had already expired. A known single-author work by an author
  who died no later than 1971 is a useful conservative starting heuristic, not a
  complete clearance test; joint, anonymous, unpublished, translated, and artistic
  works can differ.
- The [US Copyright Office overview](https://copyright.gov/what-is-copyright/)
  states that works published in the United States before 1931 are currently in
  the public domain. [Circular 15A](https://www.copyright.gov/circs/circ15a.pdf)
  provides more detailed duration rules. Publication country, renewal, edition,
  translation, and component works still matter.

### Attribution and adaptation records

For a CC BY story, a short spoken ending can say: “Adapted by Neko from *Title*
by Author, CC BY 4.0.” The full local credit view must retain the canonical source,
license URI, publisher, author, illustrator, translator, funder/donor when
required, and a plain-language list of changes. Attribution may be adapted to the
medium, but it must not imply upstream endorsement.

Every generated remix must be recorded as an adaptation with its parent item,
source license, change summary, generation policy/model revision, and output hash.
The LLM must never invent or decide rights metadata.

## Ingestion, storage, and security

### Reusable components

Use established tools instead of building a library platform:

- Calibre CLI for one-shot administrative inspection and conversion. Current
  documentation lists `ebook-meta`, `ebook-convert`, and `calibredb` in the
  [Calibre command-line interface](https://manual.calibre-ebook.com/en/generated/en/cli-index.html).
  It does not need to remain resident.
- [W3C/DAISY EPUBCheck](https://www.w3.org/publishing/epubcheck/) 5.3.0 for EPUB
  conformance. Structural validation does not establish copyright or child safety.
- [SQLite FTS5](https://www.sqlite.org/fts5.html) for local full-text search over
  titles, tags, reading level, duration, and story-card summaries. Curated French
  and Spanish synonyms/tags can support discovery without a resident embedding
  model or vector database.
- [Audiobookshelf](https://audiobookshelf.org/docs/documentation/introduction/)
  only if later requirements justify a UI for pre-rendered audiobooks, progress,
  and library APIs. It does not solve live remix, provenance, or policy enforcement
  and would add an always-running service and media dependencies.

### Proposed pipeline

1. Discover only through documented official APIs, catalogs, or curated manual
   downloads.
2. Fetch an immutable original plus the upstream item page/JSON rights snapshot.
3. Record the source URL, upstream ID/revision/ETag where available, fetch time,
   size, media type, and SHA-256 before transformation.
4. Treat EPUB, H5P, and other archive formats as hostile input. Reject path
   traversal, absolute paths, symlinks, excessive entry counts, oversized
   decompression ratios, encrypted members, malformed MIME declarations, scripts,
   and unexpected executable content. Apply download and unpack size limits.
5. Run structural validation. Never render upstream active content or allow it to
   make network requests.
6. Apply the license/attribution gate before extracting or generating runtime
   material.
7. Extract only allowlisted, normalized UTF-8 text and necessary metadata. Skip
   illustrations for the audio-first release unless each image's rights and use
   are independently recorded.
8. Perform human rights, editorial, cultural, and age review. Check stereotypes,
   outdated language, frightening or violent material, sensitive themes, and
   source-specific adaptation expectations.
9. Create an approved story card containing characters/roles, six to twelve plot
   beats, age/reading level, expected duration, safe editable slots, immutable plot
   or moral elements, pronunciation hints, and content warnings.
10. Index approved metadata and story cards in SQLite FTS5. Raw content and
    normalized artifacts remain outside Git.
11. Build a reproducible manifest and attribution record. Only approved versions
    become visible to the runtime.

Do not parse or transform a download under the privileged boot-service account.
Use a bounded administrative ingestion environment, publish immutable approved
artifacts, and let the runtime read only that approved store. Runtime content
should never contain executable instructions for the assistant supervisor.

### Minimum provenance schema

Each story/version needs at least:

- Internal immutable UUID and version.
- Provider, upstream item ID, canonical page URL, download URL, retrieval UTC,
  upstream revision/ETag/last-modified value, and saved rights snapshot.
- Original and current language as BCP 47 tags; title; edition; translation,
  adaptation, and parent-work relationships.
- Every contributor with role and source identifier: author, adaptor, illustrator,
  translator, narrator, editor, publisher, donor, and funder as applicable.
- Exact license identifier and URI, the upstream rights statement, jurisdiction
  evidence for public-domain claims, and normalized flags for adaptation,
  commercial use, ShareAlike, and attribution requirements.
- Rights reviewer, review date, reasoning, and any use restrictions.
- Raw SHA-256, normalized-text hash, media type, sizes, and storage paths.
- Reading/age band, topics, intended duration, content warnings, cultural notes,
  human content reviewer, and review date.
- English/French/Spanish validation state and the modes enabled for that version.
- Story-card schema/policy version, editable slots, immutable elements, and
  pronunciation data.
- For generated material: exact model/artifact/runtime revision, prompt-template
  and policy versions, parent story/version, requested and applied slot changes,
  generation timestamp, output hash, safety results, human approval if retained,
  and attribution/change statement.

Personal values such as a child's name should not enter this durable schema by
default. Session substitutions remain in memory and expire; saved favorites use
placeholders unless an adult explicitly approves retention.

## Child-directed remix behavior

### Deterministic mode

Name, setting, companion-animal, and harmless-object changes should normally use
curator-defined slots rather than an LLM. This is faster, reproducible, easier to
translate, and less likely to disturb the plot or lesson. A slot includes allowed
values, grammar features, pronunciation, references that must co-vary, and any
age/cultural constraints.

For French and Spanish, naive string replacement can break agreement, gender,
articles, or pronouns. Use curator-approved role/name sets with grammatical
features, or generate a candidate and require language-aware validation.

### Generative mode with Gemma 4 E2B

The official [Gemma 4 E2B model card](https://huggingface.co/google/gemma-4-E2B-it)
identifies creative text as an intended use and reports multilingual capability,
but it also documents limitations in nuance, reasoning, and factual reliability.
Those limitations matter in a child-facing storytelling system.

Neko's validated local server currently uses a 2,048-token context despite the
model family's larger theoretical context. The measured CPU fallback produced
approximately 14.7 decode tokens per second. A long story generated before
playback would therefore violate the desired interaction latency.

Use these constraints:

- Prefer source stories that measure at **300 seconds or less** with the exact
  approved local voice, speaking rate, pauses, attribution, and interaction
  cues. The lane word ranges above are curation heuristics, never permission for
  a longer telling.
- Give the model a compact reviewed story card, not the complete library or an
  unbounded transcript.
- Generate one bounded scene or paragraph, approximately 100--200 words or less,
  while carrying only compact plot state and fixed rights/safety constraints.
- Acknowledge the request immediately with approved local speech. Neko can begin
  an approved opening while preparing the next scene, but it must never speak
  unchecked generated tokens.
- Complete and evaluate an entire candidate scene before TTS. Generate ahead
  while the preceding approved scene is playing.
- Disable optional reasoning/thinking if benchmarks confirm that doing so reduces
  delay without unacceptable quality loss.
- Cache approved variants on NVMe with generic placeholders instead of child
  names. Rehydrate personal substitutions locally for the current session.
- Convert requests for copyrighted franchise characters or real-person imitation
  into generic archetypes, such as “a young wizard at a magical school,” rather
  than imitating protected characters or living people.

For the first multilingual release, prefer existing human translations over live
machine translation. English generative remix should mature first, then French,
then Spanish. The owner has
accepted an explicitly labeled **lower-assurance prototype** in which French and
Spanish outputs receive language-specific tests plus independent LLM review when
no fluent human is available. Record the reviewing model/prompt/result, never
describe that as fluent-human validation, retain validated local fallback
stories, and disable a language if field testing shows material errors.

## Local safety and child protections

The main protection is a deterministic policy and bounded story representation,
not another generative model. The allowed-slot layer should constrain the request
before generation; then a separate checker evaluates both the request and complete
candidate output. If generation, safety checking, or TTS preparation times out,
crashes, or is uncertain, use the approved original or a fixed template.

An optional defense-in-depth candidate is
[Qwen3Guard-Gen-0.6B](https://huggingface.co/Qwen/Qwen3Guard-Gen-0.6B), whose
official [release description](https://qwenlm.github.io/blog/qwen3guard/) presents
it as an Apache-2.0 multilingual prompt/response classifier. It must be benchmarked
in a quantized, sequential or on-demand configuration on this 8 GB Jetson before
installation. It is not sufficient as the sole safety control.

Always reject or safely redirect requests involving:

- Sexual content, grooming, or romantic/sexual child roleplay.
- Graphic violence, self-harm encouragement, or suicide methods.
- Hate or dehumanization.
- Drugs, weapons, dangerous challenges, or operational wrongdoing.
- Requests for secrets from caregivers or collection of personal data.
- Medical, legal, or emergency advice presented as professional guidance.
- Instructions embedded in source material that attempt to override runtime
  policy or operate devices.

For the first release, reject scary presentation, predation threat, graphic or
celebratory violence, serious death/grief, and sustained peril even when they
are mild by adult standards. Keep tone light. Reviewed, respectful
religion/folklore and age-appropriate conflict are allowed. Mild silliness can
include bathroom humour, but extreme or sustained bathroom humour is excluded;
none of these permissions bypasses the non-scary gate.

Neko should explicitly identify itself as an AI kitty cart. Its warmth and
motherly character must not become a claim that it is human, a caregiver, a
professional, a child's only friend, or an entity that needs loyalty. It should
not promise secrecy, use guilt, encourage emotional dependency, or infer a child's
age from a camera or voice. A caregiver configures the age band.

A distress disclosure should initially use a fixed compassionate response that
encourages the child to tell a nearby trusted adult. Automatic owner notification
would create additional privacy and consent requirements and needs a separate
decision.

Current guidance reviewed:

- [UNICEF Guidance on AI and Children, version 3](https://www.unicef.org/innocenti/reports/policy-guidance-ai-children)
- [UNICEF, When AI Becomes a Friend: Child Rights Risks](https://www.unicef.org/documents/when-ai-becomes-friend-child-rights-risks)
- [UNICEF business recommendations for child-facing AI](https://www.unicef.org/media/181136/file/UNICEF-When-AI-becomes-friend-Business-recommendations-2026.pdf)
- [NIST Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)

Before child deployment, red-team English, French, and Spanish behavior including
slang and obfuscation, source-text prompt injection, grooming/secrecy, self-harm,
sexual requests, hate, dangerous challenges, copyrighted characters, and attempts
to make Neko claim human status. A human adult must sign off on the release set.

## Privacy and optional online enhancement

The first story release does not require a cloud model. There must be no runtime
route capable of sending audio or images off the cart. A separately billed,
text-only API route is nevertheless authorized when an adult-authenticated mode,
visible online indicator, redaction, destination allowlist, strict spend/rate
limits, short timeout, and immediate local fallback are all active. Cloud loss,
credential failure, quota exhaustion, and provider rejection must all produce
the equivalent local request or an approved original-story fallback.

If a later cloud text path is enabled, send only a bounded, redacted request:

- Story ID and compact story card/beat needed for the current scene.
- Requested safe slots and style controls.
- Opaque placeholders in place of names, school, contact information, precise
  location, or other personal details.
- No raw audio, image, complete transcript, source-book archive, or unrelated
  conversation history.

Reinsert placeholder values locally. Apply the same local output safety gate
before TTS. Use a provider/destination allowlist, TLS, short deadlines, bounded
retries, a circuit breaker, and structured audit records that omit user text.
Network access is an enhancement, never a prerequisite.

Child names and session choices should be memory-only with a short TTL by default.
An adult-authenticated action can save a placeholder-based favorite. Do not retain
full child transcripts. If a future feature can transmit audio or images, each
transfer must show an adult exactly what payload, provider, and purpose are being
authorized and require contemporaneous confirmation. A blanket settings toggle is
not adequate human-in-the-loop consent.

Unauthenticated child activation of cloud mode remains disabled. An authorized
adult may enable the bounded text-only route for a session or configured mode;
the active state and spend must remain visible, and the adult can revoke it
immediately. Owner-run cloud pre-generation remains the lowest-risk first use.
Use a keyed switch or locked-compartment control as the default local authority.
Remote activation requires authenticated administration, automatic expiry,
visible cart-side indication and local revocation.

## Z.AI and OpenAI subscription/API findings

The owner's existing consumer/developer subscriptions are useful for research,
curation, coding, and owner-operated pre-generation. They are not embedded-runtime
API entitlements.

### Z.AI

The [Z.AI Coding Plan subscription terms](https://docs.z.ai/legal-agreement/subscription-terms)
state that the plan is personal to one natural person and prohibit using it as a
general API for applications, bots, websites, or SaaS. The
[API introduction](https://docs.z.ai/api-reference/introduction) distinguishes
coding-tool endpoints from the general application endpoint. A deployed Neko
integration must use the separately funded general API, currently documented at
`https://api.z.ai/api/paas/v4`, rather than automating Claude Code or sharing the
Coding Plan credential.

Z.AI's [API pricing](https://docs.z.ai/guides/overview/pricing) and recharge path
are separate from the Coding Plan. Its [API terms](https://docs.z.ai/legal-agreement/terms-of-use)
allow application integration but assign the application operator responsibility
for end-user notice/consent, safety, privacy, and disclosure. Those terms said API
end-user content was not used to improve models unless the customer opted in at
the review date; this setting and the terms must be rechecked before deployment.

### OpenAI/Codex

OpenAI documents that [ChatGPT subscriptions and API billing are separate](https://help.openai.com/en/articles/8156019-how-can-i-move-my-chatgpt-subscription-to-the-api).
The consumer [Terms of Use](https://openai.com/policies/terms-of-use/) prohibit
sharing account credentials and programmatically extracting output from the
consumer service. The [Services Agreement](https://openai.com/policies/services-agreement/)
supports API use in customer applications while assigning the operator obligations
for its end users, including guardian consent where applicable. The current
[Usage Policies](https://openai.com/policies/usage-policies/) add protections for
minors.

Therefore Neko must use a separately billed OpenAI API project if OpenAI is chosen
for runtime enhancement. It must not automate the owner's Codex/ChatGPT
subscription as the cart's backend.

### Runtime provider policy

For either provider:

- Use a dedicated application credential stored through a secrets mechanism, not
  in Git, `AGENTS.md`, logs, or service unit text.
- Enforce spend/rate limits and a hard response deadline.
- Make the active local/online mode visible and log mode changes without child
  content.
- Obtain required adult/guardian authorization before a child-facing live request.
- Apply local redaction before upload and local safety checks after download.
- Review current terms, data residency/retention, opt-out controls, and any DPA
  before activation.
- Treat provider failure or policy refusal as ordinary degraded operation, not an
  exceptional condition that can silence Neko.

## Phased rollout

### Phase 0: policy and data model

- Approve the license matrix, cultural policy, age bands, safety boundaries,
  provenance schema, local storage location, and retention rules.
- Add corpus paths to Git ignore rules before downloading content.
- Define adult administration and review/signoff procedures.
- Do not add cloud credentials yet.

### Phase 1: approved local originals and deterministic remix

- Curate the 30-work cat-only pilot: 16 works in the 5–7 presentation lane, 14
  in 8–10, and at least 18 centered on wild, extinct, or mythical cats. Target 14
  publisher/editor-reviewed StoryWeaver works discoverable through GDL, 10
  ASb-approved works, and 6 individually cleared public-domain works/tales;
  translations are versions, not extra works.
- Expand toward approximately 60–100 only after the pilot's rights, review,
  ingestion, narration, safety, and offline tests pass. Set the EN/FR/ES version
  split from actual licensed translations and fluent reviewer capacity rather
  than a quota.
- Ship original telling, deterministic editable slots, local catalog search, local
  TTS, attribution, and hard offline tests.
- Enforce a maximum `duration_seconds` of 300 and the light/non-scary content gate
  on every enabled original, deterministic variant, and generated scene sequence.

### Phase 2: English local generative remix

- Create reviewed beat/story cards.
- Add bounded Gemma scene generation and generation-ahead scheduling.
- Evaluate deterministic rules plus Qwen3Guard-Gen-0.6B or another measured local
  classifier.
- Cache only reviewed or successfully policy-checked placeholder variants.
- Complete adversarial testing and retain immediate original-story fallback.

### Phase 3: French first, then Spanish remix

- Prefer human translations already present in approved catalogs.
- Add language-specific grammar metadata, policy rules, test prompts, and fluent
  human review when available. For the owner-accepted prototype bridge, record
  independent LLM review and label the result lower-assurance.
- Do not expose live translation/remix merely because the base model claims the
  language.

### Phase 4: optional text-only cloud

- Start with owner-operated pre-generation and local approval.
- Provision only a separately billed Z.AI general API or OpenAI API account;
  require adult authentication, a visible online state, destination allowlist,
  and hard spend/rate limits.
- Transmit only redacted bounded text, keep short timeouts, and use the identical
  local output guard and fallback.

### Phase 5: classics and audiobook options

- Add dual-jurisdiction-cleared Faded Page/Project Gutenberg works after editorial
  review.
- Add individually cleared LibriVox recordings only if exact human narration is
  useful.
- Consider Audiobookshelf only if its library/progress UI justifies its footprint.

## Acceptance criteria

- Every enabled story has a canonical source, exact license URI, full contributor
  attribution, original and normalized hashes, rights reviewer, and content
  reviewer.
- Every enabled story centers a feline and carries structured felid/fiction,
  genre, cultural origin, age lane, duration, content flags, pronunciation, and
  immutable-elements metadata. The pilot meets its 16/14 age-lane and
  18-work wild/extinct/mythical-cat balance.
- Missing, ambiguous, and ND content cannot enter the remix path. SA/NC content is
  quarantined unless a later approved policy handles its obligations.
- A child explicitly selects original, deterministic change, or generative remix.
- No generated text reaches TTS before the complete scene passes required checks.
- A checker/model crash, timeout, unavailable network, invalid API key, quota
  exhaustion, or provider refusal produces a useful local fallback.
- Every retained generated version links to its parent, license, changes, model,
  runtime, prompt/policy revisions, safety result, and output hash.
- Every telling is no longer than 300 seconds and passes the light/non-scary gate.
- Allowed conflict and folklore/religion remain age-appropriate and respectful;
  serious grief and extreme bathroom humour fail the first-release gate.
- French and Spanish runtime content records either fluent-human validation or
  the owner-accepted, explicitly lower-assurance LLM-only prototype review path.
- Network packet-capture testing confirms that the story feature sends only
  allowlisted, redacted text JSON and has no audio/image egress path.
- Session deletion and retention tests prove that child names and transient choices
  expire as configured.
- Full credits are accessible locally; if the owner approves spoken attribution,
  its brief ending is included in the measured 300-second limit.

## Remaining owner decisions

1. Is the proposed 30-work pilot and 8/9/6/4/3 shelf balance acceptable, and
   what English/French balance should precede the lower-priority Spanish shelf?
2. Which exact keyed/locked local adult control and authenticated remote-admin
   mechanism should be used, and what per-session/daily spend cap and visible
   online-state indicator should they control?
3. Should child names and settings always be session-only by default, and who may
   save a favorite variant?
4. Should Neko offer the same “original / change names or place / surprise-safe
   remix” menu every time, or remember a session preference?
5. May the first release strictly exclude NC, SA, and ND material despite its
   current personal/noncommercial use?
6. Will story corpus artifacts ever be distributed from the project Git repository
   or carried across the US border? The recommended default is to keep all blobs
   outside Git and clear classics for both Canada and the US.
7. Is a brief spoken attribution at the end of each story acceptable?
8. Should traditional, Indigenous, and sacred stories always be original-only
    unless a source and cultural reviewer explicitly approve adaptation?
9. When might fluent French and Spanish review replace or audit the accepted
    lower-assurance prototype path?
10. Should a distress disclosure only prompt the child to tell a nearby trusted
    adult, or should Neko notify the owner? Notification materially changes the
    privacy design.
