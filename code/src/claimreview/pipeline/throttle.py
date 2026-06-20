"""Simple deterministic throttle to stay under provider RPM limits."""

from __future__ import annotations

import time


def sleep_ms(ms: int) -> None:
    """Block for `ms` milliseconds between model calls (no-op for ms <= 0)."""
    if ms and ms > 0:
        time.sleep(ms / 1000.0)
