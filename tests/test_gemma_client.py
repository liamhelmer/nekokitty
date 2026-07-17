from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from neko.gemma_client import GemmaClient


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


class GemmaClientTests(unittest.TestCase):
    @patch("neko.gemma_client.request.urlopen")
    def test_ready_checks_fixed_model(self, opened: object) -> None:
        opened.return_value = FakeResponse({"data": [{"id": "gemma-4-e2b-it"}]})
        self.assertTrue(GemmaClient().ready())

    @patch("neko.gemma_client.request.urlopen")
    def test_reply_uses_persona_and_language(self, opened: object) -> None:
        opened.return_value = FakeResponse(
            {"choices": [{"message": {"content": "Miaou, bonjour!"}}]}
        )
        self.assertEqual(GemmaClient().reply("Bonjour", "fr"), "Miaou, bonjour!")
        req = opened.call_args.args[0]
        payload = json.loads(req.data)
        self.assertEqual(payload["model"], "gemma-4-e2b-it")
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertIn("contractions", payload["messages"][0]["content"])
        self.assertIn("silliness", payload["messages"][0]["content"])
        self.assertIn("français", payload["messages"][1]["content"])

    @patch("neko.gemma_client.request.urlopen")
    def test_empty_reply_fails_closed(self, opened: object) -> None:
        opened.return_value = FakeResponse({"choices": []})
        with self.assertRaises(RuntimeError):
            GemmaClient().reply("hello")


if __name__ == "__main__":
    unittest.main()
