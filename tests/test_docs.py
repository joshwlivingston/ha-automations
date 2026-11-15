import html
import json

from ha_automations_docs import releases, set_version_map, version_map


def test_releases_newest_first_without_dev_tags():
    tags = ["v0.1.0", "v0.1.0.9001", "v0.10.0", "v0.2.0", "v1.0", "other"]
    assert releases(tags) == ["0.10.0", "0.2.0", "0.1.0"]


def test_version_map_newest_release_is_latest_at_root():
    data = version_map(["0.2.0", "0.1.0"])
    assert data["versions"] == [
        {"tag": "dev", "label": "dev", "path_prefix": "v/dev", "prerelease": True},
        {"tag": "0.2.0", "label": "0.2.0", "latest": True, "path_prefix": ""},
        {"tag": "0.1.0", "label": "0.1.0", "path_prefix": "v/0.1.0"},
    ]


def test_set_version_map_replaces_meta_content():
    page = '<head><meta name="gd-version-map" content="{&quot;old&quot;:1}"></head>'
    data = version_map(["0.1.0"])
    new = set_version_map(page, data)
    content = new.split('content="')[1].split('"')[0]
    assert json.loads(html.unescape(content)) == data
    assert new.startswith("<head>") and new.endswith("</head>")
