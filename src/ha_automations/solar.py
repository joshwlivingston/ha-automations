"""Sun position helpers."""


def parse_sun(attrs):
    """(elevation, rising) from `sun.sun` attributes; elevation is None if missing."""
    elevation = attrs.get("elevation")
    return (None if elevation is None else float(elevation)), bool(attrs.get("rising"))


def sun_state(app):
    """Current (elevation, rising) of the sun, read through an AppDaemon app."""
    entity = app.get_state("sun.sun", attribute="all") or {}
    return parse_sun(entity.get("attributes") or {})
