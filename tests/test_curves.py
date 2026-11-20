from ha_automations.curves import clamp, decay, ease_in, lerp, progress


def test_clamp_bounds():
    assert clamp(-1) == 0.0
    assert clamp(2) == 1.0
    assert clamp(0.3) == 0.3
    assert clamp(15, lo=0, hi=10) == 10


def test_progress_ascending():
    assert progress(-6, -6, 0) == 0.0
    assert progress(-3, -6, 0) == 0.5
    assert progress(0, -6, 0) == 1.0


def test_progress_descending():
    assert progress(6, 6, -6) == 0.0
    assert progress(0, 6, -6) == 0.5
    assert progress(-6, 6, -6) == 1.0


def test_progress_clamps_outside_range():
    assert progress(-10, -6, 0) == 0.0
    assert progress(5, -6, 0) == 1.0
    assert progress(10, 6, -6) == 0.0
    assert progress(-10, 6, -6) == 1.0


def test_ease_in_endpoints_and_bias():
    assert ease_in(0.0) == 0.0
    assert ease_in(1.0) == 1.0
    assert ease_in(0.5) < 0.5  # early steps are subtler


def test_lerp():
    assert lerp(5, 50, 0) == 5
    assert lerp(5, 50, 1) == 50
    assert lerp(0, 10, 0.5) == 5


def test_decay_endpoints_and_shape():
    assert decay(0) == 1.0
    assert decay(1) == 0.0
    assert decay(0.25) > 0.95
    assert decay(0.9) < 0.1
