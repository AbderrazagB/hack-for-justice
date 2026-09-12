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
from functools import lru_cache
from typing import Literal

from app.core.config import settings
from app.core.retry import with_retry

logger = logging.getLogger(__name__)

Provider = Literal["mistral", "gemini"]

GEMINI_MODEL = "gemini-2.0-flash"

# Preference order for text generation, Apache-2.0 open-weight first -- the
# same sovereignty argument as the vision model, and verified to be what a
# standard key can actually reach: mistral-small-latest and
# mistral-medium-latest answer 429 "Rate limit exceeded" on tiers that do not
# include them, which is indistinguishable from a transient limit and would
# silently disable the assistant.
CHAT_MODEL_PREFERENCE = [
    "ministral-8b-2512",
    "ministral-14b-2512",
    "mistral-small-latest",
    "mistral-medium-latest",
]


class LLMError(RuntimeError):
    """Raised when no configured provider could answer."""


@lru_cache(maxsize=1)
def _resolve_chat_model(preferred: str) -> str:
    """Pick a text model the account can actually reach.

    Mirrors the vision-model resolver: ask the API rather than trust a
    constant, because an unavailable model reports a rate limit rather than a
    404 and would otherwise look like a transient outage forever.
    """
    try:
        from mistralai.client import Mistral

        available = {
            m.id for m in Mistral(api_key=settings.mistral_api_key).models.list().data
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not list Mistral models (%s); using %s", exc, preferred)
        return preferred

    for candidate in [preferred, *CHAT_MODEL_PREFERENCE]:
        if candidate in available:
            return candidate
    return preferred


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
            except Exception as fallback_exc:
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

        model = _resolve_chat_model(settings.chat_model)
        client = Mistral(api_key=settings.mistral_api_key)
        response = with_retry(
            lambda: client.chat.complete(model=model, messages=messages),
            description=f"Mistral chat ({model})",
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
