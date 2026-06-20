"""Deterministic response cache to save quota on dev reruns.

Key = SHA-256 over the inputs that determine a claim's output (system prompt + claim
text/object + image_paths + history). Value = the validated 10 generated fields. Backed by
SQLite. A cache hit bypasses the model entirely — important when iterating on prompts over
the same claims, and it makes reruns near-instant and free.

Assumption: image files at a given path are stable within a run (true for the fixed
dataset), so the path identifies the image bytes. Change the strategy/prompt and keys
change, so a prompt edit correctly invalidates the cache.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


class ResponseCache:
    def __init__(self, path: str, enabled: bool = True) -> None:
        self.path = path
        self.enabled = enabled
        self._conn: sqlite3.Connection | None = None
        if enabled:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(path)
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)"
            )
            self._conn.commit()

    @staticmethod
    def make_key(*parts: str) -> str:
        """Return the SHA-256 hex digest of the NUL-joined string parts."""
        h = hashlib.sha256()
        for part in parts:
            h.update(str(part).encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()

    def get(self, key: str) -> dict | None:
        if not (self.enabled and self._conn):
            return None
        row = self._conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, key: str, value: dict) -> None:
        if not (self.enabled and self._conn):
            return
        self._conn.execute(
            "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)", (key, json.dumps(value))
        )
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
