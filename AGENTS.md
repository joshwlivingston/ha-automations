# AGENTS.md

- Check: `uv run pytest && uv run ruff check . && uv run pyright`
- Logic goes in `src/ha_automations/`; `deploy/appdaemon/apps/` holds only shims and `apps.yaml`.
- Release: bump `pyproject.toml` version, tag `vX.Y.Z`, push tags. CI deploys.
- Commits: one-line conventional commits, no AI trailers.
