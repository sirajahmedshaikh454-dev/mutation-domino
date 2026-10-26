from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)
SAFE_KEY = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
SAFE_SUFFIX = re.compile(r"^\.[A-Za-z0-9]{1,10}$")


class CacheError(RuntimeError):
    pass


@dataclass(frozen=True)
class CacheEntry:
    path: Path
    sha256: str
    size_bytes: int


class DiskCache:
    def __init__(self, root: Path, max_bytes: int) -> None:
        self.root = root
        self.max_bytes = max_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def _validate(self, key: str, suffix: str) -> None:
        if not SAFE_KEY.fullmatch(key):
            raise CacheError("Unsafe cache key.")
        if not SAFE_SUFFIX.fullmatch(suffix):
            raise CacheError("Unsafe cache suffix.")

    def path_for(self, key: str, suffix: str) -> Path:
        self._validate(key, suffix)
        return self.root / f"{key}{suffix}"

    def read_bytes(self, key: str, suffix: str) -> bytes | None:
        path = self.path_for(key, suffix)
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None

    def read_json(self, key: str, suffix: str = ".json") -> Any | None:
        payload = self.read_bytes(key, suffix)
        if payload is None:
            return None
        try:
            return json.loads(payload)
        except (UnicodeDecodeError, ValueError):
            logger.warning("Ignoring malformed cache JSON for %s", key)
            path = self.path_for(key, suffix)
            path.unlink(missing_ok=True)
            return None

    def _atomic_write(self, path: Path, data: bytes) -> None:
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(self.root))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        except Exception:
            Path(temp_name).unlink(missing_ok=True)
            raise

    def put_bytes(self, key: str, data: bytes, suffix: str) -> CacheEntry:
        if len(data) > self.max_bytes:
            raise CacheError("Single cache entry exceeds cache budget.")
        path = self.path_for(key, suffix)
        self._atomic_write(path, data)
        digest = hashlib.sha256(data).hexdigest()
        self.prune()
        return CacheEntry(path=path, sha256=digest, size_bytes=len(data))

    def put_json(self, key: str, value: Any, suffix: str = ".json") -> CacheEntry:
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        return self.put_bytes(key, data, suffix)

    def total_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.root.glob("*") if p.is_file())

    def prune(self) -> None:
        files = sorted(
            (p for p in self.root.glob("*") if p.is_file() and not p.name.startswith(".")),
            key=lambda p: p.stat().st_mtime,
        )
        total = sum(p.stat().st_size for p in files)
        while files and total > self.max_bytes:
            oldest = files.pop(0)
            try:
                total -= oldest.stat().st_size
                oldest.unlink()
                logger.info("Pruned cache entry %s", oldest.name)
            except FileNotFoundError:
                continue
