"""Log line format shared by apps."""


def line(action: str, reason: str, detail: str = "") -> str:
    """One log line: action, reason and optional detail."""
    return f"{action}: {reason}; {detail}" if detail else f"{action}: {reason}"
