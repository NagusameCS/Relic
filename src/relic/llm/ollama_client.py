"""
Ollama LLM client for Relic.

Communicates with a local Ollama instance via its HTTP API to generate
pentesting plans, analyse tool output, and reason about next steps.

Optimised for GLM-4.7-Flash which supports:
  - Thinking/reasoning tokens
  - Tool calling
  - Chat-style and generate-style endpoints
  - 198K context window
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncIterator

import httpx

from relic.core.config import LLMConfig

log = logging.getLogger("relic.llm.ollama")


class OllamaClient:
    """Async client for the Ollama REST API with GLM-4.7-Flash optimisations."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=config.timeout)
        self._active_model: str = config.model

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    async def ensure_model(self) -> str:
        """Verify the configured model is available; fall back if not."""
        models = await self.list_models()
        names = {m.get("name", "") for m in models}
        # Ollama names can have :latest suffix
        names_base = {n.split(":")[0] for n in names}

        primary = self.config.model
        if primary in names or primary in names_base:
            self._active_model = primary
            return primary

        fallback = self.config.fallback_model
        if fallback and (fallback in names or fallback in names_base):
            log.warning("Model %s not found, falling back to %s", primary, fallback)
            self._active_model = fallback
            return fallback

        # Use whatever is available
        if names:
            first = next(iter(names))
            log.warning("Neither %s nor %s found, using %s", primary, fallback, first)
            self._active_model = first
            return first

        raise RuntimeError("No models available in Ollama")

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    async def generate(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt and return the full generated text."""
        payload: dict[str, Any] = {
            "model": self._active_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "num_ctx": self.config.num_ctx,
            },
        }
        if system:
            payload["system"] = system

        url = f"{self.base_url}/api/generate"
        log.debug("POST %s model=%s prompt_len=%d", url, self._active_model, len(prompt))

        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "")
            return self._strip_thinking(raw)
        except httpx.HTTPStatusError as exc:
            log.error("Ollama HTTP error: %s", exc)
            raise
        except httpx.ConnectError:
            log.error("Cannot connect to Ollama at %s", self.base_url)
            raise RuntimeError(f"Ollama unreachable at {self.base_url}")

    async def generate_stream(self, prompt: str, system: str | None = None) -> AsyncIterator[str]:
        """Stream tokens as they arrive."""
        payload: dict[str, Any] = {
            "model": self._active_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "num_ctx": self.config.num_ctx,
            },
        }
        if system:
            payload["system"] = system

        url = f"{self.base_url}/api/generate"

        async with self._client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        return
                except json.JSONDecodeError:
                    continue

    # ------------------------------------------------------------------
    # Chat-style interface (GLM-4.7-Flash works well with chat format)
    # ------------------------------------------------------------------

    async def chat(self, messages: list[dict[str, str]], think: bool = True) -> str:
        """Send a chat-style request and return the assistant message.

        GLM-4.7-Flash supports ``think`` mode which produces higher quality
        reasoning for complex prompts like pentesting planning.
        """
        payload: dict[str, Any] = {
            "model": self._active_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "num_ctx": self.config.num_ctx,
            },
        }
        if think:
            payload["think"] = True

        url = f"{self.base_url}/api/chat"
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # If think mode fails (old Ollama), retry without it
            if think and exc.response.status_code == 500:
                log.warning("Think mode failed, retrying without it")
                payload.pop("think", None)
                resp = await self._client.post(url, json=payload)
                resp.raise_for_status()
            else:
                raise
        data = resp.json()

        # Extract thinking + response
        message = data.get("message", {})
        thinking = message.get("thinking", "")
        content = message.get("content", "")

        if thinking:
            log.debug("LLM thinking (%d chars): %.200s...", len(thinking), thinking)

        # Some Ollama versions put GLM output solely in the thinking field.
        # When content is empty but thinking has text, fall back to generate.
        if not content and thinking:
            log.warning("Chat returned empty content with thinking — falling back to generate")
            return await self._chat_via_generate(messages)

        if not content:
            # Last resort: generate endpoint with concatenated messages
            log.warning("Chat returned empty content — falling back to generate")
            return await self._chat_via_generate(messages)

        return content

    async def _chat_via_generate(self, messages: list[dict[str, str]]) -> str:
        """Emulate chat using the generate endpoint (more reliable on older Ollama)."""
        system_parts: list[str] = []
        prompt_parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "system":
                system_parts.append(text)
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {text}")
            else:
                prompt_parts.append(f"User: {text}")
        prompt_parts.append("Assistant:")

        return await self.generate(
            prompt="\n\n".join(prompt_parts),
            system="\n".join(system_parts) if system_parts else None,
        )

    async def chat_with_thinking(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        """Like chat() but returns (thinking, content) separately."""
        payload: dict[str, Any] = {
            "model": self._active_model,
            "messages": messages,
            "stream": False,
            "think": True,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "num_ctx": self.config.num_ctx,
            },
        }

        url = f"{self.base_url}/api/chat"
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        message = data.get("message", {})
        return message.get("thinking", ""), message.get("content", "")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    async def list_models(self) -> list[dict[str, Any]]:
        """Return available models from the Ollama instance."""
        resp = await self._client.get(f"{self.base_url}/api/tags")
        resp.raise_for_status()
        return resp.json().get("models", [])

    async def health_check(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def model_info(self) -> dict[str, Any]:
        """Get details about the active model."""
        try:
            resp = await self._client.post(
                f"{self.base_url}/api/show",
                json={"name": self._active_model},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return {}

    async def close(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_thinking(text: str) -> str:
        """Remove <think>...</think> blocks from generate-style responses.

        GLM-4.7-Flash may wrap internal reasoning in think tags when using
        the generate endpoint (as opposed to the chat endpoint with think=True).
        """
        return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()
