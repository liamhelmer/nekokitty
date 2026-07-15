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
- The sherpa-onnx runtime is Apache-2.0. The separately downloaded Nemotron 3.5
  streaming ASR export is derived from NVIDIA model weights under OpenMDW-1.1;
  it is an external runtime artifact and is not covered by this repository's MIT
  licence.
- Supertonic's Python code is MIT, while the separately downloaded Supertonic 3
  weights are BigScience OpenRAIL-M. Built-in voice-style data and generated
  audio remain subject to the upstream model terms and applicable voice rights.
- No model weights, ONNX models, TensorRT plans, voice profiles, story corpus, or
  generated media are distributed in this repository.
- RF-DETR's Apache-2.0 code and Apache-designated model weights may be evaluated
  as external dependencies without changing Neko's MIT licence.
- Ultralytics code and trained YOLO models are AGPL-3.0 by default according to
  Ultralytics' current licence guidance. An isolated local benchmark does not
  make them MIT. Selecting YOLO26 as an integrated distributed dependency
  requires an AGPL-compatible project distribution or a separate Ultralytics
  commercial licence; do not commit YOLO weights or represent them as MIT.

Before adding or distributing a dependency or asset, record its exact revision,
source, licence, checksum, and required attribution in the project ledger.
