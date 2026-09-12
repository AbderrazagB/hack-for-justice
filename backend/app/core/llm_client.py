from typing import Literal

import google.generativeai as genai
from mistralai.client import Mistral

from app.core.config import settings

Provider = Literal["mistral", "gemini"]


class LLMClient:
    """Small provider-neutral client for text generation."""

    def __init__(self, provider: Provider = "mistral") -> None:
        self.provider = provider

    def generate(self, prompt: str, system: str = "") -> str:
        if self.provider == "gemini":
            return self._generate_gemini(prompt, system)

        try:
            return self._generate_mistral(prompt, system)
        except Exception:  # noqa: BLE001 - any Mistral failure triggers the requested fallback.
            return self._generate_gemini(prompt, system)

    def _generate_mistral(self, prompt: str, system: str) -> str:
        if not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is not configured")

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = Mistral(api_key=settings.mistral_api_key).chat.complete(
            model="mistral-small-latest",
            messages=messages,
        )
        content = response.choices[0].message.content
        return content if isinstance(content, str) else str(content)

    def _generate_gemini(self, prompt: str, system: str) -> str:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            system_instruction=system or None,
        )
        return model.generate_content(prompt).text
