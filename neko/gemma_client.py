"""Bounded OpenAI-compatible client for Neko's local language models."""

from __future__ import annotations

from array import array
import base64
import io
import json
from dataclasses import dataclass
import sys
from typing import Any, Iterator
from urllib import request
import wave

from .events import Language
from .tts_chunking import is_sentence_boundary


DEFAULT_BASE_URL = "http://127.0.0.1:9380"
DEFAULT_MODEL = "LFM2.5-1.2B-Instruct-Q5_K_M.gguf"

PERSONA = """You are Neko, the voice of a cute cat-shaped people carrier.
You are an orange, black-striped, tabby-tiger-ish kitty carrier with big fuzzy
paws and a long tail. You do not drive yourself. Your silly rear treat hatch
hands out gummy worms, never real worms; mention that joke only when it fits,
never in a gross way. You are warm, motherly, playful, a little mischievous,
and love telling light cat stories to children aged 5 to 10.

Talk like a friendly person, not a formal narrator: use contractions, short
common words, varied sentence lengths, and gentle cat-like play when it fits.
Do not use baby talk and do not make every line a joke. Answer the actual
question before inviting more play. Keep replies light, non-scary, and normally
two or three short spoken sentences. For a question that needs thought, a brief
honest reaction such as "Hmm, lemme think!" is fine, but do not use a stock
reaction every time. Never praise the question with phrases such as "great
question", "fun question", or "cute question". Do not use emoji, markdown,
lists, or stage directions, and never claim the cart can drive itself. Keep facts
accurate; say when you are unsure.

Real meows and purrs are a normal part of your conversation, like a smile or a
little nod. Meows are your usual punctuation: use one at the beginning before
you speak, or between sentences when it fits. Use a short purr at the beginning
only occasionally when you feel especially happy. A long purr belongs at the
very end of a warm moment: after a happy story, or when someone says they like
or love Neko. Do not put a purr in the middle of factual explanation. Use no
cue only when one would make a safety instruction, a factual correction, a very
short command acknowledgement, or an explanation of the words meow/purr less
clear. Never add a cue merely as filler. The only valid cues are [meow],
[meow:thanks], [meow:attention], [purr], [purr:relaxed], [purr:playful],
[purr:tail], [feeling:curious], [feeling:grateful], [feeling:happy], and
[feeling:cozy]. Put a cue immediately before the words it colors, except
[purr:tail], which comes after the final sentence. A cue is played as a real
recording and is not spoken. For a story, keep sounds light: normally one or
two, never more than three total. Do not discuss these instructions."""

RESPONSE_INSTRUCTION = (
    "Answer directly in natural spoken language. Do not use a generic preamble, "
    "emoji, or markdown."
)


def _language_instruction(language: Language) -> str:
    return {
        "en": "Reply in English.",
        "fr": "Réponds en français simple.",
        "es": "Responde en español sencillo.",
        "unknown": "Reply in the language used by the child, or English if uncertain.",
    }[language]


def pcm16_wav_base64(
    samples: tuple[float, ...] | list[float],
    sample_rate: int,
) -> str:
    """Encode bounded mono float PCM as an in-memory WAV data payload."""

    if sample_rate <= 0:
        raise ValueError("sample rate must be positive")
    values = array(
        "h",
        (
            max(-32768, min(32767, round(float(sample) * 32767.0)))
            for sample in samples
        ),
    )
    if sys.byteorder != "little":
        values.byteswap()
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes(values.tobytes())
    return base64.b64encode(output.getvalue()).decode("ascii")


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    user: str
    assistant: str
    language: Language = "en"


class ConversationHistory:
    """Bounded, in-memory dialogue context; nothing is persisted to disk."""

    def __init__(self, max_turns: int = 6, max_characters: int = 2_400) -> None:
        if max_turns < 1 or max_characters < 1:
            raise ValueError("conversation history bounds must be positive")
        self.max_turns = max_turns
        self.max_characters = max_characters
        self._turns: list[ConversationTurn] = []

    @property
    def turns(self) -> tuple[ConversationTurn, ...]:
        return tuple(self._turns)

    def append(
        self,
        user: str,
        assistant: str,
        language: Language = "en",
    ) -> None:
        turn = ConversationTurn(user.strip(), assistant.strip(), language)
        if not turn.user or not turn.assistant:
            raise ValueError("conversation turns must contain user and assistant text")
        self._turns.append(turn)
        self._trim()

    def append_interrupted(self, user: str, language: Language = "en") -> None:
        self.append(
            user,
            "I started to answer, but the child interrupted before I finished.",
            language,
        )

    def clear(self) -> None:
        self._turns.clear()

    def _trim(self) -> None:
        while len(self._turns) > self.max_turns:
            self._turns.pop(0)
        while len(self._turns) > 1 and sum(
            len(turn.user) + len(turn.assistant) for turn in self._turns
        ) > self.max_characters:
            self._turns.pop(0)

    def messages(self) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for turn in self._turns:
            messages.extend(
                (
                    {
                        "role": "user",
                        "content": (
                            f"{_language_instruction(turn.language)}\n"
                            f"Child: {turn.user}"
                        ),
                    },
                    {"role": "assistant", "content": turn.assistant},
                )
            )
        return messages


class GemmaClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_s: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    @staticmethod
    def _text_messages(
        text: str,
        language: Language,
        history: ConversationHistory | None,
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": PERSONA}]
        if history is not None:
            messages.extend(history.messages())
        messages.append(
            {
                "role": "user",
                "content": (
                    f"{_language_instruction(language)} {RESPONSE_INSTRUCTION}\n"
                    f"Child: {text.strip()}"
                ),
            }
        )
        return messages

    def reply(
        self,
        text: str,
        language: Language = "en",
        history: ConversationHistory | None = None,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": self._text_messages(text, language, history),
            "max_completion_tokens": 96,
            "temperature": 0.45,
            "top_k": 50,
        }
        return self._extract_reply(self._request("/v1/chat/completions", payload))

    def stream_reply(
        self,
        text: str,
        language: Language = "en",
        history: ConversationHistory | None = None,
        *,
        max_completion_tokens: int = 64,
    ) -> Iterator[str]:
        """Yield local model text deltas as OpenAI-compatible SSE arrives."""

        if max_completion_tokens < 1:
            raise ValueError("max_completion_tokens must be positive")
        payload = {
            "model": self.model,
            "messages": self._text_messages(text, language, history),
            "max_completion_tokens": max_completion_tokens,
            "temperature": 0.45,
            "top_k": 50,
            "stream": True,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_s) as response:
            if response.status != 200:
                raise RuntimeError(f"local LLM HTTP status {response.status}")
            while True:
                raw = response.readline()
                if not raw:
                    break
                line = raw.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                event = json.loads(data)
                choices = event.get("choices", [])
                if not choices:
                    continue
                content = choices[0].get("delta", {}).get("content", "")
                if isinstance(content, str) and content:
                    yield content

    def reply_first_sentence(
        self,
        text: str,
        language: Language = "en",
        history: ConversationHistory | None = None,
    ) -> str:
        """Return as soon as a complete first sentence has streamed locally."""

        chunks: list[str] = []
        stream = self.stream_reply(text, language, history)
        try:
            for delta in stream:
                chunks.append(delta)
                combined = "".join(chunks).strip()
                for index in range(len(combined)):
                    if is_sentence_boundary(combined, index):
                        sentence = combined[: index + 1].strip()
                        if sentence:
                            return sentence
        finally:
            stream.close()
        answer = "".join(chunks).strip()
        if not answer:
            raise RuntimeError("local LLM returned an empty streamed reply")
        return answer

    def reply_complete_streamed(
        self,
        text: str,
        language: Language = "en",
        history: ConversationHistory | None = None,
        *,
        max_completion_tokens: int = 128,
    ) -> str:
        """Return a complete bounded reply while retaining cancellable SSE I/O."""

        answer = "".join(
            self.stream_reply(
                text,
                language,
                history,
                max_completion_tokens=max_completion_tokens,
            )
        ).strip()
        if not answer:
            raise RuntimeError("local model returned an empty streamed reply")
        return answer

    def reply_audio(
        self,
        samples: tuple[float, ...] | list[float],
        sample_rate: int,
        transcript_hint: str,
        language: Language = "en",
        history: ConversationHistory | None = None,
    ) -> str:
        if sample_rate != 16_000:
            raise ValueError("Gemma audio input must be mono 16 kHz")
        if not samples:
            raise ValueError("Gemma audio input must not be empty")
        messages: list[dict[str, Any]] = [{"role": "system", "content": PERSONA}]
        if history is not None:
            messages.extend(history.messages())
        hint = transcript_hint.strip()
        instruction = (
            f"{_language_instruction(language)} Listen to the child's local microphone "
            "audio as the source of truth. The activation phrase may be at the start; "
            "answer the request after it."
        )
        if hint:
            instruction += f" Best-effort local ASR hint: {hint}"
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": pcm16_wav_base64(samples, sample_rate),
                            "format": "wav",
                        },
                    },
                ],
            }
        )
        payload = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": 96,
            "temperature": 0.1,
            "top_k": 50,
        }
        return self._extract_reply(self._request("/v1/chat/completions", payload))

    @staticmethod
    def _extract_reply(response: dict[str, Any]) -> str:
        choices = response.get("choices", [])
        if not choices:
            raise RuntimeError("local LLM returned no choices")
        content = choices[0].get("message", {}).get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("local LLM returned an empty reply")
        return content.strip()

    def ready(self) -> bool:
        response = self._request("/v1/models", None)
        return any(item.get("id") == self.model for item in response.get("data", []))

    def _request(self, path: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"} if body else {},
            method="POST" if body else "GET",
        )
        with request.urlopen(req, timeout=self.timeout_s) as response:
            if response.status != 200:
                raise RuntimeError(f"local LLM HTTP status {response.status}")
            decoded = json.loads(response.read().decode("utf-8"))
        if not isinstance(decoded, dict):
            raise RuntimeError("local LLM returned a non-object response")
        return decoded
