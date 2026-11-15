# AGENTS.md

- Check: `uv run pytest && uv run ruff check . && uv run pyright`
- Snapshots (syrupy) live in `tests/__snapshots__/` and are committed. Accept changes with `uv run pytest --snapshot-update`, then review the diff.
- Logic goes in `src/ha_automations/`; `deploy/appdaemon/apps/` holds only shims; `apps.yaml` lives in a private config repo.
- Changelog: `feat` and `fix` PRs add a line under `## [Unreleased]` in `CHANGELOG.md`, written for users.
- Version: every change bumps the dev version (`uv version X.Y.Z.9NNN`, next 9NNN), so `main` always carries an untagged version.
- Release: `uv run release dev` tags the current dev version and deploys it; `uv run release prod [patch|minor|major|X.Y.Z]` moves `## [Unreleased]` in `CHANGELOG.md` to the new version, bumps, commits, tags and deploys, then deletes older dev tags once CI and the deploy succeed. Both wait for CI on the tag, then run the config repo's deploy workflow (`CONFIG_REPO`, default `<origin owner>/ha-automations-config`); GitHub calls target the `origin` repo, so forks work. `--dry-run` shows what would happen.
- Commits: one-line conventional commits, no AI trailers.
- Docstrings/comments: plain and terse; say what the code does. No en/em dashes, arrows, or flourishes ("pitch black", "takes over"). Reference constants by name, not their values.
- Settings meanings live in `Field(description=...)` on each app's settings model. Docs pages render settings tables, defaults and charts from the code with `docs/_helpers.py`; never hand-write them.
- Docs: Great Docs, config in `great-docs.yml`, homepage `index.qmd`, pages in `docs/`. Preview with `uv run great-docs preview` (needs Quarto). `scripts/build_docs.py` builds the versioned site; see `CONTRIBUTING.md`.
- Docs are for users, in order: User Guide (`docs/user_guide/`), Apps (`docs/apps/`), Reference (generated API). No prose about internals; developer notes go in `CONTRIBUTING.md`. User Guide, homepage and README stay app-agnostic; topics for one group of apps (e.g. sun levels for light apps) go in Apps. Plain, terse, lists and tables over paragraphs.
