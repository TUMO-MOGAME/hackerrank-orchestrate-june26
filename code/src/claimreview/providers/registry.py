"""Select and construct a VisionProvider from configuration.

Keeps provider choice in one place so main.py / api / evaluation all resolve the
same way: `get_provider(settings)`. API keys are read from the environment here, not
stored in Settings, so secrets never live in a config object.
"""

from __future__ import annotations

import os

from claimreview.config import Settings
from claimreview.providers.base import VisionProvider

# Per-provider env var(s) for the API key; first non-empty wins.
_KEY_ENV = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
}


def _require_key(provider: str, env: dict) -> str:
    for name in _KEY_ENV[provider]:
        val = env.get(name)
        if val:
            return val
    names = " or ".join(_KEY_ENV[provider])
    raise RuntimeError(f"{provider} provider selected but {names} is not set in the environment")


def get_provider(settings: Settings, env: dict | None = None) -> VisionProvider:
    """Return the configured provider adapter. Adapters are imported lazily so an
    unused provider's SDK need not be installed."""
    e = os.environ if env is None else env
    provider = settings.provider

    if provider == "fake":
        from claimreview.providers.fake_provider import FakeProvider

        return FakeProvider()
    if provider == "anthropic":
        from claimreview.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=_require_key("anthropic", e), model=settings.model)
    if provider == "gemini":
        from claimreview.providers.gemini_provider import GeminiProvider

        return GeminiProvider(api_key=_require_key("gemini", e), model=settings.model)
    if provider == "openai":
        from claimreview.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=_require_key("openai", e), model=settings.model)
    raise ValueError(f"unknown provider: {provider!r}")
