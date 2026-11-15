"""Build-time helpers for docs pages. Pages import this from a `{python}` cell.

Every table, example and chart here is generated from the package so the docs
follow the code.
"""
import inspect
import re
from types import ModuleType

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from ha_automations.apps.light_fade import LightFadeSettings
from ha_automations.curves import progress
from ha_automations.fades import brightness_at

ACCENT = "#e8902a"
MUTED = "#8a8f98"


def _fmt(value) -> str:
    """Markdown for a settings default."""
    if value is PydanticUndefined:
        return "required"
    if value is None:
        return "unset"
    if isinstance(value, BaseModel):
        return " ".join(f"`{k}: {v}`" for k, v in value.model_dump().items())
    if isinstance(value, tuple):
        if not value:
            return "`[]`"
        return "<br>".join(f"`- {_fmt_trigger(v)}`" for v in value)
    return f"`{value}`"


def _fmt_trigger(trigger: BaseModel) -> str:
    return ", ".join(f'{k}: "{v}"' for k, v in trigger.model_dump().items())


def settings_table(cls: type[BaseModel]) -> None:
    """Print a Markdown table of the settings in `cls`. Use with `output: asis`."""
    print("| Setting | Default | Meaning |")
    print("|---|---|---|")
    for name, field in cls.model_fields.items():
        print(f"| `{name}` | {_fmt(field.default)} | {field.description} |")


def compare_table(apps: list[tuple[str, str, type[LightFadeSettings], str]]) -> None:
    """Print a Markdown table comparing apps. Each entry is (title, link, settings, summary).

    Use with `output: asis`.
    """
    print("| App | What it does | `start` | `from_level` | `to_level` | `off_level` |")
    print("|---|---|---|---|---|---|")
    for title, link, cls, summary in apps:
        f = cls.model_fields
        cells = [_fmt(f[name].default) for name in ("start", "from_level", "to_level", "off_level")]
        print(f"| [{title}]({link}) | {summary} | {' | '.join(cells)} |")


def usage_yaml(module: ModuleType) -> None:
    """Print the Usage block of an app module's docstring as YAML. Use with `output: asis`."""
    doc = inspect.getdoc(module) or ""
    match = re.search(r"Usage\n-+\n(.*?)\n\n", doc, re.DOTALL)
    if match is None:
        raise ValueError(f"{module.__name__} has no Usage block")
    print(f"```yaml\n{match.group(1)}\n```")


def fade_chart(cls: type[LightFadeSettings], *, height: float = 3.0, ramp_from: float | None = None, **overrides):
    """Plot light brightness against level for the defaults in `cls`.

    `overrides` replace defaults, for settings that have none. A triggered fade
    (non-empty `start`) ramps from the level when the trigger fired, which is
    short of from_level; `ramp_from` sets that example level. The x-axis runs
    in the fade's direction, so time reads left to right.
    """
    import matplotlib.pyplot as plt

    s = {name: f.default for name, f in cls.model_fields.items()} | overrides
    lo_b, hi_b = s["min_brightness"], s["max_brightness"]
    start, end, off = s["from_level"], s["to_level"], s["off_level"]
    sign = 1 if end > start else -1
    span = abs(end - start)
    if s["start"] and ramp_from is None:
        ramp_from = start - sign * span * 0.5
    ramp = start if ramp_from is None else ramp_from
    last = off if off is not None else end
    left, right = ramp - sign * span * 0.3, last + sign * span * 0.3

    steps = 400
    xs = [left + (right - left) * i / steps for i in range(steps + 1)]

    def brightness(x: float) -> float:
        if sign * (x - ramp) < 0:
            return 0
        if off is not None and sign * (x - off) >= 0:
            return 0
        return brightness_at(progress(x, ramp, end), lo_b, hi_b)

    ys = [brightness(x) for x in xs]

    fig, ax = plt.subplots(figsize=(7, height))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    ax.fill_between(xs, ys, color=ACCENT, alpha=0.18, linewidth=0)
    ax.plot(xs, ys, color=ACCENT, linewidth=2.2)

    marks = [(f"from_level\n{start:g}", start), (f"to_level\n{end:g}", end)]
    if ramp_from is not None:
        marks.insert(0, ("start fires\n(example)", ramp_from))
    if off is not None:
        marks.append((f"off_level\n{off:g}", off))
    for label, x in marks:
        ax.axvline(x, ymax=1.05 / 1.35, color=MUTED, linestyle="--", linewidth=1)
        ax.annotate(label, (x, hi_b * 1.08), ha="center", va="bottom", fontsize=8, color=MUTED)

    ax.set_xlim(left, right)
    ax.set_ylim(0, hi_b * 1.35)
    ax.set_xlabel("sun elevation, degrees")
    ax.set_ylabel("brightness, %")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for item in (ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(), *ax.get_yticklabels()):
        item.set_color(MUTED)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    fig.tight_layout()
    plt.show()
