"""Reusable light actions (take the calling AppDaemon app as first argument)."""


def brightness_pct(app, entity_id):
    """Current brightness in percent (0 if off)."""
    if app.get_state(entity_id) != "on":
        return 0
    return round((app.get_state(entity_id, attribute="brightness") or 0) / 2.55)


def brighten_only(app, entity_id, pct, transition=60):
    """Raise a light to `pct`, never lower it – respects manual adjustments."""
    if pct > brightness_pct(app, entity_id):
        app.call_service(
            "light/turn_on", entity_id=entity_id, brightness_pct=pct, transition=transition
        )
