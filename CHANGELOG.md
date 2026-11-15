# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Each release section is published as its GitHub release.

## [Unreleased]

- `scripts/deploy.sh` deploys dev tags (`vX.Y.Z.9xxx`) only with `DEV=1`, so you can test a build on the box before releasing it. Tags that are neither `vX.Y.Z` nor `vX.Y.Z.9xxx` are refused.
- Sun levels in logs use `deg` instead of the degree sign, which showed as garbled characters in the AppDaemon log (e.g. `from_level=-6deg`).
- `uv run release dev` and `uv run release prod` tag a release, wait for CI, and deploy it from your config repo.

## [0.1.0] - 2026-11-14

- Initial release.

[Unreleased]: https://github.com/joshwlivingston/ha-automations/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/joshwlivingston/ha-automations/releases/tag/v0.1.0
