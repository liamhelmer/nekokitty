# Third-party notices

The repository's original Neko-authored code and documentation are licensed
under the root [MIT License](LICENSE). External software, model weights, copied
agent skills, story content, and generated inference artifacts retain their own
licences and are not relicensed by the root licence.

Current notable boundaries:

- `.agents/skills/jetson-diagnostic` is an NVIDIA-authored Agent Skill under
  Apache-2.0; its own `LICENSE` controls that directory.
- Gemma 4, Nemotron/Audex, ZipDepth and their dependencies retain the terms and
  notices recorded in `AGENTS.md` and the linked research/operations ledger.
- LiquidAI LFM2.5-1.2B-Instruct GGUF weights are installed externally under the
  LFM Open 1.0 terms. They are not distributed by this repository or relicensed
  under MIT. The normal server uses an external digest-pinned NVIDIA llama.cpp
  container; its own notices remain controlling.
- The sherpa-onnx runtime is Apache-2.0. The separately downloaded Nemotron 3.5
  streaming ASR export is derived from NVIDIA model weights under OpenMDW-1.1;
  it is an external runtime artifact and is not covered by this repository's MIT
  licence.
- The external Silero VAD ONNX artifact is from the MIT-licensed Silero VAD
  project. The sherpa-onnx 3M bilingual open-vocabulary keyword archive is also
  installed only as an external evaluation artifact; it is not distributed by
  this repository. Confirm its model-specific redistribution terms before ever
  packaging it. Exact sources and hashes are in the setup log.
- Supertonic's Python code is MIT, while the separately downloaded Supertonic 3
  weights are BigScience OpenRAIL-M. Built-in voice-style data and generated
  audio remain subject to the upstream model terms and applicable voice rights.
- No model weights, ONNX models, TensorRT plans, voice profiles, story corpus, or
  generated media are distributed in this repository.
- RF-DETR's Apache-2.0 code and Apache-designated model weights may be evaluated
  as external dependencies without changing Neko's MIT licence.
- MeowLLM source and the separately downloaded `hunt3rx99/meowllm` checkpoint
  are identified as MIT by their upstream repository/model card. They remain
  external artifacts, are not distributed here, and are not covered by Neko's
  root licence merely by being installed locally. Exact revisions and hashes are
  recorded in `AGENTS.md` and the setup log.
- KittenTTS 0.8.1 code and the separately downloaded KittenTTS Mini, Micro, and
  Nano INT8 0.8 ONNX/voice artifacts are identified as Apache-2.0 upstream. They
  remain external; Neko's local minimal-offline patch does not relicense them.
  Exact wheel/model revisions and hashes are in the setup log.
- Piper 1.4.2 is GPL-3.0-or-later and is executed as a separate local service.
  The external Lessac medium voice files retain the terms recorded in their
  upstream model card and training-data notices. Neither Piper nor the voice
  model is covered by Neko's MIT licence, and neither is distributed here.
- CatMeows 1.0.2 is an external University of Milan dataset. Zenodo identifies
  CC BY 4.0 and the authors additionally state scientific-research/
  non-commercial use and acknowledgement terms. It is not distributed in this
  repository and no recording is yet approved as a Neko playback asset.
- The owner-curated library began as 24 external Freesound assets. Twenty
  reviewed `keep_*` originals are distributed unchanged under
  `assets/cat-sounds/originals`: eleven CC0 1.0, three CC BY 4.0, two CC BY-NC
  3.0, and four CC BY-NC 4.0. The six noncommercial recordings are usable here
  only within the owner's personal/noncommercial scope. The root MIT licence
  does not apply to any of these recordings or their derivatives. Exact
  attribution, source/license URLs, decisions, and SHA-256 values are in
  `assets/cat-sounds/manifest.json` and the maintained Cat Sounds Master.
- Twenty-five lossless bench derivatives from seven of those sources are under
  `assets/cat-sounds/derived`: ten CC0 1.0 files, fourteen CC BY 4.0 files, and
  one CC BY-NC 3.0 file. They retain the source terms, modification notices, and
  TASL credits in `assets/cat-sounds/ATTRIBUTION.md` and
  `assets/cat-sounds/derived/manifest.json`. They are not MIT-licensed, do not
  imply creator endorsement, and remain disabled pending derived listening and
  output-hardware acceptance.
- Stable Audio 3 Small SFX source/runtime and selected optimized weights are
  installed externally as a stopped research profile after owner acceptance.
  Its weights use the Stability AI Community License and include T5Gemma
  components under the Gemma terms. Nothing is distributed in this repository,
  and the failed quality evaluation excludes generated audio from revision-one
  child-facing playback.
- Ultralytics code and trained YOLO models are AGPL-3.0 by default according to
  Ultralytics' current licence guidance. An isolated local benchmark does not
  make them MIT. Selecting YOLO26 as an integrated distributed dependency
  requires an AGPL-compatible project distribution or a separate Ultralytics
  commercial licence; do not commit YOLO weights or represent them as MIT.

Before adding or distributing a dependency or asset, record its exact revision,
source, licence, checksum, and required attribution in the project ledger.
