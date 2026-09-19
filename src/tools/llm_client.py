"""Minimal wrapper around the Anthropic Messages API for plain text/JSON
completions (used by the Outreach Agent). The orchestrator's tool-use loop
(src/orchestrator/agentic_loop.py) talks to the Anthropic SDK directly
instead, since tool-use has a materially different request/response shape.

Defined as a Protocol so tests can inject a fake without any network access.
"""
from __future__ import annotations

from typing import Protocol

import anthropic


class LLMClient(Protocol):
    def complete(self, *, system: str, user: str, max_tokens: int = 1024) -> str: ...


class AnthropicLLMClient:
    def __init__(self, *, api_key: str, model: str):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set. Add it to .env (see .env.example).")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, *, system: str, user: str, max_tokens: int = 1024) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
