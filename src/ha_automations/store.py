"""Stores that keep one record across restarts.

A record is a dict of JSON types. Saving None clears the store.
"""
import json
from pathlib import Path
from typing import Protocol


class Store(Protocol):
    def load(self) -> dict | None:
        """The saved record, or None if there is none."""
        ...

    def save(self, record: dict | None) -> None:
        """Save `record`, or clear the store if None."""
        ...


class JsonFile:
    """A record in a JSON file at `path`. An unreadable file loads as None."""

    def __init__(self, path: Path):
        self.path = path

    def __str__(self) -> str:
        return str(self.path)

    def load(self) -> dict | None:
        try:
            record = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return None
        return record if isinstance(record, dict) else None

    def save(self, record: dict | None) -> None:
        if record is None:
            self.path.unlink(missing_ok=True)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record))
        tmp.replace(self.path)
