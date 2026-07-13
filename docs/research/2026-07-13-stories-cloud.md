# Offline-first story library and optional cloud enhancement

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
- English is required; French and Spanish are desirable.
- A child decides whether a story is altered.
- Text may leave the cart under policy. Audio and images may leave only with
  explicit human-in-the-loop consent.
- Existing Z.AI and Codex subscriptions may be used for development, but their
  suitability for an embedded runtime must be evaluated separately.
- Neko should be cute, motherly, playful, and a little mischievous, without
  presenting itself as a human caregiver.
- A few seconds of interaction latency is acceptable, but a child should receive
  immediate acknowledgment while a longer response is prepared.

No story corpus, ingestion software, safety model, cloud API, or related service
was installed as part of this research.

## Recommendation

The first release should contain a human-curated collection of approximately
60--100 short stories carrying either `CC0-1.0` or `CC-BY-4.0`. Use the Global
Digital Library as the main machine-readable source, then supplement it with
selected StoryWeaver and African Storybook titles. Do not expose an upstream
catalog wholesale merely because a title has an acceptable license; every
runtime-visible item also needs rights, attribution, age/content, and cultural
review.

Every story should offer three clearly distinct modes, chosen by the child:

1. **Original:** tell the approved text without generative rewriting.
2. **Change a few things:** make deterministic substitutions only in
   curator-defined slots such as character names, setting, or a harmless object.
3. **Surprise-safe remix:** use Gemma to rewrite one bounded scene at a time from
   an approved story card, then check the entire scene before sending it to TTS.

Neko must never silently convert an original telling into a remix. If adaptation
is not permitted for a particular story, it should offer the original or another
adaptable story instead.

Keep content blobs outside the public Git repository, provisionally under
`/var/lib/neko/stories`. The project repository should contain ingestion code,
schemas, manifests, hashes, review records, and deployment configuration, but not
source content unless its redistribution rights have been individually verified.

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

The cart operates in Canada, while a public GitHub repository and downloadable
artifacts can be accessed globally. A conservative classics policy should require
both Canadian and US clearance, or an explicit worldwide license, before content
is committed or redistributed.

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

- Prefer short source stories of roughly 300--900 words.
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
machine translation. English generative remix should mature first. French and
Spanish generation require fluent-human review, language-specific policy tests,
and validated fallback stories before becoming child-visible.

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

Mild scares, sadness, death, conflict, religion/folklore, and bathroom humor need
owner-configured age-band rules rather than a universal assumption.

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

The first story release does not need a cloud model. There should be no runtime
route capable of sending audio or images off the cart. Cloud loss, credential
failure, quota exhaustion, and provider rejection must all produce the equivalent
local request or an approved original-story fallback.

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

Live child-facing cloud use should remain disabled until an adult/guardian policy,
age handling, retention terms, provider configuration, and consent UX are approved.
Owner-run cloud pre-generation followed by local human review is the safer first
online enhancement.

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

- Curate approximately 60--100 GDL, StoryWeaver, and ASb CC BY/CC0 stories.
- A provisional split is 60 English, 20 French, and 20 Spanish; revise based on
  child age, desired duration, and available human reviewers.
- Ship original telling, deterministic editable slots, local catalog search, local
  TTS, attribution, and hard offline tests.

### Phase 2: English local generative remix

- Create reviewed beat/story cards.
- Add bounded Gemma scene generation and generation-ahead scheduling.
- Evaluate deterministic rules plus Qwen3Guard-Gen-0.6B or another measured local
  classifier.
- Cache only reviewed or successfully policy-checked placeholder variants.
- Complete adversarial testing and retain immediate original-story fallback.

### Phase 3: French and Spanish remix

- Prefer human translations already present in approved catalogs.
- Add language-specific grammar metadata, policy rules, test prompts, and fluent
  human review.
- Do not expose live translation/remix merely because the base model claims the
  language.

### Phase 4: optional text-only cloud

- Start with owner-operated pre-generation and local approval.
- If live use is justified, provision a separate Z.AI general API or OpenAI API
  account and adult-enabled mode.
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
- Missing, ambiguous, and ND content cannot enter the remix path. SA/NC content is
  quarantined unless a later approved policy handles its obligations.
- A child explicitly selects original, deterministic change, or generative remix.
- No generated text reaches TTS before the complete scene passes required checks.
- A checker/model crash, timeout, unavailable network, invalid API key, quota
  exhaustion, or provider refusal produces a useful local fallback.
- Every retained generated version links to its parent, license, changes, model,
  runtime, prompt/policy revisions, safety result, and output hash.
- French and Spanish runtime content has fluent-human validation.
- Network packet-capture testing confirms that the story feature sends only
  allowlisted, redacted text JSON and has no audio/image egress path.
- Session deletion and retention tests prove that child names and transient choices
  expire as configured.
- Attribution is spoken briefly and full credits are accessible locally.

## Remaining owner decisions

1. What child age bands and reading levels should the first collection target?
2. Should the default lengths be approximately two, five, and ten minutes, or a
   different set?
3. What initial story count and English/French/Spanish split are preferred?
4. Is an adult/guardian normally present, and would an adult PIN or phone approval
   be acceptable for any live cloud child session?
5. Should child names and settings always be session-only by default, and who may
   save a favorite variant?
6. What are the boundaries for mild scares, death/grief, conflict,
   religion/folklore, and bathroom humor? What themes are absolute exclusions?
7. Should Neko offer the same “original / change names or place / surprise-safe
   remix” menu every time, or remember a session preference?
8. May the first release strictly exclude NC, SA, and ND material despite its
   current personal/noncommercial use?
9. Will story corpus artifacts ever be distributed from the public Git repository
   or carried across the US border? The recommended default is to keep all blobs
   outside Git and clear classics for both Canada and the US.
10. Is a brief spoken attribution at the end of each story acceptable?
11. Should traditional, Indigenous, and sacred stories always be original-only
    unless a source and cultural reviewer explicitly approve adaptation?
12. Who can perform fluent French and Spanish quality/safety review?
13. Should a distress disclosure only prompt the child to tell a nearby trusted
    adult, or should Neko notify the owner? Notification materially changes the
    privacy design.
14. Is the owner willing to fund separate runtime API usage, since neither the
    Z.AI Coding Plan nor the Codex/ChatGPT subscription licenses embedded use?
15. Should the first online release be limited to owner-run pre-generation, with
    live child-cloud interaction deferred?
