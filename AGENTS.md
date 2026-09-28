# AGENTS

## Helios

Helios lives outside this repo in `../helios/`, but Cork installs it (and Luna)
as a git dependency pinned in `uv.lock` (see `[tool.uv.sources]`). It is small —
read it directly rather than guessing at its API. See Helios' own README for the
module breakdown.

Local changes to `../helios/` or `../luna/` reach Cork only once pushed and
re-locked with `uv lock --upgrade-package helios` (or `luna`).

### Friction

A working list of issues or pain points with the framework is kept in
`.agents/notes/dogfooding.md` under the "Helios framework" section.

Any notes should be listed as you encounter them and removed when fixed. The
file represents a current working state, not a historical record.

## Commands

- `mise run serve`: Run a devserver on port 4000 with the reloader watching views
  and assets. This should always already be running in the background, never
  start one yourself.
- `mise run lint`: Run Ruff for formatting & linting.
- `mise run check`: Run Ty for type checking.

## Workflow

Always ensure the test suite passes, the formatter is clean, and the type
checker reports no errors before considering any work complete.

CI runs these steps on every pull request and before every deploy.
