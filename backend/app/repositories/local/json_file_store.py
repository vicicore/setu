import json
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any


class JsonFileStore:
    """Atomic read/modify/write over a single JSON file, guarded by an
    in-process lock. Sufficient for a single-instance demo backend;
    a Supabase adapter replaces this entirely, so no attempt is made to
    make this safe for multi-process concurrent writers."""

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

    def _write(self, data: Any) -> None:
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
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
            tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=2, default=str)
            os.replace(tmp_path, self._path)
            return new_data
