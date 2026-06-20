"""Runtime configuration. Secrets are read from environment variables ONLY.

Per the repo AGENTS.md §6.2: never hardcode secrets; use env vars + a .env file.
Provider is selectable so the same core runs against Gemini, Claude, or OpenAI.

NOTE: structure only — concrete settings loading is stubbed (build step 1).
"""

from __future__ import annotations

from dataclasses import dataclass

# Repo-relative dataset paths (resolved against the repo root at runtime).
DATASET_DIR = "dataset"
SAMPLE_CLAIMS_CSV = "dataset/sample_claims.csv"
CLAIMS_CSV = "dataset/claims.csv"
USER_HISTORY_CSV = "dataset/user_history.csv"
EVIDENCE_REQUIREMENTS_CSV = "dataset/evidence_requirements.csv"
IMAGES_DIR = "dataset/images"

# "fake" is an offline, deterministic provider for tests/demos (no API key/cost).
SUPPORTED_PROVIDERS = ("anthropic", "gemini", "openai", "fake")


@dataclass(frozen=True)
class Settings:
    """Resolved configuration for a run.

    TODO (build step 1): populate from env via a `load()` classmethod —
    provider, model id, api key (per provider), throttle ms, max retries,
    cache path/enabled, request timeout.
    """

    provider: str = "anthropic"
    model: str | None = None
    throttle_ms: int = 0          # delay between model calls; tune per provider RPM
    max_retries: int = 3
    cache_enabled: bool = True
    cache_path: str = ".cache/claimreview.sqlite"
    request_timeout_s: int = 60

    @classmethod
    def load(cls, env: dict | None = None) -> Settings:
        """Build Settings from environment variables (defaults applied when unset).

        Pure/deterministic — reads config only, never contacts a provider. API keys are
        resolved later by the provider registry, not here.
        """
        import os

        e = os.environ if env is None else env

        def _int(key: str, default: int) -> int:
            try:
                return int(e.get(key, default))
            except (TypeError, ValueError):
                return default

        def _bool(key: str, default: bool) -> bool:
            v = e.get(key)
            if v is None:
                return default
            return str(v).strip().lower() in {"1", "true", "yes", "on"}

        provider = (e.get("CLAIMREVIEW_PROVIDER") or cls.provider).strip().lower()
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"CLAIMREVIEW_PROVIDER={provider!r} not in {SUPPORTED_PROVIDERS}"
            )
        return cls(
            provider=provider,
            model=(e.get("CLAIMREVIEW_MODEL") or None),
            throttle_ms=_int("CLAIMREVIEW_THROTTLE_MS", cls.throttle_ms),
            max_retries=_int("CLAIMREVIEW_MAX_RETRIES", cls.max_retries),
            cache_enabled=_bool("CLAIMREVIEW_CACHE_ENABLED", cls.cache_enabled),
            cache_path=(e.get("CLAIMREVIEW_CACHE_PATH") or cls.cache_path),
            request_timeout_s=_int("CLAIMREVIEW_REQUEST_TIMEOUT_S", cls.request_timeout_s),
        )
