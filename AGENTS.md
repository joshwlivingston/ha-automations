# AGENTS.md

- Check: `uv run pytest && uv run ruff check . && uv run pyright`
- Logic goes in `src/ha_automations/`; `deploy/appdaemon/apps/` holds only shims; `apps.yaml` lives in a private config repo.
- Release: bump `pyproject.toml` version, tag `vX.Y.Z`, push tags. CI deploys.
- Commits: one-line conventional commits, no AI trailers.
- Docstrings/comments: plain and terse; say what the code does. No en/em dashes, arrows, or flourishes ("pitch black", "takes over"). Reference constants by name, not their values.
