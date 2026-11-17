from ha_automations.store import FileStore


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def test_save_and_load(tmp_path):
    store = FileStore(tmp_path / "a" / "x.json", max_age=60, now=Clock())
    assert store.load() is None
    store.save(-7.5)
    assert store.load() == -7.5


def test_save_none_clears(tmp_path):
    store = FileStore(tmp_path / "x.json", max_age=60, now=Clock())
    store.save(1)
    store.save(None)
    store.save(None)
    assert store.load() is None
    assert not store.path.exists()


def test_expires(tmp_path):
    clock = Clock()
    store = FileStore(tmp_path / "x.json", max_age=60, now=clock)
    store.save(1)
    clock.t += 60
    assert store.load() == 1
    clock.t += 1
    assert store.load() is None


def test_future_value_ignored(tmp_path):
    clock = Clock()
    store = FileStore(tmp_path / "x.json", max_age=60, now=clock)
    store.save(1)
    clock.t -= 1
    assert store.load() is None


def test_unreadable_is_none(tmp_path):
    path = tmp_path / "x.json"
    path.write_text("{not json")
    assert FileStore(path, max_age=60).load() is None
    path.write_text('{"value": 1}')
    assert FileStore(path, max_age=60).load() is None
