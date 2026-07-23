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
import random
import re
import signal
import subprocess
import sys
import threading
import time
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neko.behavior import BehaviorController, normalize_phrase  # noqa: E402
from neko.audio_tagging import AudioTagger, should_meow_back  # noqa: E402
from neko.events import (  # noqa: E402
    Acknowledge,
    CancelAudio,
    DialogueRequest,
    SetMuted,
    SpeakText,
    TranscriptEvent,
)
from neko.event_schedule import (  # noqa: E402
    EventSchedule,
    is_schedule_query,
    is_schedule_refinement,
    requests_all_results,
)
from neko.cat_audio import (  # noqa: E402
    CatAudioDenied,
    CatSoundCatalog,
    CatSoundPart,
    CatSoundPlayer,
    CatSoundSelection,
    TextPart,
    parse_audio_script,
)
from neko.gemma_client import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    ConversationHistory,
    GemmaClient,
)
from neko.online_jobs import (  # noqa: E402
    ConnectivityMonitor,
    CodexOnlineJobRunner,
    OFFLINE_REPLY,
    OnlineCommand,
    OnlineJobResult,
    parse_online_command,
)
from neko.local_commands import (  # noqa: E402
    LocalCommand,
    check_services,
    parse_local_command,
    primary_ip_address,
    request_reboot,
    speakable_ip_address,
)
from neko.story_library import RecordedStory, StoryLibrary  # noqa: E402
from neko.story_recording_rebuild import enqueue_story_rebuild  # noqa: E402
from neko.tts_protocol import NEKO_NAME_RE, TtsClient  # noqa: E402
from neko.tts_chunking import chunk_text, is_sentence_boundary  # noqa: E402
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
DEFAULT_TTS_SOCKET = Path("/run/neko/tts.sock")
DEFAULT_AUDIO_TAGGING_MODEL = Path(
    "/home/neko/models/sherpa-onnx-zipformer-small-audio-tagging-2024-04-15/"
    "model.int8.onnx"
)
DEFAULT_AUDIO_TAGGING_LABELS = DEFAULT_AUDIO_TAGGING_MODEL.with_name(
    "class_labels_indices.csv"
)
ATTENDED_CAT_SOUND_ALLOWLIST = (
    Path(__file__).resolve().parents[1]
    / "config/cat-sounds/attended-headphone-allowlist.json"
)
PRODUCTION_CAT_SOUND_ALLOWLIST = (
    Path(__file__).resolve().parents[1] / "config/cat-sounds/runtime-allowlist.json"
)
SAMPLE_RATE = 16_000
VAD_WINDOW_SAMPLES = 512
VAD_WINDOW_BYTES = VAD_WINDOW_SAMPLES * 2
MAX_WAKE_PREFIX_SECONDS = 2.0
PURR_WORD_RE = re.compile(
    r"\bp+u+r+(?:s|ed|ing|y|fect(?:ly)?)?\b",
    re.IGNORECASE,
)
REQUEST_FAILURE_REPLY = (
    "Oops! I'm not sure what happened, but I wasn't able to do that. "
    "Maybe next time."
)
REBOOT_ACKNOWLEDGEMENT = "OK, going to have a quick power nap now!"
REBOOT_FAILURE_REPLY = "Oops! I couldn't start my power nap. Please check me manually."


def wake_is_in_prefix_window(speech_frames_seen: int) -> bool:
    """Accept KWS as an address only near the beginning of active speech."""

    elapsed = speech_frames_seen * VAD_WINDOW_SAMPLES / SAMPLE_RATE
    return speech_frames_seen > 0 and elapsed <= MAX_WAKE_PREFIX_SECONDS


WAKE_ADDRESS_TOKENS = {
    "neko", "nekko", "nico", "niko", "nikko", "neco", "eko", "echo", "necho",
}


def canonicalize_wake_transcript(text: str) -> str:
    """Use accepted KWS evidence to replace noisy leading name renderings."""

    tokens = normalize_phrase(text).split()
    removed = 0
    while tokens and removed < 2 and tokens[0] in WAKE_ADDRESS_TOKENS:
        tokens.pop(0)
        removed += 1
    remainder = " ".join(tokens)
    return f"Neko {remainder}".strip()


def is_addressed_stop_transcript(text: str) -> bool:
    """Recognize a narrow ASR fallback when the dedicated stop KWS misses."""

    tokens = normalize_phrase(text).split()
    removed = 0
    while tokens and removed < 2 and tokens[0] in WAKE_ADDRESS_TOKENS:
        tokens.pop(0)
        removed += 1
    if removed == 0:
        return False
    if tokens and tokens[0] == "please":
        tokens.pop(0)
    return tokens == ["stop"]


def is_double_addressed_transcript(text: str) -> bool:
    tokens = normalize_phrase(text).split()
    return len(tokens) >= 2 and all(
        token in WAKE_ADDRESS_TOKENS for token in tokens[:2]
    )


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    samples: tuple[float, ...]
    captured_at_s: float
    wake_detected: bool = False
    sleep_detected: bool = False
    stop_detected: bool = False
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
        on_wake: Callable[[str], bool | None],
        on_stop: Callable[[], None],
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
        self.on_stop = on_stop
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
        self._stop_for_segment = False
        self._speech_frames_seen = 0
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
        stop_detected: bool,
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
            stop_detected,
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
        is_speech = bool(self.vad.is_speech_detected())
        speech_started = is_speech and not self._was_speech
        if speech_started:
            self._speech_frames_seen = 1
        elif is_speech:
            self._speech_frames_seen += 1
        while self.keyword_spotter.is_ready(self.keyword_stream):
            self.keyword_spotter.decode_stream(self.keyword_stream)
            detected = self.keyword_spotter.get_result(self.keyword_stream)
            if detected:
                if detected.startswith("STOP_"):
                    self._stop_for_segment = True
                    self.on_stop()
                elif detected.startswith("SLEEP_"):
                    self._sleep_for_segment = True
                elif wake_is_in_prefix_window(self._speech_frames_seen):
                    accepted = self.on_wake(detected)
                    if accepted is not False:
                        self._wake_for_segment = True
                self.keyword_spotter.reset_stream(self.keyword_stream)
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
                self._stop_for_segment,
                transcript,
                asr_steps,
                asr_finalize_seconds,
            )
            self._wake_for_segment = False
            self._sleep_for_segment = False
            self._stop_for_segment = False
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
        on_wake: Callable[[str], bool | None],
        on_stop: Callable[[], None],
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
            on_stop,
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
        self.cancel_cat_sound = threading.Event()
        self.cancel_tail_purr = threading.Event()
        self.cancel_work_purr = threading.Event()
        self.speaking = threading.Event()
        self.spoken_turn_active = threading.Event()
        self.story_playing = threading.Event()
        self.story_followup_pending = threading.Event()
        self.story_interrupt_armed = threading.Event()
        self.self_wake_guard = threading.Event()
        self.ignored_story_sequences: set[int] = set()
        self.cat_sound_playing = threading.Event()
        self.tail_purr_playing = threading.Event()
        self._thinking_sound_thread: threading.Thread | None = None
        self._tail_purr_thread: threading.Thread | None = None
        self._work_purr_thread: threading.Thread | None = None
        self._cue_rng = random.SystemRandom()
        self._meow_back_output_windows: deque[tuple[float, float]] = deque(maxlen=8)
        self.story_library = StoryLibrary()
        self.event_schedule = EventSchedule()
        self.pending_schedule_query: str | None = None
        self.pending_schedule_base_query: str | None = None
        self.last_story_id: str | None = None
        self.online_results: queue.Queue[OnlineJobResult] = queue.Queue()
        self.active_online_command: OnlineCommand | None = None
        self.online_monitor = ConnectivityMonitor(
            interval_s=args.connectivity_interval,
            on_change=self._on_online_mode_change,
        )
        self.online_jobs = CodexOnlineJobRunner(
            self.online_results.put,
            timeout_s=args.online_job_timeout,
        )
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
        self.cat_sounds = CatSoundCatalog(
            allowlist_path=(
                ATTENDED_CAT_SOUND_ALLOWLIST
                if args.attended_cat_sounds
                else PRODUCTION_CAT_SOUND_ALLOWLIST
            ),
            attended_bench_test=args.attended_cat_sounds,
        )
        self.cat_sound_player = CatSoundPlayer(
            {
                "speaker": args.cat_speaker_target,
                "body_transducer": args.cat_transducer_target,
            }
        )
        tagger_load_started = time.monotonic()
        self.audio_tagger: AudioTagger | None = None
        self._audio_tagger_error_type: str | None = None
        if args.meow_back_enabled:
            try:
                self.audio_tagger = AudioTagger(
                    args.audio_tagging_model,
                    args.audio_tagging_labels,
                    num_threads=args.audio_tagging_threads,
                )
            except Exception as error:
                # Conversation remains useful if this optional reflex cannot
                # load. Log only the exception type; paths/details stay local.
                self._audio_tagger_error_type = type(error).__name__
        self.audio_tagger_load_seconds = time.monotonic() - tagger_load_started
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
                self._on_stop,
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
                self._on_stop,
            )

    def _maybe_meow_back(self, segment: SpeechSegment) -> bool:
        """Answer a likely human meow without waking the LLM conversation."""

        segment_end = segment.captured_at_s
        segment_start = segment_end - len(segment.samples) / SAMPLE_RATE
        if any(
            segment_start <= output_end and segment_end >= output_start
            for output_start, output_end in self._meow_back_output_windows
        ):
            self._event("meow_back_self_audio_ignored", sequence=segment.sequence)
            return False
        tagger = self.audio_tagger
        if tagger is None:
            return False
        try:
            result = tagger.classify(segment.samples, sample_rate=SAMPLE_RATE)
        except Exception as error:
            self._event("audio_tagging_error", error_type=type(error).__name__)
            # Fail quiet after a runtime fault rather than repeatedly spending
            # CPU and emitting errors for ambient VAD segments.
            self.audio_tagger = None
            return False
        self._event(
            "audio_tagging_result",
            top_label=result.top_label,
            top_score=round(result.top_score, 4),
            meow_score=round(result.meow_score, 4),
            audio_seconds=round(len(segment.samples) / SAMPLE_RATE, 3),
        )
        if not should_meow_back(
            segment.transcript,
            result,
            meow_threshold=self.args.meow_back_threshold,
        ):
            return False
        try:
            selection = self.cat_sounds.select(
                "meow_reply",
                self.args.cat_sound_output,
                autonomous=True,
                # A new qualifying human vocalization may receive a new answer.
                # Selection still avoids immediately repeating the same asset.
                enforce_cooldown=False,
            )
        except CatAudioDenied as error:
            self._event("cat_sound_fallback", action="meow_reply", reason=str(error))
            return False
        if selection.duration_seconds > 10.0:
            self._event("meow_back_denied", reason="duration_limit")
            return False
        if self.args.no_speak:
            self._event(
                "meow_back_selected",
                asset_id=selection.asset_id,
                trigger=result.top_label,
            )
            return True
        self.cancel_cat_sound.clear()
        self.speaking.set()
        self.cat_sound_playing.set()
        output_started = time.monotonic()
        try:
            played = self.cat_sound_player.play(
                selection,
                cancel_event=self.cancel_cat_sound,
                on_started=lambda: self._event(
                    "meow_back_started",
                    asset_id=selection.asset_id,
                    trigger=result.top_label,
                ),
            )
            if not played:
                self._event("meow_back_interrupted", asset_id=selection.asset_id)
                return False
            self.cat_sounds.mark_played(selection)
            self._event("meow_back_complete", asset_id=selection.asset_id)
            return True
        finally:
            # VAD finalization trails the audible sound. Retaining the actual
            # overlap interval plus a short tail prevents Neko's recorded meow
            # from recursively triggering itself on an open speaker/microphone.
            self._meow_back_output_windows.append(
                (output_started - 0.1, time.monotonic() + 1.0)
            )
            self.cat_sound_playing.clear()
            self.speaking.clear()

    def _event(self, kind: str, **values: object) -> None:
        print(json.dumps({"event": kind, **values}, ensure_ascii=False), flush=True)

    def _on_online_mode_change(self, online: bool) -> None:
        self._event("online_mode_changed", online=online, probe="ping_8.8.8.8_c2")

    def _handle_local_command(self, command: LocalCommand) -> bool:
        """Execute a bounded local command without consulting or retaining LLM state."""

        self._stop_thinking_cue_for_speech()
        self._stop_tail_purr_for_neko_speech()
        if command.kind == "ip_address":
            address = primary_ip_address()
            answer = (
                f"My IP address is {speakable_ip_address(address)}."
                if address is not None
                else "I couldn't find my IP address right now."
            )
            self._event("local_command", command="ip_address", available=address is not None)
            completed = self._speak(answer, vad_finalized_s=self.current_vad_finalized_s)
        elif command.kind == "online":
            online = self.online_monitor.probe_once()
            self._event("local_command", command="online", online=online)
            answer = "Yep, I'm online!" if online else "Nope, I'm offline right now."
            completed = self._speak(answer, vad_finalized_s=self.current_vad_finalized_s)
        elif command.kind == "health":
            report = check_services()
            self._event(
                "local_command",
                command="health",
                healthy=report.healthy,
                problems=[
                    {"unit": problem.unit, "issue": problem.issue}
                    for problem in report.problems
                ],
            )
            completed = self._speak(
                report.spoken_text(),
                vad_finalized_s=self.current_vad_finalized_s,
            )
        elif command.kind == "reboot":
            self._event("local_command", command="reboot", phase="acknowledging")
            completed = self._speak(
                REBOOT_ACKNOWLEDGEMENT,
                vad_finalized_s=self.current_vad_finalized_s,
            )
            if not completed:
                self._event("reboot_cancelled_before_request")
                return False
            self._event("local_command", command="reboot", phase="requesting")
            if not request_reboot():
                self._event("reboot_request_failed")
                self._speak(REBOOT_FAILURE_REPLY)
                return False
            return True
        else:
            raise ValueError(f"unsupported local command: {command.kind}")
        if completed:
            self.controller.extend_active_session(time.monotonic())
        return completed

    def _on_speech_start(self) -> None:
        if self.spoken_turn_active.is_set():
            sequence = self.audio.speech_sequence
            if self.story_interrupt_armed.is_set():
                self.story_followup_pending.set()
            else:
                self.ignored_story_sequences.add(sequence)
                self._event("output_nonwake_speech_ignored", sequence=sequence)
                return
            self.cancel_speech.set()
            self._event("barge_in_detected")

    def _on_wake(self, keyword: str = "") -> bool:
        strong_address = keyword.startswith(("NEKO_NEKO", "ASR_NEKO_NEKO"))
        if (
            self.spoken_turn_active.is_set()
            and self.self_wake_guard.is_set()
            and not strong_address
        ):
            self._event("self_wake_echo_ignored")
            return False
        if self.spoken_turn_active.is_set():
            self.story_interrupt_armed.set()
            self.story_followup_pending.set()
            self.cancel_speech.set()
            self._event("addressed_barge_in_armed")
        self._event("wake_keyword_detected")
        return True

    def _on_stop(self) -> None:
        """Cancel every output immediately; the finalized segment closes state."""

        self.cancel_speech.set()
        self.cancel_cat_sound.set()
        self.cancel_tail_purr.set()
        self.cancel_work_purr.set()
        self.online_jobs.cancel()
        self.active_online_command = None
        self._event("stop_keyword_detected")

    def _thinking_cue_action(self, text: str) -> str | None:
        """Choose a short, local acknowledgement before an LLM reply starts."""

        rate = self.args.thinking_cue_rate
        if rate <= 0 or self._cue_rng.random() >= rate:
            return None
        normalized = normalize_phrase(text)
        if any(word in normalized for word in ("thank", "thanks", "merci", "gracias")):
            return "meow_thank_you"
        if any(word in normalized for word in ("like neko", "love neko", "love you")):
            return "purr_playful_affection"
        return "meow_general"

    def _response_cue_action(self, request_text: str, answer: str) -> str | None:
        """Select a varied mid-reply cue when the model omitted one itself."""

        if any(isinstance(part, CatSoundPart) for part in parse_audio_script(answer)):
            return None
        is_story = "story" in normalize_phrase(request_text)
        if not is_story and (
            self.args.response_cue_rate <= 0
            or self._cue_rng.random() >= self.args.response_cue_rate
        ):
            return None
        normalized = normalize_phrase(f"{request_text} {answer}")
        if any(word in normalized for word in ("thank", "thanks", "merci", "gracias")):
            return "meow_thank_you"
        return "meow_general"

    @staticmethod
    def _audio_cue_count(text: str, *, max_markers: int = 3) -> int:
        return sum(
            isinstance(part, CatSoundPart)
            for part in parse_audio_script(text, max_markers=max_markers)
        )

    def _insert_response_cue(self, request_text: str, answer: str) -> str:
        """Place a semantic real-cat cue between sentences, never as a preamble."""

        action = self._response_cue_action(request_text, answer)
        if action is None:
            return answer
        marker = {
            "meow_general": "[meow]",
            "meow_thank_you": "[meow:thanks]",
            "purr_short": "[purr]",
            "purr_relaxing_short": "[purr:relaxed]",
            "purr_playful_affection": "[purr:playful]",
        }[action]
        for index in range(len(answer)):
            if is_sentence_boundary(answer, index):
                remainder = answer[index + 1 :].lstrip()
                if remainder:
                    return f"{answer[: index + 1]} {marker} {remainder}"
        # A one-sentence reply remains uninterrupted rather than acquiring the
        # old, deterministic pre-answer meow.
        return answer

    @staticmethod
    def _warm_tail_purr(request_text: str, answer: str) -> bool:
        normalized = normalize_phrase(f"{request_text} {answer}")
        return "story" in normalized or any(
            phrase in normalized
            for phrase in ("like neko", "love neko", "love you", "you are nice")
        )

    @staticmethod
    def _answer_mentions_purr(answer: str) -> bool:
        """Treat purr words and purr cue tags as a post-speech purr request."""

        return PURR_WORD_RE.search(answer) is not None

    @staticmethod
    def _has_tail_purr_marker(answer: str) -> bool:
        return any(
            isinstance(part, CatSoundPart) and part.action == "purr_primary"
            for part in parse_audio_script(answer)
        )

    def _should_start_tail_purr(self, request_text: str, answer: str) -> bool:
        if self._has_tail_purr_marker(answer):
            return False
        if self._answer_mentions_purr(answer):
            return True
        return (
            self._warm_tail_purr(request_text, answer)
            and self._audio_cue_count(answer) < 3
        )

    def _start_tail_purr(self) -> None:
        """Start a long post-speech purr; child speech intentionally does not stop it."""

        try:
            selection = self.cat_sounds.select(
                "purr_primary", self.args.cat_sound_output, autonomous=True
            )
        except CatAudioDenied as error:
            self._event("cat_sound_fallback", action="purr_primary", reason=str(error))
            return
        self.cancel_tail_purr.clear()

        def play() -> None:
            self.tail_purr_playing.set()
            try:
                played = self.cat_sound_player.play(
                    selection,
                    cancel_event=self.cancel_tail_purr,
                    on_started=lambda: self._event(
                        "tail_purr_started", asset_id=selection.asset_id
                    ),
                )
                if played:
                    self.cat_sounds.mark_played(selection)
                    self._event("tail_purr_complete", asset_id=selection.asset_id)
                else:
                    self._event("tail_purr_interrupted", asset_id=selection.asset_id)
            except Exception as error:
                self._event("cat_sound_error", action="purr_primary", message=str(error))
            finally:
                self.tail_purr_playing.clear()

        self._tail_purr_thread = threading.Thread(
            target=play, name="neko-tail-purr", daemon=True
        )
        self._tail_purr_thread.start()

    def _stop_tail_purr_for_neko_speech(self) -> None:
        """Only Neko's next reply (or an explicit command) ends a tail purr."""

        self.cancel_tail_purr.set()
        thread = self._tail_purr_thread
        if thread is not None:
            thread.join(timeout=1)
        self._tail_purr_thread = None

    def _start_work_purr(self) -> None:
        """Loop a local purr for the full lifetime of a long online job."""

        thread = self._work_purr_thread
        if thread is not None and thread.is_alive():
            return
        try:
            selection = self.cat_sounds.select(
                "purr_primary",
                self.args.cat_sound_output,
                autonomous=True,
                # A deliberate work-state loop must start even if an ordinary
                # happy tail purr finished moments before the online command.
                enforce_cooldown=False,
            )
        except CatAudioDenied as error:
            self._event("cat_sound_fallback", action="purr_primary", reason=str(error))
            return
        self.cancel_work_purr.clear()

        def play_loop() -> None:
            self.cat_sound_playing.set()
            self.speaking.set()
            self._event("online_job_purr_started", asset_id=selection.asset_id)
            try:
                while not self.cancel_work_purr.is_set():
                    played = self.cat_sound_player.play(
                        selection,
                        cancel_event=self.cancel_work_purr,
                    )
                    if not played:
                        break
                    self.cat_sounds.mark_played(selection)
            except Exception as error:
                self._event("cat_sound_error", action="purr_primary", message=str(error))
            finally:
                self.cat_sound_playing.clear()
                self.speaking.clear()
                self._event("online_job_purr_stopped", asset_id=selection.asset_id)

        self._work_purr_thread = threading.Thread(
            target=play_loop,
            name="neko-online-job-purr",
            daemon=True,
        )
        self._work_purr_thread.start()

    def _stop_work_purr(self) -> None:
        self.cancel_work_purr.set()
        thread = self._work_purr_thread
        if thread is not None:
            thread.join(timeout=1)
        self._work_purr_thread = None

    def _speak_online_job_status(self) -> bool:
        command = self.active_online_command
        if command is None:
            return False
        self._stop_work_purr()
        completed = self._speak(
            f"I'm working on your request to {command.status_description}."
        )
        if self.active_online_command == command:
            self._start_work_purr()
        return completed

    def _start_online_job(self, command: OnlineCommand) -> bool:
        if not self.online_monitor.online:
            self._stop_thinking_cue_for_speech()
            self._stop_tail_purr_for_neko_speech()
            return self._speak(OFFLINE_REPLY, vad_finalized_s=self.current_vad_finalized_s)
        if self.active_online_command is not None:
            return self._speak_online_job_status()
        if not self.online_jobs.start(command):
            return self._speak_online_job_status()
        self.active_online_command = command
        self._stop_thinking_cue_for_speech()
        self._stop_tail_purr_for_neko_speech()
        self._event(
            "online_job_started",
            job_kind=command.kind,
            description=command.status_description,
        )
        acceptance = (
            "Sounds like fun, let me work on that!"
            if command.kind == "compose_story"
            else "Ooh, let me sniff around the web!"
        )
        self._speak(acceptance, vad_finalized_s=self.current_vad_finalized_s)
        self._start_work_purr()
        # The request stays deliberately outside local LLM history. Codex owns
        # its own bounded one-shot context and the completion is read directly.
        self.controller.extend_active_session(time.monotonic())
        return True

    def _finish_online_job(self, result: OnlineJobResult) -> None:
        self._stop_work_purr()
        if self.active_online_command != result.command:
            self._event(
                "online_job_stale_result_ignored",
                job_kind=result.command.kind,
            )
            return
        self.active_online_command = None
        if result.succeeded and result.added_story_ids:
            try:
                # The recording manifest will hot-reload later when the low-
                # priority renderer atomically publishes the new sections.
                self.story_library = StoryLibrary()
            except (OSError, TypeError, ValueError) as error:
                self._event("story_library_reload_error", message=str(error))
        self._event(
            "online_job_complete",
            job_kind=result.command.kind,
            succeeded=result.succeeded,
            added_story_ids=list(result.added_story_ids),
        )
        self._stop_tail_purr_for_neko_speech()
        self._speak(result.spoken_text)
        self.controller.extend_active_session(time.monotonic())

    def _drain_online_results(self) -> None:
        while True:
            try:
                result = self.online_results.get_nowait()
            except queue.Empty:
                return
            try:
                self._finish_online_job(result)
            except Exception as error:
                self._recover_request_failure(error, phase="online_completion")

    def _recover_request_failure(self, error: Exception, *, phase: str) -> None:
        """Cancel partial work and audibly recover from an unexpected request error."""

        try:
            self._event(
                "request_failed",
                phase=phase,
                error_type=type(error).__name__,
            )
        except Exception:
            # Error reporting must never become a second fatal request error.
            pass

        self.cancel_speech.set()
        self.cancel_cat_sound.set()
        self.cancel_tail_purr.set()
        self.cancel_work_purr.set()
        try:
            self.online_jobs.cancel()
        except Exception:
            pass
        self.active_online_command = None
        self.pending_schedule_query = None
        self.pending_schedule_base_query = None
        for stop_output in (
            self._stop_thinking_cue_for_speech,
            self._stop_tail_purr_for_neko_speech,
            self._stop_work_purr,
        ):
            try:
                stop_output()
            except Exception:
                pass
        try:
            self._speak(REQUEST_FAILURE_REPLY)
            self.controller.extend_active_session(time.monotonic())
        except Exception as fallback_error:
            try:
                self._event(
                    "request_failure_reply_failed",
                    error_type=type(fallback_error).__name__,
                )
            except Exception:
                pass

    def _handle_segment_safely(self, segment: SpeechSegment) -> bool:
        try:
            return self._handle_segment(segment)
        except Exception as error:
            self._recover_request_failure(error, phase="request")
            return False

    def _start_thinking_cue(self, text: str) -> None:
        """Play a real acknowledgement while the model thinks, when approved.

        A child speaking does not cancel this clip.  Model readiness does: this
        keeps a purr from delaying Neko's actual spoken answer.
        """

        action = self._thinking_cue_action(text)
        if action is None:
            return
        try:
            selection = self.cat_sounds.select(
                action,
                self.args.cat_sound_output,
                autonomous=True,
            )
        except CatAudioDenied as error:
            self._event("cat_sound_fallback", action=action, reason=str(error))
            return
        self.cancel_cat_sound.clear()

        def play() -> None:
            self.speaking.set()
            self.cat_sound_playing.set()
            try:
                played = self.cat_sound_player.play(
                    selection,
                    cancel_event=self.cancel_cat_sound,
                    on_started=lambda: self._event(
                        "thinking_cat_sound_started",
                        action=selection.action,
                        asset_id=selection.asset_id,
                    ),
                )
                if played:
                    self.cat_sounds.mark_played(selection)
                    self._event(
                        "thinking_cat_sound_complete",
                        action=selection.action,
                        asset_id=selection.asset_id,
                    )
                else:
                    self._event("thinking_cat_sound_interrupted", action=selection.action)
            except Exception as error:
                self._event("cat_sound_error", action=selection.action, message=str(error))
            finally:
                self.cat_sound_playing.clear()
                self.speaking.clear()

        self._thinking_sound_thread = threading.Thread(
            target=play, name="neko-thinking-cat-sound", daemon=True
        )
        self._thinking_sound_thread.start()

    def _stop_thinking_cue_for_speech(self) -> None:
        """Stop the cue only because Neko's generated speech is now ready."""

        self.cancel_cat_sound.set()
        thread = self._thinking_sound_thread
        if thread is not None:
            thread.join(timeout=1)
        self._thinking_sound_thread = None

    def _play_recorded_story(
        self,
        recording: RecordedStory,
        *,
        vad_finalized_s: float | None = None,
    ) -> bool:
        """Play verified Mini narration sections and their fixed cue plan."""

        if self.args.no_speak:
            self._event("recorded_story", story_id=recording.story_id)
            return True
        self.cancel_speech.clear()
        self.cancel_cat_sound.clear()
        self.story_interrupt_armed.clear()
        self.speaking.set()
        self.spoken_turn_active.set()
        first_output_started = False

        def first_pcm() -> None:
            nonlocal first_output_started
            if first_output_started:
                return
            first_output_started = True
            now = time.monotonic()
            values: dict[str, object] = {"source": "prerecorded_mini"}
            if vad_finalized_s is not None:
                after_finalize = now - vad_finalized_s
                values.update(
                    {
                        "from_vad_finalize_seconds": round(after_finalize, 3),
                        "estimated_from_speech_end_seconds": round(
                            after_finalize + self.args.min_silence_seconds,
                            3,
                        ),
                        "vad_tail_seconds": self.args.min_silence_seconds,
                    }
                )
            self._event("first_pcm_written", **values)

        completed = True
        try:
            for index, section in enumerate(recording.sections):
                if self.cancel_speech.is_set():
                    completed = False
                    break
                narration = CatSoundSelection(
                    action="story_narration",
                    asset_id=f"{recording.story_id}.section-{index + 1}",
                    path=section.path,
                    output="speaker",
                    gain_db=0.0,
                    duration_seconds=section.duration_seconds,
                    interruptible=True,
                )
                if section.contains_neko:
                    self.self_wake_guard.set()
                try:
                    played = self.cat_sound_player.play(
                        narration,
                        cancel_event=self.cancel_speech,
                        on_started=first_pcm,
                    )
                finally:
                    self.self_wake_guard.clear()
                if not played:
                    completed = False
                    break
                self._event(
                    "recorded_story_section_complete",
                    story_id=recording.story_id,
                    section=index + 1,
                )
                if section.cue_after is None:
                    continue
                try:
                    selection = self.cat_sounds.select(
                        section.cue_after,
                        self.args.cat_sound_output,
                        autonomous=True,
                    )
                except CatAudioDenied as error:
                    self._event(
                        "story_cat_sound_skipped",
                        action=section.cue_after,
                        reason=str(error),
                    )
                    continue
                played = self.cat_sound_player.play(
                    selection,
                    cancel_event=self.cancel_cat_sound,
                )
                if not played:
                    completed = False
                    break
                self.cat_sounds.mark_played(selection)
                self._event(
                    "cat_sound_complete",
                    action=selection.action,
                    asset_id=selection.asset_id,
                    output=selection.output,
                )
        except Exception as error:
            self._event("recorded_story_error", message=str(error))
            completed = False
        finally:
            self.spoken_turn_active.clear()
            self.speaking.clear()
            self.story_interrupt_armed.clear()
        self._event("playback_complete" if completed else "playback_cancelled")
        return completed

    def _speak(
        self,
        text: str,
        *,
        vad_finalized_s: float | None = None,
        max_audio_markers: int = 3,
    ) -> bool:
        if self.args.no_speak:
            self._event("reply", text=text)
            return True
        self.cancel_speech.clear()
        self.cancel_cat_sound.clear()
        self.story_interrupt_armed.clear()
        self.speaking.set()
        self.spoken_turn_active.set()
        first_output_started = False

        def first_pcm() -> None:
            nonlocal first_output_started
            if first_output_started:
                return
            first_output_started = True
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

        completed = True
        try:
            parts = parse_audio_script(text, max_markers=max_audio_markers)
            for index, part in enumerate(parts):
                if self.cancel_speech.is_set():
                    completed = False
                    break
                if isinstance(part, TextPart):
                    for chunk in chunk_text(part.text):
                        if NEKO_NAME_RE.search(chunk):
                            self.self_wake_guard.set()
                        try:
                            result = self.tts.synthesize(
                                chunk,
                                play=True,
                                cancel_event=self.cancel_speech,
                                on_first_pcm=first_pcm,
                            )
                        except Exception as error:
                            self._event("tts_error", message=str(error))
                            return False
                        finally:
                            self.self_wake_guard.clear()
                        if result.get("cancelled"):
                            completed = False
                            break
                    if not completed:
                        break
                    continue
                if not isinstance(part, CatSoundPart):
                    raise TypeError(f"unknown audio script part: {part!r}")
                if part.action == "purr_primary" and index == len(parts) - 1:
                    self._start_tail_purr()
                    continue
                try:
                    selection = self.cat_sounds.select(
                        part.action,
                        self.args.cat_sound_output,
                        autonomous=True,
                    )
                except CatAudioDenied as error:
                    self._event(
                        "cat_sound_fallback",
                        action=part.action,
                        reason=str(error),
                    )
                    try:
                        result = self.tts.synthesize(
                            part.fallback_text,
                            play=True,
                            cancel_event=self.cancel_speech,
                            on_first_pcm=first_pcm,
                        )
                    except Exception as error:
                        self._event("tts_error", message=str(error))
                        return False
                    if result.get("cancelled"):
                        completed = False
                        break
                    continue
                try:
                    played = self.cat_sound_player.play(
                        selection,
                        cancel_event=self.cancel_cat_sound,
                        on_started=first_pcm,
                    )
                except Exception as error:
                    self._event("cat_sound_error", action=part.action, message=str(error))
                    return False
                if not played:
                    completed = False
                    break
                self.cat_sounds.mark_played(selection)
                self._event(
                    "cat_sound_complete",
                    action=part.action,
                    asset_id=selection.asset_id,
                    output=selection.output,
                )
        finally:
            self.spoken_turn_active.clear()
            self.speaking.clear()
            self.story_interrupt_armed.clear()
        self._event("playback_complete" if completed else "playback_cancelled")
        return completed

    def _dialogue(self, request: DialogueRequest) -> bool:
        started = time.monotonic()
        local_command = parse_local_command(request.text)
        if local_command is not None:
            return self._handle_local_command(local_command)
        online_command = parse_online_command(request.text)
        if online_command is not None:
            return self._start_online_job(online_command)
        if (
            getattr(self, "active_online_command", None) is not None
        ):
            return self._speak_online_job_status()
        self._start_thinking_cue(request.text)
        schedule_followup = (
            self.pending_schedule_query is not None
            and is_schedule_refinement(request.text)
        )
        if is_schedule_query(request.text) or schedule_followup:
            schedule_query = request.text
            list_requested = requests_all_results(request.text)
            if schedule_followup and list_requested:
                assert self.pending_schedule_query is not None
                schedule_query = self.pending_schedule_query
            elif schedule_followup:
                schedule_query = f"{self.pending_schedule_query} {request.text}"
            reply = self.event_schedule.respond(schedule_query, force_list=list_requested)
            if (
                schedule_followup
                and not list_requested
                and reply.match_count == 0
                and self.pending_schedule_base_query is not None
            ):
                fallback = self.event_schedule.respond(
                    self.pending_schedule_base_query,
                    force_list=True,
                )
                reply = type(reply)(
                    "I couldn't find a match for that. Here are all the choices "
                    f"from that time instead. {fallback.text}",
                    needs_refinement=False,
                    match_count=fallback.match_count,
                )
            answer = reply.text
            if reply.needs_refinement:
                if self.pending_schedule_base_query is None:
                    self.pending_schedule_base_query = request.text
                self.pending_schedule_query = schedule_query
            else:
                self.pending_schedule_query = None
                self.pending_schedule_base_query = None
            self._event(
                "event_schedule_lookup",
                available=self.event_schedule.available(),
                source="local_cache",
                match_count=reply.match_count,
                needs_refinement=reply.needs_refinement,
            )
            self._stop_thinking_cue_for_speech()
            self._stop_tail_purr_for_neko_speech()
            completed = self._speak(
                answer,
                vad_finalized_s=self.current_vad_finalized_s,
            )
            if completed:
                self.controller.extend_active_session(time.monotonic())
            return completed
        self.pending_schedule_query = None
        self.pending_schedule_base_query = None
        if "story" in normalize_phrase(request.text):
            recording: RecordedStory | None = None
            try:
                story = self.story_library.choose(
                    request.text,
                    exclude_id=self.last_story_id,
                    rng=self._cue_rng,
                )
                answer = self.story_library.spoken_text(story)
                try:
                    recording = self.story_library.recording_for(story)
                except (KeyError, OSError, TypeError, ValueError) as error:
                    queued = enqueue_story_rebuild(
                        story.story_id,
                        "stale_or_invalid_recording",
                    )
                    self._event(
                        "story_recording_rebuild_queued",
                        story_id=story.story_id,
                        queued=queued,
                        reason=type(error).__name__,
                    )
                    recording = None
                if recording is None and story.story_id not in self.story_library.recordings:
                    queued = enqueue_story_rebuild(
                        story.story_id,
                        "missing_recording",
                    )
                    self._event(
                        "story_recording_rebuild_queued",
                        story_id=story.story_id,
                        queued=queued,
                        reason="missing",
                    )
                story_sound_budget = self.story_library.sound_budget(answer)
                if recording is None:
                    answer = self.story_library.with_audio_cues(
                        answer,
                        rng=self._cue_rng,
                    )
                self.last_story_id = story.story_id
                self._event(
                    "story_selected",
                    story_id=story.story_id,
                    title=story.title,
                    retrieval="local_manifest",
                    playback="prerecorded_mini" if recording else "live_tts_fallback",
                )
            except (LookupError, OSError, ValueError) as error:
                self._event("story_library_error", message=str(error))
                answer = ""
            if answer:
                self._stop_thinking_cue_for_speech()
                self._stop_tail_purr_for_neko_speech()
                self.story_interrupt_armed.clear()
                self.story_playing.set()
                try:
                    if recording is not None:
                        completed = self._play_recorded_story(
                            recording,
                            vad_finalized_s=self.current_vad_finalized_s,
                        )
                    else:
                        completed = self._speak(
                            answer,
                            vad_finalized_s=self.current_vad_finalized_s,
                            max_audio_markers=max(0, story_sound_budget - 1),
                        )
                finally:
                    self.story_playing.clear()
                    self.story_interrupt_armed.clear()
                context_note = self.story_library.context_note(
                    story,
                    interrupted=not completed,
                )
                if completed:
                    self.history.append(request.text, context_note, request.language)
                    self.controller.extend_active_session(time.monotonic())
                    if recording is None or recording.ending_purr:
                        self._start_tail_purr()
                else:
                    self.history.append(request.text, context_note, request.language)
                return completed
        try:
            if self.args.llm_route == "audio":
                answer = self.gemma.reply_audio(
                    self.current_audio_samples,
                    SAMPLE_RATE,
                    request.text,
                    request.language,
                    self.history,
                )
            elif self.args.response_mode == "first-sentence":
                answer = self.gemma.reply_first_sentence(
                    request.text,
                    request.language,
                    self.history,
                )
            else:
                answer = self.gemma.reply_complete_streamed(
                    request.text,
                    request.language,
                    self.history,
                )
        except Exception as error:
            self._stop_thinking_cue_for_speech()
            self._event("llm_error", message=str(error))
            self._speak("Oops, my thoughts got tangled. Try that once more?")
            return False
        self._event(
            "reply_ready",
            latency_seconds=round(time.monotonic() - started, 3),
            route=self.args.llm_route,
            response_mode=self.args.response_mode,
            **({"text": answer} if self.args.verbose_transcripts else {}),
        )
        self._stop_thinking_cue_for_speech()
        self._stop_tail_purr_for_neko_speech()

        # If another utterance already began while Gemma was thinking, do not
        # talk over it. Preserve the unanswered prompt and process the queued
        # speech next.
        superseded = self.audio.speech_sequence != self.current_segment_sequence
        if superseded and self.tail_purr_playing.is_set():
            # With the Bluetooth headset, the long local purr can occasionally
            # create a VAD edge of its own.  The child utterance that produced
            # this request is already finalized, so do not discard its reply
            # solely because the tail-purr output was seen by capture.
            self._event("tail_purr_self_audio_ignored")
            superseded = False
        if superseded:
            self.history.append_interrupted(request.text, request.language)
            self._event("reply_superseded_before_playback")
            return False

        answer = self._insert_response_cue(request.text, answer)

        completed = self._speak(answer, vad_finalized_s=self.current_vad_finalized_s)
        if completed:
            self.history.append(request.text, answer, request.language)
            if self._should_start_tail_purr(request.text, answer):
                self._start_tail_purr()
        else:
            self.history.append_interrupted(request.text, request.language)
        return completed

    def _handle_segment(self, segment: SpeechSegment) -> bool:
        if (
            not segment.stop_detected
            and is_addressed_stop_transcript(segment.transcript)
        ):
            # Speaker echo can prevent the dedicated stop KWS from firing.
            # Streaming ASR already covers every VAD segment, including output
            # segments tentatively ignored before they are finalized.
            self._on_stop()
            segment = SpeechSegment(
                samples=segment.samples,
                captured_at_s=segment.captured_at_s,
                wake_detected=segment.wake_detected,
                sleep_detected=segment.sleep_detected,
                stop_detected=True,
                sequence=segment.sequence,
                transcript=segment.transcript,
                asr_steps=segment.asr_steps,
                asr_finalize_seconds=segment.asr_finalize_seconds,
            )
            self._event("stop_transcript_fallback_detected")
        ignored_during_output = segment.sequence in self.ignored_story_sequences
        if (
            ignored_during_output
            and not segment.wake_detected
            and self.story_playing.is_set()
            and is_double_addressed_transcript(segment.transcript)
            and self._on_wake("ASR_NEKO_NEKO") is not False
        ):
            segment = SpeechSegment(
                samples=segment.samples,
                captured_at_s=segment.captured_at_s,
                wake_detected=True,
                sleep_detected=segment.sleep_detected,
                stop_detected=segment.stop_detected,
                sequence=segment.sequence,
                transcript=segment.transcript,
                asr_steps=segment.asr_steps,
                asr_finalize_seconds=segment.asr_finalize_seconds,
            )
            self._event("wake_transcript_fallback_detected")
        if ignored_during_output:
            self.ignored_story_sequences.discard(segment.sequence)
            if not segment.wake_detected and not segment.sleep_detected and not segment.stop_detected:
                self._event("output_nonwake_segment_discarded", sequence=segment.sequence)
                return False
        text = segment.transcript
        if not text and not segment.wake_detected and not segment.sleep_detected and not segment.stop_detected:
            self._event("empty_transcript")
            return self._maybe_meow_back(segment)
        if (
            getattr(self, "active_online_command", None) is not None
            and not segment.wake_detected
            and not segment.sleep_detected
            and not segment.stop_detected
        ):
            # A long job's purr keeps the ordinary session open, but only an
            # addressed Neko utterance may request a spoken progress update.
            self._event("online_job_nonwake_speech_ignored", sequence=segment.sequence)
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
                command=(
                    "stop" if segment.stop_detected
                    else "sleep" if segment.sleep_detected
                    else "wake"
                ),
            )
        was_active = self.controller.session_active
        self.current_segment_sequence = segment.sequence
        self.current_audio_samples = segment.samples
        self.current_vad_finalized_s = segment.captured_at_s
        policy_text = text
        if segment.stop_detected:
            policy_text = "Neko stop"
        elif segment.sleep_detected:
            policy_text = "bye bye"
        elif segment.wake_detected:
            policy_text = canonicalize_wake_transcript(text)
        if self.tail_purr_playing.is_set() or self.story_followup_pending.is_set():
            # Preserve the existing session and history across a tail purr or
            # addressed interruption. A tail purr follows a completed spoken
            # turn, so an ordinary in-session follow-up remains valid; only
            # speech that began during spoken output requires Neko's name.
            self.controller.extend_active_session(segment.captured_at_s)
            self._event(
                "output_session_extended",
                tail_purr=self.tail_purr_playing.is_set(),
                story_barge_in=self.story_followup_pending.is_set(),
            )
            self.story_followup_pending.clear()
        actions = self.controller.handle(
            TranscriptEvent(policy_text, language, segment.captured_at_s)  # type: ignore[arg-type]
        )
        if not was_active and self.controller.session_active:
            self.history.clear()
            self.pending_schedule_query = None
            self.pending_schedule_base_query = None
            self._event("session_started")
        dialogue_seen = False
        for action in actions:
            if isinstance(action, Acknowledge):
                self._event("wake_acknowledged")
                if not any(isinstance(item, DialogueRequest) for item in actions):
                    if (
                        getattr(self, "active_online_command", None) is not None
                    ):
                        self._speak_online_job_status()
                    else:
                        self._speak("[meow]")
            elif isinstance(action, DialogueRequest):
                dialogue_seen = True
                self._dialogue(action)
            elif isinstance(action, CancelAudio):
                self.cancel_speech.set()
                self.cancel_cat_sound.set()
                self.cancel_tail_purr.set()
                self.cancel_work_purr.set()
                self.online_jobs.cancel()
                self.active_online_command = None
                self.history.clear()
                self.pending_schedule_query = None
                self.pending_schedule_base_query = None
                self._event("audio_cancelled", reason=action.reason)
            elif isinstance(action, SetMuted):
                self._event("muted", value=action.muted)
            elif isinstance(action, SpeakText):
                self._speak(action.text)
        return dialogue_seen

    def run(self) -> int:
        if not self.gemma.ready():
            raise RuntimeError("local LLM is not ready")
        self.online_monitor.start()
        self.audio.start()
        if self._audio_tagger_error_type is not None:
            self._event(
                "audio_tagging_unavailable",
                error_type=self._audio_tagger_error_type,
            )
        self._event(
            "ready",
            asr_load_seconds=round(self.model_load_seconds, 3),
            audio_tagger_loaded=self.audio_tagger is not None,
            audio_tagger_load_seconds=round(self.audio_tagger_load_seconds, 3),
            device=self.args.device,
            media_retained=False,
            replay=bool(self.args.replay_wav),
            wake_phrase="Neko Neko",
            llm_model=self.args.model,
            llm_route=self.args.llm_route,
            tts_socket=str(self.args.tts_socket),
            online=self.online_monitor.online,
        )
        handled_dialogues = 0
        try:
            while not self.shutdown.is_set():
                self._drain_online_results()
                if self.audio.error is not None:
                    raise RuntimeError(f"audio capture failed: {self.audio.error}")
                try:
                    segment = self.audio.segments.get(timeout=0.2)
                except queue.Empty:
                    if self.audio.finished_event.is_set():
                        return 0
                    continue
                if self._handle_segment_safely(segment):
                    handled_dialogues += 1
                    if self.args.max_dialogues and handled_dialogues >= self.args.max_dialogues:
                        return 0
        finally:
            self.cancel_speech.set()
            self.cancel_cat_sound.set()
            self.cancel_tail_purr.set()
            self.cancel_work_purr.set()
            self.online_jobs.cancel()
            self._stop_work_purr()
            self.online_monitor.close()
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
    parser.add_argument(
        "--response-mode",
        choices=("complete", "first-sentence"),
        default="complete",
        help="complete keeps natural multi-sentence replies; first-sentence is a latency lab mode",
    )
    parser.add_argument("--gemma-timeout", type=float, default=60.0)
    parser.add_argument(
        "--connectivity-interval",
        type=float,
        default=120.0,
        help="seconds between immediate two-packet online probes",
    )
    parser.add_argument(
        "--online-job-timeout",
        type=float,
        default=1800.0,
        help="long Codex one-shot ceiling; deliberately exceeds dialogue timeout",
    )
    parser.add_argument("--tts-socket", type=Path, default=DEFAULT_TTS_SOCKET)
    parser.add_argument(
        "--audio-tagging-model",
        type=Path,
        default=DEFAULT_AUDIO_TAGGING_MODEL,
    )
    parser.add_argument(
        "--audio-tagging-labels",
        type=Path,
        default=DEFAULT_AUDIO_TAGGING_LABELS,
    )
    parser.add_argument("--audio-tagging-threads", type=int, choices=(1, 2), default=2)
    parser.add_argument("--meow-back-threshold", type=float, default=0.10)
    parser.add_argument(
        "--disable-meow-back",
        dest="meow_back_enabled",
        action="store_false",
        help="disable the local empty-STT human-meow reflex",
    )
    parser.set_defaults(meow_back_enabled=True)
    parser.add_argument(
        "--cat-sound-output",
        choices=("speaker", "body_transducer"),
        default="speaker",
    )
    parser.add_argument("--cat-speaker-target")
    parser.add_argument("--cat-transducer-target")
    parser.add_argument(
        "--thinking-cue-rate",
        type=float,
        default=0.12,
        help="chance of a short approved real-cat acknowledgement while LLM text is generated",
    )
    parser.add_argument(
        "--response-cue-rate",
        type=float,
        default=0.75,
        help="chance of a varied real-cat cue between sentences when LLM omitted one",
    )
    parser.add_argument(
        "--attended-cat-sounds",
        action="store_true",
        help=(
            "allow selected bench recordings only for a supervised headphone "
            "listening pass; never use this for cart hardware or boot"
        ),
    )
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
    if not 0 <= args.thinking_cue_rate <= 1:
        raise ValueError("thinking cue rate must be between zero and one")
    if not 0 <= args.response_cue_rate <= 1:
        raise ValueError("response cue rate must be between zero and one")
    if not 0 <= args.meow_back_threshold <= 1:
        raise ValueError("meow-back threshold must be between zero and one")
    if args.connectivity_interval <= 0 or args.online_job_timeout <= 120:
        raise ValueError("online intervals must be positive and jobs must allow over two minutes")
    if args.attended_cat_sounds and args.cat_sound_output != "speaker":
        raise ValueError("attended cat-sound testing supports speaker output only")
    assistant = VoiceAssistant(args)

    def stop(_signum: int, _frame: object) -> None:
        assistant.shutdown.set()
        assistant.cancel_speech.set()
        assistant.cancel_cat_sound.set()
        assistant.cancel_work_purr.set()
        assistant.online_jobs.cancel()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    return assistant.run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error
