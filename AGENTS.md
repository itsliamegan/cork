# AGENTS

## Helios

Helios lives outside this repo in `../helios/` (editable path dep, see
`[tool.uv.sources]`). It is small — read it directly rather than guessing at its
API. See Helios' own README for the module breakdown.

### Friction

A working list of issues or pain points with the framework is kept in
`.agents/notes/dogfooding.md` under the "Helios framework" section.

Any notes should be listed as you encounter them and removed when fixed. The
file represents a current working state, not a historical record.

## Commands

- `mise run serve`: Run a devserver on port 4000 with the reloader watching views
  and assets. This should always already be running in the background, never
  start one yourself.
- `mise run lint`: Run Ruff for formatting & linting and Ty for type checking.
  This should be run before considering any changes finished.
