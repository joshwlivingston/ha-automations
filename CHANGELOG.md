# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Each release section is published as its GitHub release.

## [Unreleased]

### Bugfixes

- Light apps with start triggers, like Sunrise Fade, carry on a fade after AppDaemon or Home Assistant restarts (#28).
- Light apps without start triggers, like Sunset Fade, set the light as soon as they load, not at the next sun update (#28).

- `uv run release prod` no longer fails when GitHub deletes the release branch on merge (#18).
- Rerun `uv run release prod` to tag and deploy a release that was merged but never tagged (#18).

### Documentation

- The docs site rebuilds when a tag is pushed or deleted (#19).
- Building several docs versions at once no longer fails (#21).
- The Changelog page of dev and dev tag docs lists unreleased changes first (#26, #27).

### Defaults

| App | Setting | Was | Now |
|---|---|---|---|
| Light apps | `min_brightness` | 5 | 0 |
| Light apps | `max_brightness` | 50 | 100 |
| Sunset Fade | `from_level` | 6 | 12 |

## [0.2.0] - 2026-11-15

### Breaking changes

- Sunset Fade turns its light off at 23:00 by default. Set `off_time: null` to keep it on (#12).
- Log lines read `action: reason; key=value ...`, e.g. `load: init; light=light.bedroom_lamp` (#2, #6).
- `scripts/deploy.sh` refuses tags other than `vX.Y.Z` and `vX.Y.Z.9xxx` (#3).

### New features

- `off_time` turns a light app's light off at a set time, e.g. `"23:00:00"` (#12).
- `uv run release` tags a version and deploys it from your config repo once CI passes; `prod` merges into `main` by pull request (#8, #9, #16).
- `DEV=1 scripts/deploy.sh vX.Y.Z.9xxx` deploys a dev tag for testing before release (#3).
- GitHub releases take their notes from `CHANGELOG.md` (#4).

### Bugfixes

- Logs write sun levels as `-6deg`; the degree sign showed garbled in AppDaemon (#7).

### Documentation

- The docs are rewritten for users, in three parts: User Guide, Apps, Reference (#11).
- The docs site opens on the latest release, with a version selector for every release and dev tag; `dev` holds unreleased changes (#13).
- Each GitHub release has its docs attached (#14).

## [0.1.0] - 2026-11-14

- Initial release.

[Unreleased]: https://github.com/joshwlivingston/ha-automations/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/joshwlivingston/ha-automations/releases/tag/v0.2.0
[0.1.0]: https://github.com/joshwlivingston/ha-automations/releases/tag/v0.1.0
