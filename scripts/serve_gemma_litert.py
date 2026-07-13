#!/usr/bin/env python3
"""Serve the pinned Gemma LiteRT model with bounded Jetson-safe settings.

LiteRT-LM 0.14.0's stock server lazily chooses the artifact's backend and does
not expose the KV-cache or CPU-thread controls available to ``litert-lm run``.
This wrapper intentionally supports one fixed local model, preloads it before
listening, binds to loopback by default, and uses the CPU path that passed the
local Jetson smoke tests.

This imports private LiteRT-LM CLI handler APIs and is therefore coupled to the
pinned ``litert-lm==0.14.0`` tool environment. Re-test before any upgrade.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import sys
from typing import Any

import litert_lm
from litert_lm_cli.commands import openai_handler
from litert_lm_cli.commands import serve_util


DEFAULT_MODEL_ID = "gemma-4-e2b-it"
DEFAULT_MODEL_PATH = Path(
    "/home/neko/.litert-lm/models/gemma-4-e2b-it/model.litertlm"
)


class FixedModelOpenAIHandler(openai_handler.OpenAIHandler):
    """OpenAI handler that can only return the already-loaded fixed engine."""

    def _get_engine(
        self,
        model_id: str,
        translated_messages: list[dict[str, Any]] | None = None,
        prompt: Any = None,
    ) -> litert_lm.Engine | None:
        del translated_messages, prompt
        assert isinstance(self.server, serve_util.LiteRTLMServer)
        if model_id != self.server.model_id:
            self.send_error(404, f"Model {model_id!r} is not served here")
            return None
        if self.server.litert_lm_engine is None:
            self.send_error(503, "Model engine is not ready")
            return None
        return self.server.litert_lm_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9379)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--max-num-tokens", type=int, default=2048)
    parser.add_argument("--cpu-thread-count", type=int, default=4)
    parser.add_argument(
        "--verbose", action="store_true", help="enable LiteRT informational logs"
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.model_path.is_file():
        raise FileNotFoundError(f"LiteRT model not found: {args.model_path}")
    if args.max_num_tokens < 2048:
        raise ValueError(
            "--max-num-tokens must be at least 2048 for this Gemma artifact"
        )
    if args.cpu_thread_count < 1:
        raise ValueError("--cpu-thread-count must be positive")
    if not 1 <= args.port <= 65535:
        raise ValueError("--port must be between 1 and 65535")


def notify_systemd(message: str) -> None:
    """Send a readiness/status datagram when systemd supplied NOTIFY_SOCKET."""
    notify_socket = os.environ.get("NOTIFY_SOCKET")
    if not notify_socket:
        return
    if notify_socket.startswith("@"):
        notify_socket = "\0" + notify_socket[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notifier:
        notifier.connect(notify_socket)
        notifier.sendall(message.encode("utf-8"))


def main() -> int:
    args = parse_args()
    validate_args(args)

    litert_lm.set_min_log_severity(
        litert_lm.LogSeverity.INFO
        if args.verbose
        else litert_lm.LogSeverity.WARNING
    )

    cpu_backend = litert_lm.Backend.CPU(thread_count=args.cpu_thread_count)
    server_address = (args.host, args.port)

    with serve_util.LiteRTLMServer(
        server_address, FixedModelOpenAIHandler
    ) as server:
        engine = litert_lm.Engine(
            str(args.model_path),
            backend=cpu_backend,
            vision_backend=litert_lm.Backend.CPU(),
            audio_backend=litert_lm.Backend.CPU(),
            max_num_tokens=args.max_num_tokens,
            cache_dir="",
        )
        engine.__enter__()
        server.litert_lm_engine = engine
        server.model_id = args.model_id
        server.backend = cpu_backend
        server.max_num_tokens = args.max_num_tokens
        server.vision_backend = litert_lm.Backend.CPU()
        server.audio_backend = litert_lm.Backend.CPU()

        print(
            f"READY model={args.model_id} backend=cpu "
            f"max_num_tokens={args.max_num_tokens} "
            f"listen={args.host}:{args.port}",
            flush=True,
        )
        notify_systemd(
            f"READY=1\nSTATUS=Serving {args.model_id} on "
            f"{args.host}:{args.port} with {args.cpu_thread_count} CPU threads"
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            engine.__exit__(None, None, None)
            server.litert_lm_engine = None
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error
