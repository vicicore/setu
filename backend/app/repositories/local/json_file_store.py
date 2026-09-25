import json
import os
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any


class JsonFileStore:
    """Atomic read/modify/write over a single JSON file, guarded by an
    in-process lock. Sufficient for a single-instance demo backend;
    a Supabase adapter replaces this entirely, so no attempt is made to
    make this safe for multi-process concurrent writers.

    The in-process lock is per-*instance*, not per-*path* — it only
    serializes calls made through this one object, which is exactly what
    every caller gets in normal operation, since every repository is
    constructed exactly once behind an `lru_cache`d factory
    (app/core/container.py). The one place that isn't true is
    construction itself: `lru_cache` has no "single-flight" behavior, so
    two concurrent requests that are both the very first to touch a
    given repository (e.g. two demo panels silently logging in at once
    against a brand-new data directory) can each construct their own
    `JsonFileStore` for the same path before either result is cached.
    Real bug hit exactly this way in Phase 7 browser testing: both
    constructors wrote the same fixed `<path>.tmp` name for their
    initial write, and one's `os.replace` failed with WinError 32
    (target file in use by the other). Giving every write call its own
    unique temp filename fixes the collision — the two writers' content
    is equivalent here (both are writing the same `default` value), so
    whichever one's rename wins first is fine."""

    def __init__(self, path: str | Path, default: Any) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self._path.exists():
            self._write(default)

    def read(self) -> Any:
        with self._lock:
            if not self._path.exists():
                return None
            with open(self._path, encoding="utf-8") as f:
                return json.load(f)

    def _tmp_path(self) -> Path:
        return self._path.with_suffix(f"{self._path.suffix}.{uuid.uuid4().hex}.tmp")

    def _write(self, data: Any) -> None:
        tmp_path = self._tmp_path()
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp_path, self._path)

    def mutate(self, fn: Callable[[Any], Any]) -> Any:
        """Read, apply fn(data) -> new_data, write back, return new_data."""
        with self._lock:
            data = {}
            if self._path.exists():
                with open(self._path, encoding="utf-8") as f:
                    data = json.load(f)
            new_data = fn(data)
            tmp_path = self._tmp_path()
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=2, default=str)
            os.replace(tmp_path, self._path)
            return new_data
