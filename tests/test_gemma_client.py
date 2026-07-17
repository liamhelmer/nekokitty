from __future__ import annotations

import io
import json
import base64
import unittest
from unittest.mock import patch
import wave

from neko.gemma_client import ConversationHistory, GemmaClient


class FakeResponse:
    def __init__(self, payload: object, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


class FakeSseResponse:
    def __init__(self, deltas: list[str], status: int = 200) -> None:
        lines: list[bytes] = []
        for delta in deltas:
            event = {"choices": [{"delta": {"content": delta}}]}
            lines.append(f"data: {json.dumps(event)}\n\n".encode())
        lines.append(b"data: [DONE]\n\n")
        self.stream = io.BytesIO(b"".join(lines))
        self.status = status
        self.closed = False

    def __enter__(self) -> "FakeSseResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True

    def readline(self) -> bytes:
        return self.stream.readline()


class GemmaClientTests(unittest.TestCase):
    @patch("neko.gemma_client.request.urlopen")
    def test_ready_checks_fixed_model(self, opened: object) -> None:
        opened.return_value = FakeResponse(
            {"data": [{"id": "LFM2.5-1.2B-Instruct-Q5_K_M.gguf"}]}
        )
        self.assertTrue(GemmaClient().ready())

    @patch("neko.gemma_client.request.urlopen")
    def test_reply_uses_persona_and_language(self, opened: object) -> None:
        opened.return_value = FakeResponse(
            {"choices": [{"message": {"content": "Miaou, bonjour!"}}]}
        )
        self.assertEqual(GemmaClient().reply("Bonjour", "fr"), "Miaou, bonjour!")
        req = opened.call_args.args[0]
        payload = json.loads(req.data)
        self.assertEqual(payload["model"], "LFM2.5-1.2B-Instruct-Q5_K_M.gguf")
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertIn("contractions", payload["messages"][0]["content"])
        self.assertIn("silliness", payload["messages"][0]["content"])
        self.assertIn("Do not use emoji", payload["messages"][0]["content"])
        self.assertIn("français", payload["messages"][1]["content"])
        self.assertEqual(payload["max_completion_tokens"], 96)
        self.assertEqual(payload["temperature"], 0.1)

    @patch("neko.gemma_client.request.urlopen")
    def test_first_sentence_returns_before_later_streamed_text(self, opened: object) -> None:
        response = FakeSseResponse(["Cats ", "purr!", " This is later."])
        opened.return_value = response
        answer = GemmaClient().reply_first_sentence("Why?")
        self.assertEqual(answer, "Cats purr!")
        self.assertTrue(response.closed)
        payload = json.loads(opened.call_args.args[0].data)
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["max_completion_tokens"], 64)

    @patch("neko.gemma_client.request.urlopen")
    def test_first_sentence_uses_final_unpunctuated_stream(self, opened: object) -> None:
        opened.return_value = FakeSseResponse(["Soft ", "paws"])
        self.assertEqual(GemmaClient().reply_first_sentence("Tell me"), "Soft paws")

    @patch("neko.gemma_client.request.urlopen")
    def test_empty_reply_fails_closed(self, opened: object) -> None:
        opened.return_value = FakeResponse({"choices": []})
        with self.assertRaises(RuntimeError):
            GemmaClient().reply("hello")

    @patch("neko.gemma_client.request.urlopen")
    def test_reply_includes_bounded_conversation_history(self, opened: object) -> None:
        opened.return_value = FakeResponse(
            {"choices": [{"message": {"content": "The blue one!"}}]}
        )
        history = ConversationHistory(max_turns=2, max_characters=1_000)
        history.append("Pick red or blue.", "Blue!", "en")
        GemmaClient().reply("Which one did you pick?", "en", history)
        payload = json.loads(opened.call_args.args[0].data)
        self.assertEqual([message["role"] for message in payload["messages"]], [
            "system",
            "user",
            "assistant",
            "user",
        ])
        self.assertIn("Pick red or blue", payload["messages"][1]["content"])
        self.assertIn("Which one did you pick", payload["messages"][3]["content"])

    def test_history_discards_oldest_turns_to_stay_bounded(self) -> None:
        history = ConversationHistory(max_turns=2, max_characters=100)
        history.append("one", "first")
        history.append("two", "second")
        history.append("three", "third")
        self.assertEqual([turn.user for turn in history.turns], ["two", "three"])
        history.clear()
        self.assertEqual(history.turns, ())

    def test_interrupted_turn_is_explicit_context(self) -> None:
        history = ConversationHistory()
        history.append_interrupted("Tell me why cats purr")
        self.assertIn("interrupted", history.turns[0].assistant)

    @patch("neko.gemma_client.request.urlopen")
    def test_audio_reply_posts_an_inline_mono_16khz_wav(self, opened: object) -> None:
        opened.return_value = FakeResponse(
            {"choices": [{"message": {"content": "A cat fact!"}}]}
        )
        answer = GemmaClient().reply_audio([0.0, 0.25, -0.25], 16_000, "cat fact")
        self.assertEqual(answer, "A cat fact!")
        payload = json.loads(opened.call_args.args[0].data)
        content = payload["messages"][-1]["content"]
        self.assertEqual(content[1]["type"], "input_audio")
        wav_bytes = base64.b64decode(content[1]["input_audio"]["data"])
        with wave.open(io.BytesIO(wav_bytes), "rb") as source:
            self.assertEqual(source.getframerate(), 16_000)
            self.assertEqual(source.getnchannels(), 1)
            self.assertEqual(source.getnframes(), 3)

    def test_audio_reply_rejects_wrong_rate_and_empty_audio(self) -> None:
        with self.assertRaises(ValueError):
            GemmaClient().reply_audio([0.0], 24_000, "")
        with self.assertRaises(ValueError):
            GemmaClient().reply_audio([], 16_000, "")


if __name__ == "__main__":
    unittest.main()
