# AGENTS

## Helios

Helios lives outside this repo in `../helios/`, but Cork installs it (and Luna)
as a git dependency pinned in `uv.lock` (see `[tool.uv.sources]`). It is small —
read it directly rather than guessing at its API. See Helios' own README for the
module breakdown.

Local changes to `../helios/` or `../luna/` reach Cork only once pushed and
re-locked. Helios is five packages from one repository. Upgrading `helios` alone
leaves the lock unchanged, so upgrade all five together:

```sh
uv lock --upgrade-package helios --upgrade-package helios-assets \
	--upgrade-package helios-database --upgrade-package helios-url \
	--upgrade-package helios-view
```

Re-lock Luna with `uv lock --upgrade-package luna`.

### Friction

A working list of issues or pain points with the framework is kept in
`.agents/notes/dogfooding.md` under the "Helios framework" section.

Any notes should be listed as you encounter them and removed when fixed. The
file represents a current working state, not a historical record.

## Commands

- `just serve`: Run `bin/helios serve`, the devserver, on the host at
  `APP_BASE_URL` (port 4000). It serves `public/`, and recompiles the assets and
  restarts on any change to a Python file, a view, or an asset. This should always already be running in the
  background, never start one yourself.
- `just migrate`: Apply pending migrations to the database `.env` names.
- `just test`: Compile the assets with esbuild, which needs `npm ci` first,
  and run the test suite.
- `just lint`: Run Ruff for formatting & linting.
- `just check`: Run Ty for type checking.

The development database in `./data` can be overwritten without asking. Seed
representative dummy data there for browser checks, and leave it in place.

## Design

- Models hold domain rules and record changes. They never validate or
  normalize user input. The HTTP layer does, through form objects when the
  validation is worth extracting from a controller.
- Models never shape data only for display, such as grouping rows or picking
  fields for a page. That belongs in the controller. The canonical order of
  pins on a board and of boards on the index is domain, so it lives in the
  models (`Placement.arrange`, `Ordering.arrange`).

## Code

- Export domain classes from `app/__init__.py`, but not their exceptions.
  Import an exception from its module (`from app.move import OutOfDate`).
- Give a field that holds a UUID an `_id` suffix (`record_id`).
- The generic name for a model instance is `record`.

## Testing

- HTTP tests do not assert on markup, such as page copy or hidden-field
  values. Markup checks belong in the component tests in `test/views/`.
- Test a form in the test file for the module that declares it, beside the
  controller's tests (`PinForm` in `test/http/pins_test.py`).

## Workflow

CI runs the tests, linter, and type checker on every pull request and
before every deploy.
