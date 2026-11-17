from ha_automations.store import JsonFile


def test_save_and_load(tmp_path):
    store = JsonFile(tmp_path / "a" / "x.json")
    assert store.load() is None
    store.save({"a": 1.5, "b": "x"})
    assert store.load() == {"a": 1.5, "b": "x"}


def test_save_none_clears(tmp_path):
    store = JsonFile(tmp_path / "x.json")
    store.save({"a": 1})
    store.save(None)
    store.save(None)
    assert store.load() is None
    assert not store.path.exists()


def test_unreadable_is_none(tmp_path):
    path = tmp_path / "x.json"
    path.write_text("{not json")
    assert JsonFile(path).load() is None
    path.write_text("[1, 2]")
    assert JsonFile(path).load() is None
