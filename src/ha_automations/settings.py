"""Read app settings from AppDaemon args."""
from collections.abc import Collection
from dataclasses import fields
from typing import Any


def settings_for(cls, args: dict[str, Any], exclude: Collection[str] = ()) -> dict[str, Any]:
    """Entries of `args` that set an init field of dataclass `cls`, other than those in `exclude`."""
    names = {f.name for f in fields(cls) if f.init} - set(exclude)
    return {k: v for k, v in args.items() if k in names}
