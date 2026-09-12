"""Provider-neutral text generation for Sahilli.

Mistral is primary; Gemini is the fallback so a single provider outage cannot
take the demo down. Both are reached over their vendor APIs -- unlike the
retrieval stack, this layer is not self-hosted yet. See README > Local AI
Infrastructure for why that split is deliberate and what the migration path is.

Uses `google-genai`, not `google-generativeai`: the latter is end-of-life and
warns on every import.
"""

from __future__ import annotations

import logging
from typing import Literal

from app.core.config import settings

logger = logging.getLogger(__name__)

Provider = Literal["mistral", "gemini"]

MISTRAL_MODEL = "mistral-small-latest"
GEMINI_MODEL = "gemini-2.0-flash"


class LLMError(RuntimeError):
    """Raised when no configured provider could answer."""


class LLMClient:
    """Small provider-neutral client for text generation."""

    def __init__(self, provider: Provider = "mistral") -> None:
        self.provider = provider

    def generate(self, prompt: str, system: str = "") -> str:
        if self.provider == "gemini":
            return self._generate_gemini(prompt, system)

        try:
            return self._generate_mistral(prompt, system)
        except Exception as exc:  # noqa: BLE001 - any Mistral failure triggers fallback
            logger.warning("Mistral generation failed, falling back to Gemini: %s", exc)
            try:
                return self._generate_gemini(prompt, system)
            except Exception as fallback_exc:  # noqa: BLE001
                raise LLMError(
                    f"Both providers failed. Mistral: {exc}. Gemini: {fallback_exc}"
                ) from fallback_exc

    def _generate_mistral(self, prompt: str, system: str) -> str:
        if not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is not configured")

        from mistralai.client import Mistral

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = Mistral(api_key=settings.mistral_api_key).chat.complete(
            model=MISTRAL_MODEL,
            messages=messages,
        )
        content = response.choices[0].message.content
        return content if isinstance(content, str) else str(content)

    def _generate_gemini(self, prompt: str, system: str) -> str:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system or None),
        )
        return response.text or ""
