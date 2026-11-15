# AGENTS.md

- Check: `uv run pytest && uv run ruff check . && uv run pyright`
- Logic goes in `src/ha_automations/`; `deploy/appdaemon/apps/` holds only shims; `apps.yaml` lives in a private config repo.
- Release: bump `pyproject.toml` version, tag `vX.Y.Z`, push tags. CI deploys.
- Commits: one-line conventional commits, no AI trailers.
- Docstrings/comments: plain and terse; say what the code does. No en/em dashes, arrows, or flourishes ("pitch black", "takes over"). Reference constants by name, not their values.
- Settings meanings live in `Field(description=...)` on each app's settings model. Docs pages render settings tables, defaults and charts from the code with `docs/_helpers.py`; never hand-write them.
- Docs: Great Docs, config in `great-docs.yml`, homepage `index.qmd`, pages in `docs/`. Preview with `uv run great-docs preview` (needs Quarto).
