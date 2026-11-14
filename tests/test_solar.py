from ha_automations.solar import parse_sun


def test_normal_attributes():
    assert parse_sun({"elevation": -4.2, "rising": True}) == (-4.2, True)


def test_missing_elevation():
    assert parse_sun({"rising": False}) == (None, False)


def test_string_elevation():
    assert parse_sun({"elevation": "3.5", "rising": False}) == (3.5, False)


def test_empty():
    assert parse_sun({}) == (None, False)
