from __future__ import annotations

import json
import time
from pathlib import Path

CACHE_FILENAME = "cfps.json"
META_FILENAME = "meta.json"


class Cache:
    def __init__(self, cache_dir: Path, ttl_seconds: int = 3600) -> None:
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self._data_path = cache_dir / CACHE_FILENAME
        self._meta_path = cache_dir / META_FILENAME

    def read(self, *, allow_stale: bool = False) -> list | None:
        if not self._data_path.exists() or not self._meta_path.exists():
            return None
        meta = json.loads(self._meta_path.read_text())
        age = time.time() - meta["written_at"]
        if age > self.ttl_seconds and not allow_stale:
            return None
        return json.loads(self._data_path.read_text())

    def write(self, data: list) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._data_path.write_text(json.dumps(data))
        self._meta_path.write_text(json.dumps({"written_at": time.time()}))
