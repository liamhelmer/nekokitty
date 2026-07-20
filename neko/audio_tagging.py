"""Small offline audio-tagging adapter for deterministic sound reflexes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class AudioTagResult:
    """The only scores the interaction policy needs from the 527-class model."""

    top_label: str
    top_score: float
    meow_score: float


def should_meow_back(
    transcript: str,
    result: AudioTagResult,
    *,
    meow_threshold: float = 0.10,
) -> bool:
    """Apply the owner's deliberately permissive human-meow response rule."""

    if transcript.strip():
        return False
    return result.meow_score > meow_threshold or result.top_label in {
        "Music",
        "Mantra",
    }


class AudioTagger:
    """Run sherpa-onnx's small INT8 AudioSet Zipformer on one VAD segment."""

    def __init__(
        self,
        model_path: Path,
        labels_path: Path,
        *,
        num_threads: int = 2,
    ) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(f"audio-tagging model is missing: {model_path}")
        if not labels_path.is_file():
            raise FileNotFoundError(f"audio-tagging labels are missing: {labels_path}")

        import sherpa_onnx

        config = sherpa_onnx.AudioTaggingConfig(
            model=sherpa_onnx.AudioTaggingModelConfig(
                zipformer=sherpa_onnx.OfflineZipformerAudioTaggingModelConfig(
                    model=str(model_path),
                ),
                num_threads=num_threads,
                debug=False,
                provider="cpu",
            ),
            labels=str(labels_path),
            # Returning all labels makes the explicit Meow score available even
            # when a human imitation ranks far below Speech or Mantra.
            top_k=527,
        )
        if not config.validate():
            raise ValueError("invalid audio-tagging configuration")
        self._tagger = sherpa_onnx.AudioTagging(config)

    def classify(
        self,
        samples: Iterable[float],
        *,
        sample_rate: int = 16_000,
    ) -> AudioTagResult:
        waveform = [float(value) for value in samples]
        if not waveform:
            raise ValueError("cannot tag empty audio")
        stream = self._tagger.create_stream()
        stream.accept_waveform(sample_rate=sample_rate, waveform=waveform)
        events = self._tagger.compute(stream)
        if not events:
            raise RuntimeError("audio tagger returned no events")
        scores = {event.name: float(event.prob) for event in events}
        return AudioTagResult(
            top_label=str(events[0].name),
            top_score=float(events[0].prob),
            meow_score=scores.get("Meow", 0.0),
        )
