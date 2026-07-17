#!/usr/bin/env python3
"""Run Neko's local always-listening, wake-gated, interruptible voice loop.

The microphone stream and speech segments remain in memory. No audio or
transcript is written to disk. Run with the dedicated sherpa-onnx ASR Python
environment documented in ``docs/operations/setup-log.md``.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import json
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.behavior import BehaviorController, normalize_phrase  # noqa: E402
from neko.events import (  # noqa: E402
    Acknowledge,
    CancelAudio,
    DialogueRequest,
    SetMuted,
    SpeakText,
    TranscriptEvent,
)
from neko.gemma_client import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    ConversationHistory,
    GemmaClient,
)
from neko.tts_protocol import TtsClient  # noqa: E402
from scripts.neko_asr_transcribe import (  # noqa: E402
    DEFAULT_MODEL as DEFAULT_ASR_MODEL,
    build_recognizer,
    pcm16_to_float,
    read_wav,
)


DEFAULT_VAD_MODEL = Path("/home/neko/models/sherpa-onnx-vad/silero_vad.onnx")
DEFAULT_KWS_MODEL = Path(
    "/home/neko/models/sherpa-onnx-kws/"
    "sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20"
)
DEFAULT_KEYWORDS = Path(__file__).resolve().parents[1] / "config/asr/neko-keywords.txt"
DEFAULT_TTS_SOCKET = Path("/run/neko/tts-fast.sock")
SAMPLE_RATE = 16_000
VAD_WINDOW_SAMPLES = 512
VAD_WINDOW_BYTES = VAD_WINDOW_SAMPLES * 2


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    samples: tuple[float, ...]
    captured_at_s: float
    wake_detected: bool = False
    sleep_detected: bool = False
    sequence: int = 0
    transcript: str = ""
    asr_steps: int = 0
    asr_finalize_seconds: float = 0.0


class ContinuousSpeechInput:
    """Own an ALSA capture process and emit Silero-finalized speech segments."""

    def __init__(
        self,
        device: str,
        vad: object,
        keyword_spotter: object,
        recognizer: object,
        language: str,
        on_speech_start: Callable[[], None],
        on_wake: Callable[[], None],
        *,
        queue_size: int = 8,
    ) -> None:
        self.device = device
        self.vad = vad
        self.keyword_spotter = keyword_spotter
        self.keyword_stream = keyword_spotter.create_stream()
        self.recognizer = recognizer
        self.language = language
        self.on_speech_start = on_speech_start
        self.on_wake = on_wake
        self.segments: queue.Queue[SpeechSegment] = queue.Queue(maxsize=queue_size)
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()
        self.finished_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.process: subprocess.Popen[bytes] | None = None
        self.error: BaseException | None = None
        self.speech_sequence = 0
        self._was_speech = False
        self._wake_for_segment = False
        self._sleep_for_segment = False
        self._asr_pre_roll: deque[tuple[float, ...]] = deque(maxlen=16)
        self._asr_stream: object | None = None
        self._asr_steps = 0

    def start(self) -> None:
        if self.thread is not None:
            raise RuntimeError("speech input is already started")
        self.thread = threading.Thread(target=self._run, name="neko-audio-capture", daemon=True)
        self.thread.start()
        if not self.ready_event.wait(5):
            raise RuntimeError("microphone capture did not become ready")
        if self.error is not None:
            raise RuntimeError(f"microphone capture failed: {self.error}")

    def close(self) -> None:
        self.stop_event.set()
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
        if self.thread is not None:
            self.thread.join(timeout=3)
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=2)

    def _put_segment(
        self,
        samples: tuple[float, ...],
        wake_detected: bool,
        sleep_detected: bool,
        transcript: str,
        asr_steps: int,
        asr_finalize_seconds: float,
    ) -> None:
        if not samples:
            return
        segment = SpeechSegment(
            samples,
            time.monotonic(),
            wake_detected,
            sleep_detected,
            self.speech_sequence,
            transcript,
            asr_steps,
            asr_finalize_seconds,
        )
        try:
            self.segments.put_nowait(segment)
        except queue.Full:
            # Fresh speech is more useful than stale queued turns.
            try:
                self.segments.get_nowait()
            except queue.Empty:
                pass
            self.segments.put_nowait(segment)

    def _decode_asr_ready(self) -> int:
        stream = self._asr_stream
        if stream is None:
            return 0
        steps = 0
        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)
            steps += 1
        self._asr_steps += steps
        return steps

    def _start_streaming_asr(self) -> None:
        self._asr_stream = self.recognizer.create_stream()
        self._asr_stream.set_option("language", self.language)
        self._asr_steps = 0
        for frame in self._asr_pre_roll:
            self._asr_stream.accept_waveform(SAMPLE_RATE, frame)
            self._decode_asr_ready()

    def _finish_streaming_asr(self) -> tuple[str, int, float]:
        stream = self._asr_stream
        if stream is None:
            return "", 0, 0.0
        started = time.monotonic()
        stream.input_finished()
        self._decode_asr_ready()
        text = self.recognizer.get_result_all(stream).text.strip()
        elapsed = time.monotonic() - started
        steps = self._asr_steps
        self._asr_stream = None
        self._asr_steps = 0
        return text, steps, elapsed

    def _accept_samples(self, samples: list[float]) -> None:
        self.vad.accept_waveform(samples)
        self.keyword_stream.accept_waveform(SAMPLE_RATE, samples)
        while self.keyword_spotter.is_ready(self.keyword_stream):
            self.keyword_spotter.decode_stream(self.keyword_stream)
            detected = self.keyword_spotter.get_result(self.keyword_stream)
            if detected:
                if detected.startswith("SLEEP_"):
                    self._sleep_for_segment = True
                else:
                    self._wake_for_segment = True
                    self.on_wake()
                self.keyword_spotter.reset_stream(self.keyword_stream)
        is_speech = bool(self.vad.is_speech_detected())
        speech_started = is_speech and not self._was_speech
        self._asr_pre_roll.append(tuple(samples))
        if speech_started:
            self.speech_sequence += 1
            self._start_streaming_asr()
            self.on_speech_start()
        elif self._asr_stream is not None:
            self._asr_stream.accept_waveform(SAMPLE_RATE, samples)
            self._decode_asr_ready()
        self._was_speech = is_speech
        while not self.vad.empty():
            segment_samples = tuple(float(value) for value in self.vad.front.samples)
            transcript, asr_steps, asr_finalize_seconds = self._finish_streaming_asr()
            self._put_segment(
                segment_samples,
                self._wake_for_segment,
                self._sleep_for_segment,
                transcript,
                asr_steps,
                asr_finalize_seconds,
            )
            self._wake_for_segment = False
            self._sleep_for_segment = False
            self.vad.pop()

    def _run(self) -> None:
        command = [
            "/usr/bin/arecord",
            "--quiet",
            "--device",
            self.device,
            "--format",
            "S16_LE",
            "--rate",
            str(SAMPLE_RATE),
            "--channels",
            "1",
            "--file-type",
            "raw",
            "-",
        ]
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            assert self.process.stdout is not None
            self.ready_event.set()
            while not self.stop_event.is_set():
                raw = self.process.stdout.read(VAD_WINDOW_BYTES)
                if not raw:
                    if self.process.poll() is not None and not self.stop_event.is_set():
                        detail = b""
                        if self.process.stderr is not None:
                            detail = self.process.stderr.read()
                        raise RuntimeError(
                            detail.decode("utf-8", errors="replace").strip()
                            or f"arecord exited {self.process.returncode}"
                        )
                    continue
                if len(raw) != VAD_WINDOW_BYTES:
                    continue
                self._accept_samples(pcm16_to_float(raw))
        except BaseException as error:
            self.error = error
            self.ready_event.set()


class ReplaySpeechInput(ContinuousSpeechInput):
    """Replay private WAV fixtures through the real detector at wall-clock speed."""

    def __init__(
        self,
        paths: list[Path],
        vad: object,
        keyword_spotter: object,
        recognizer: object,
        language: str,
        on_speech_start: Callable[[], None],
        on_wake: Callable[[], None],
        speaking: threading.Event,
    ) -> None:
        super().__init__(
            "private-replay",
            vad,
            keyword_spotter,
            recognizer,
            language,
            on_speech_start,
            on_wake,
        )
        self.paths = paths
        self.speaking = speaking

    def _run(self) -> None:
        try:
            self.ready_event.set()
            for index, path in enumerate(self.paths):
                if index:
                    if not self.speaking.wait(timeout=90):
                        raise RuntimeError("timed out waiting for Neko playback before replay")
                    if self.stop_event.wait(0.35):
                        return
                rate, samples = read_wav(path)
                if rate != SAMPLE_RATE:
                    raise ValueError(f"replay WAV must be 16 kHz: {path}")
                for start in range(0, len(samples), VAD_WINDOW_SAMPLES):
                    if self.stop_event.is_set():
                        return
                    frame = samples[start : start + VAD_WINDOW_SAMPLES]
                    self._accept_samples(frame)
                    if self.stop_event.wait(len(frame) / SAMPLE_RATE):
                        return
                # Complete Silero's trailing-silence requirement while keeping
                # the replay timing equivalent to a real paused speaker.
                for _ in range(25):
                    if self.stop_event.is_set():
                        return
                    self._accept_samples([0.0] * VAD_WINDOW_SAMPLES)
                    if self.stop_event.wait(VAD_WINDOW_SAMPLES / SAMPLE_RATE):
                        return
            self.finished_event.set()
        except BaseException as error:
            self.error = error
            self.finished_event.set()
            self.ready_event.set()


def build_vad(
    model: Path,
    *,
    threshold: float,
    min_silence_s: float,
    min_speech_s: float,
    max_speech_s: float,
) -> object:
    import sherpa_onnx

    silero = sherpa_onnx.SileroVadModelConfig(
        model=str(model),
        threshold=threshold,
        min_silence_duration=min_silence_s,
        min_speech_duration=min_speech_s,
        window_size=VAD_WINDOW_SAMPLES,
        max_speech_duration=max_speech_s,
    )
    config = sherpa_onnx.VadModelConfig(
        silero_vad=silero,
        sample_rate=SAMPLE_RATE,
        num_threads=1,
        provider="cpu",
    )
    if not silero.validate() or not config.validate():
        raise RuntimeError("invalid Silero VAD configuration")
    return sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=30)


def build_keyword_spotter(
    model: Path,
    keywords: Path,
    *,
    score: float,
    threshold: float,
) -> object:
    import sherpa_onnx

    return sherpa_onnx.KeywordSpotter(
        tokens=str(model / "tokens.txt"),
        encoder=str(model / "encoder-epoch-13-avg-2-chunk-16-left-64.int8.onnx"),
        decoder=str(model / "decoder-epoch-13-avg-2-chunk-16-left-64.onnx"),
        joiner=str(model / "joiner-epoch-13-avg-2-chunk-16-left-64.int8.onnx"),
        keywords_file=str(keywords),
        num_threads=1,
        max_active_paths=4,
        keywords_score=score,
        keywords_threshold=threshold,
        num_trailing_blanks=1,
        provider="cpu",
    )


class VoiceAssistant:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.shutdown = threading.Event()
        self.cancel_speech = threading.Event()
        self.speaking = threading.Event()
        self.controller = BehaviorController()
        self.history = ConversationHistory(
            max_turns=args.history_turns,
            max_characters=args.history_characters,
        )
        self.gemma = GemmaClient(
            base_url=args.base_url,
            model=args.model,
            timeout_s=args.gemma_timeout,
        )
        self.tts = TtsClient(socket_path=args.tts_socket)
        self.current_segment_sequence = 0
        self.current_audio_samples: tuple[float, ...] = ()
        self.current_vad_finalized_s = 0.0
        load_started = time.monotonic()
        self.recognizer = build_recognizer(args.asr_model, args.asr_threads)
        vad = build_vad(
            args.vad_model,
            threshold=args.vad_threshold,
            min_silence_s=args.min_silence_seconds,
            min_speech_s=args.min_speech_seconds,
            max_speech_s=args.max_speech_seconds,
        )
        keyword_spotter = build_keyword_spotter(
            args.kws_model,
            args.keywords,
            score=args.keywords_score,
            threshold=args.keywords_threshold,
        )
        self.model_load_seconds = time.monotonic() - load_started
        if args.replay_wav:
            self.audio = ReplaySpeechInput(
                args.replay_wav,
                vad,
                keyword_spotter,
                self.recognizer,
                args.language,
                self._on_speech_start,
                self._on_wake,
                self.speaking,
            )
        else:
            self.audio = ContinuousSpeechInput(
                args.device,
                vad,
                keyword_spotter,
                self.recognizer,
                args.language,
                self._on_speech_start,
                self._on_wake,
            )

    def _event(self, kind: str, **values: object) -> None:
        print(json.dumps({"event": kind, **values}, ensure_ascii=False), flush=True)

    def _on_speech_start(self) -> None:
        if self.speaking.is_set():
            self.cancel_speech.set()
            self._event("barge_in_detected")

    def _on_wake(self) -> None:
        self._event("wake_keyword_detected")

    def _speak(self, text: str, *, vad_finalized_s: float | None = None) -> bool:
        if self.args.no_speak:
            self._event("reply", text=text)
            return True
        self.cancel_speech.clear()
        self.speaking.set()

        def first_pcm() -> None:
            now = time.monotonic()
            values: dict[str, object] = {}
            if vad_finalized_s is not None:
                after_finalize = now - vad_finalized_s
                values = {
                    "from_vad_finalize_seconds": round(after_finalize, 3),
                    "estimated_from_speech_end_seconds": round(
                        after_finalize + self.args.min_silence_seconds,
                        3,
                    ),
                    "vad_tail_seconds": self.args.min_silence_seconds,
                }
            self._event("first_pcm_written", **values)

        try:
            try:
                result = self.tts.synthesize(
                    text,
                    play=True,
                    cancel_event=self.cancel_speech,
                    on_first_pcm=first_pcm,
                )
            except Exception as error:
                self._event("tts_error", message=str(error))
                return False
        finally:
            self.speaking.clear()
        cancelled = bool(result.get("cancelled"))
        self._event("playback_cancelled" if cancelled else "playback_complete")
        return not cancelled

    def _dialogue(self, request: DialogueRequest) -> bool:
        started = time.monotonic()
        try:
            if self.args.llm_route == "audio":
                answer = self.gemma.reply_audio(
                    self.current_audio_samples,
                    SAMPLE_RATE,
                    request.text,
                    request.language,
                    self.history,
                )
            else:
                answer = self.gemma.reply_first_sentence(
                    request.text,
                    request.language,
                    self.history,
                )
        except Exception as error:
            self._event("llm_error", message=str(error))
            self._speak("Oops, my thoughts got tangled. Try that once more?")
            return False
        self._event(
            "reply_ready",
            latency_seconds=round(time.monotonic() - started, 3),
            route=self.args.llm_route,
            **({"text": answer} if self.args.verbose_transcripts else {}),
        )

        # If another utterance already began while Gemma was thinking, do not
        # talk over it. Preserve the unanswered prompt and process the queued
        # speech next.
        if self.audio.speech_sequence != self.current_segment_sequence:
            self.history.append_interrupted(request.text, request.language)
            self._event("reply_superseded_before_playback")
            return False

        completed = self._speak(answer, vad_finalized_s=self.current_vad_finalized_s)
        if completed:
            self.history.append(request.text, answer, request.language)
        else:
            self.history.append_interrupted(request.text, request.language)
        return completed

    def _handle_segment(self, segment: SpeechSegment) -> bool:
        text = segment.transcript
        if not text and not segment.wake_detected and not segment.sleep_detected:
            self._event("empty_transcript")
            return False
        language = self.args.language if self.args.language != "auto" else "unknown"
        if text:
            self._event(
                "transcript",
                audio_seconds=round(len(segment.samples) / SAMPLE_RATE, 3),
                asr_finalize_seconds=round(segment.asr_finalize_seconds, 3),
                steps=segment.asr_steps,
                streaming=True,
                **({"text": text} if self.args.verbose_transcripts else {}),
            )
        else:
            self._event(
                "keyword_only_command",
                command="sleep" if segment.sleep_detected else "wake",
            )
        was_active = self.controller.session_active
        self.current_segment_sequence = segment.sequence
        self.current_audio_samples = segment.samples
        self.current_vad_finalized_s = segment.captured_at_s
        policy_text = text
        if segment.sleep_detected:
            policy_text = "bye bye"
        elif segment.wake_detected and not was_active:
            normalized = normalize_phrase(text)
            recognized_wake = (
                normalized.startswith("neko neko")
                or normalized.startswith("eko neko")
                or normalized.startswith("echo neko")
                or normalized.startswith("echo necho")
                or normalized.startswith("eko necho")
                or normalized == "neko"
                or normalized.startswith("neko ")
            )
            if not recognized_wake:
                policy_text = f"Neko Neko {text}"
        actions = self.controller.handle(
            TranscriptEvent(policy_text, language, segment.captured_at_s)  # type: ignore[arg-type]
        )
        if not was_active and self.controller.session_active:
            self.history.clear()
            self._event("session_started")
        dialogue_seen = False
        for action in actions:
            if isinstance(action, Acknowledge):
                self._event("wake_acknowledged")
                if not any(isinstance(item, DialogueRequest) for item in actions):
                    self._speak("Mrrp?")
            elif isinstance(action, DialogueRequest):
                dialogue_seen = True
                self._dialogue(action)
            elif isinstance(action, CancelAudio):
                self.cancel_speech.set()
                self.history.clear()
                self._event("audio_cancelled", reason=action.reason)
            elif isinstance(action, SetMuted):
                self._event("muted", value=action.muted)
            elif isinstance(action, SpeakText):
                self._speak(action.text)
        return dialogue_seen

    def run(self) -> int:
        if not self.gemma.ready():
            raise RuntimeError("local LLM is not ready")
        self.audio.start()
        self._event(
            "ready",
            asr_load_seconds=round(self.model_load_seconds, 3),
            device=self.args.device,
            media_retained=False,
            replay=bool(self.args.replay_wav),
            wake_phrase="Neko Neko",
            llm_model=self.args.model,
            llm_route=self.args.llm_route,
            tts_socket=str(self.args.tts_socket),
        )
        handled_dialogues = 0
        try:
            while not self.shutdown.is_set():
                if self.audio.error is not None:
                    raise RuntimeError(f"audio capture failed: {self.audio.error}")
                try:
                    segment = self.audio.segments.get(timeout=0.2)
                except queue.Empty:
                    if self.audio.finished_event.is_set():
                        return 0
                    continue
                if self._handle_segment(segment):
                    handled_dialogues += 1
                    if self.args.max_dialogues and handled_dialogues >= self.args.max_dialogues:
                        return 0
        finally:
            self.cancel_speech.set()
            self.audio.close()
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="plughw:CARD=Webcam,DEV=0")
    parser.add_argument(
        "--replay-wav",
        type=Path,
        action="append",
        default=[],
        help="private 16 kHz mono WAV; later clips wait for playback and barge in",
    )
    parser.add_argument("--language", choices=("auto", "en", "fr", "es"), default="en")
    parser.add_argument("--asr-model", type=Path, default=DEFAULT_ASR_MODEL)
    parser.add_argument("--asr-threads", type=int, choices=range(1, 7), default=4)
    parser.add_argument("--vad-model", type=Path, default=DEFAULT_VAD_MODEL)
    parser.add_argument("--kws-model", type=Path, default=DEFAULT_KWS_MODEL)
    parser.add_argument("--keywords", type=Path, default=DEFAULT_KEYWORDS)
    parser.add_argument("--keywords-score", type=float, default=1.5)
    parser.add_argument("--keywords-threshold", type=float, default=0.1)
    parser.add_argument("--vad-threshold", type=float, default=0.25)
    parser.add_argument("--min-silence-seconds", type=float, default=0.6)
    parser.add_argument("--min-speech-seconds", type=float, default=0.2)
    parser.add_argument("--max-speech-seconds", type=float, default=20.0)
    parser.add_argument("--history-turns", type=int, default=6)
    parser.add_argument("--history-characters", type=int, default=2400)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--llm-route",
        choices=("streaming-text", "audio"),
        default="streaming-text",
    )
    parser.add_argument("--gemma-timeout", type=float, default=60.0)
    parser.add_argument("--tts-socket", type=Path, default=DEFAULT_TTS_SOCKET)
    parser.add_argument("--no-speak", action="store_true")
    parser.add_argument("--verbose-transcripts", action="store_true")
    parser.add_argument("--max-dialogues", type=int, default=0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.asr_model.is_dir():
        raise FileNotFoundError(f"ASR model not found: {args.asr_model}")
    if not args.vad_model.is_file():
        raise FileNotFoundError(f"VAD model not found: {args.vad_model}")
    if not args.kws_model.is_dir():
        raise FileNotFoundError(f"keyword model not found: {args.kws_model}")
    if not args.keywords.is_file():
        raise FileNotFoundError(f"keywords file not found: {args.keywords}")
    for replay in args.replay_wav:
        if not replay.is_file():
            raise FileNotFoundError(f"replay WAV not found: {replay}")
    if not 0 < args.vad_threshold < 1:
        raise ValueError("VAD threshold must be between zero and one")
    assistant = VoiceAssistant(args)

    def stop(_signum: int, _frame: object) -> None:
        assistant.shutdown.set()
        assistant.cancel_speech.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    return assistant.run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error
