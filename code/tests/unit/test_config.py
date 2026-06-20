"""Settings.load() tests — pure env parsing, no provider contact."""

from __future__ import annotations

import pytest

from claimreview.config import Settings


def test_defaults_when_env_empty():
    s = Settings.load(env={})
    assert s.provider == "anthropic"
    assert s.max_retries == 3
    assert s.cache_enabled is True


def test_reads_env_overrides():
    s = Settings.load(env={
        "CLAIMREVIEW_PROVIDER": "gemini",
        "CLAIMREVIEW_MODEL": "some-model",
        "CLAIMREVIEW_THROTTLE_MS": "4100",
        "CLAIMREVIEW_CACHE_ENABLED": "false",
    })
    assert s.provider == "gemini"
    assert s.model == "some-model"
    assert s.throttle_ms == 4100
    assert s.cache_enabled is False


def test_rejects_unknown_provider():
    with pytest.raises(ValueError):
        Settings.load(env={"CLAIMREVIEW_PROVIDER": "skynet"})
