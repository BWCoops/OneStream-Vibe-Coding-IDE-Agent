"""LLM client abstraction — supports both Claude API and vLLM."""

from __future__ import annotations

import httpx
import structlog
from config import LLMConfig

logger = structlog.get_logger()


class LLMClient:
    """Unified interface for Claude API (cloud) and vLLM (on-prem)."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._http = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Generate a completion from the configured LLM provider."""
        tokens = max_tokens or self.config.generator_max_tokens

        if self.config.provider == "anthropic":
            return await self._call_anthropic(system_prompt, user_message, tokens, temperature)
        elif self.config.provider == "vllm":
            return await self._call_vllm(system_prompt, user_message, tokens, temperature)
        else:
            raise ValueError(f"Unknown LLM provider: {self.config.provider}")

    async def _call_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Call Claude via the Anthropic Messages API."""
        response = await self._http.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.config.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    async def _call_vllm(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Call vLLM via OpenAI-compatible API."""
        response = await self._http.post(
            f"{self.config.vllm_endpoint}/v1/chat/completions",
            json={
                "model": self.config.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def close(self) -> None:
        await self._http.aclose()
