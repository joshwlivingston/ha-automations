"""Stores that keep one number across restarts.

A store saves a number, or None to clear it, and loads it back. Values older
than the store's max age load as None.
"""
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol


class Store(Protocol):
    def load(self) -> float | None:
        """The saved value, or None if there is none or it expired."""
        ...

    def save(self, value: float | None) -> None:
        """Save `value`, or clear the store if None."""
        ...


class FileStore:
    """A JSON file at `path`. Values expire after `max_age` seconds."""

    def __init__(self, path: Path, max_age: float, now: Callable[[], float] = time.time):
        self.path = path
        self.max_age = max_age
        self.now = now

    def __str__(self) -> str:
        return str(self.path)

    def load(self) -> float | None:
        try:
            data = json.loads(self.path.read_text())
            value, saved_at = float(data["value"]), float(data["saved_at"])
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if not 0 <= self.now() - saved_at <= self.max_age:
            return None
        return value

    def save(self, value: float | None) -> None:
        if value is None:
            self.path.unlink(missing_ok=True)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"value": value, "saved_at": self.now()}))
        tmp.replace(self.path)
