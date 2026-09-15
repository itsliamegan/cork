# Searchable pin board picker

## Goal

Bring the board-selection section on the new- and edit-pin forms in line with
`sketch/107-new-pin-searchable-boards.html` and
`sketch/108-edit-pin-searchable-boards.html` while preserving Cork's current
multi-board behavior and optional Note field.

The result should show an available-board count, a compact search input, a
scrollable checkbox list, each board's sharing context, and an empty search
state. Searching is client-side only; submitted checkbox values and server-side
validation remain authoritative.

## Product decisions

- Apply the picker to both `app/views/pins/new.html` and
  `app/views/pins/edit.html` so the two pin workflows use the same interaction.
- Keep the existing Details fields, including Note, and keep the current page
  context, cancel destinations, submit actions, checked-board behavior, and
  return URL behavior.
- Keep `app/views/pins/show.html` unchanged. The reference sketches depict the
  new and edit forms, not the read-only pin details page; verify it only as a
  regression surface.
- Show `N available` in the Boards frame header, where `N` is the complete
  accessible-board count and does not change as the list is filtered.
- Remove the selected-board chips entirely. Checked rows are the sole visual
  representation of the selection.
- Remove the picker footer, including both `2 boards selected` and `Visible to
  Nadia and Theo`.
- Do not render the visible `Find a board` label. Use `placeholder="Search"` and
  retain an accessible name such as `aria-label="Search boards"` so removing
  the copy does not remove the control's label.
- Keep sharing context in every checkbox row:
  - `Private` for a board with no Share records.
  - `Shared · Nadia, Theo` for a shared board, with names sorted
    case-insensitively.
  - Names should identify everyone other than the signed-in user who can access
    the board: the owner when it is someone else, plus Share recipients other
    than the current user. This keeps the row useful for both owned boards and
    boards shared with the current user without restoring the removed aggregate
    visibility message.
- Search only board titles, case-insensitively, after trimming the query. Do not
  search `Private`, `Shared`, or people's names.
- Preserve checkbox state while filtering. A checked board may be hidden by a
  query but must remain checked and must still be submitted.
- Show `No boards match this search.` when no rows match. Clearing the query
  restores all boards.
- Do not add server-side search, URL query parameters, selection limits, board
  reordering, or a new pin validation path.

## Server-rendered picker data

Update `app/http/pins.py` to build presentation data for each accessible board.

1. Add a clearly named helper such as `build_board_options` rather than putting
   Share/User joins in each handler.
2. Load the accessible boards once, all relevant Share records once, and the
   users needed for labels once. Group shares by board and map user IDs to names
   in memory.
3. For each accessible board, return its Board plus a ready-to-render sharing
   label following the rules above. Keep the Board objects themselves available
   so templates can still compare IDs for checked state.
4. Use the same option list in `pins.new` and `pins.edit`; pass it under one
   consistent context name such as `board_options`.
5. Derive the available count from that list in the template rather than
   issuing another store read.
6. Do not alter `create` or `update`: repeated `board_id` inputs, deduplication,
   accessibility checks, the at-least-one-board rule, Placement reconciliation,
   and redirects continue to work as they do now.

This join belongs in the pin-page presentation path for now. Do not change the
shape or ordering contract of `find_all_accessible_boards`, since it is also
used by the boards index and ordering endpoint.

## Templates

Update both pin form templates with equivalent board-picker markup.

### `app/views/pins/new.html`

- Add the available count as `.frame-meta` in the Boards header.
- Replace the current plain `board-checklist` fieldset with a picker container
  carrying `data-controller="filter"`.
- Render a search row immediately under the header. The search input should:
  - be `type="search"`;
  - have `placeholder="Search"`;
  - have no `name`, so it is never submitted;
  - use `autocomplete="off"`;
  - be the filter query target;
  - invoke filtering on `input`.
- Render the complete board option list below it. Each label remains the click
  target for a repeated `name="board_id"` checkbox and includes:
  - a filter item target and title-only filter text;
  - the board title;
  - the server-rendered `Private` or `Shared · …` state.
- Keep only the originating board checked by default.
- Add a hidden-by-default no-results element after the options.
- Keep the form actions directly after the board list; do not add chips or a
  status row.

### `app/views/pins/edit.html`

Apply the same structure and data attributes as the new form, while preserving
all existing Placement IDs in `placed_board_ids` as checked. Do not seed the
search field with a value; the populated query in sketch 108 demonstrates the
filtered state, not a default edit-page query.

If the duplicated markup becomes difficult to keep identical, extract only the
board picker to a narrowly scoped Jinja partial or macro. Keep new/edit-specific
checked-state expressions explicit rather than introducing a broad form
component abstraction.

## Stimulus filtering

Create `app/assets/scripts/controllers/filter_controller.js` as a small generic
filter controller and register it as `filter` in
`app/assets/scripts/main.js`.

- Define query, item, and empty-state targets.
- On connect and on each input event:
  1. trim and locale-lowercase the query;
  2. locale-lowercase each item's title-only filter text;
  3. set each item's `hidden` property according to substring matching;
  4. hide the empty state when at least one item is visible and reveal it when
     none are visible.
- Change only visibility. Do not modify, reorder, clone, or uncheck inputs and
  do not generate selection chips/counts.
- Let Stimulus lifecycle handle Turbo page visits; do not install document-level
  listeners.
- Keep the server-rendered default usable without JavaScript: all boards remain
  visible and the no-results message remains hidden.

## CSS and theme

Replace the pin-only checklist styling in `app/assets/styles/main.css` with
narrowly scoped picker styles, while leaving the sharing checklist behavior
intact.

1. Add styles for the search row/input, bounded options region, option row,
   board title, board state, and no-results message.
2. Match the sketches' structure:
   - search row separated by a quiet rule;
   - full-width search control;
   - options constrained to roughly `15rem` with vertical scrolling and
     `overscroll-behavior: contain`;
   - checkbox/title/state laid out as three columns;
   - compact rows with normal inter-row dividers;
   - state text right-aligned and muted;
   - hover surface for pointer feedback;
   - a selected surface on rows containing a checked checkbox.
3. Add a semantic selected-surface color to `app/assets/styles/theme.css`, using
   the sketch's light and dark blue-soft treatments (`#e6f1fb` and `#173c5a`)
   rather than embedding mode-specific colors in the component CSS.
4. Continue using the existing action color for checkbox accents and the
   existing focus treatment for the search input and checkboxes.
5. Ensure `[hidden]` option rows do not participate in layout. The no-results
   element should use the `hidden` attribute rather than inline styles.
6. At the existing `28rem` container breakpoint, retain the three-column option
   row but constrain the state width so long names wrap without forcing the
   board title or checkbox outside the frame. Allow a slightly taller scroll
   region if needed, as in the sketches.
7. Remove obsolete `.board-checklist*` declarations after both pin forms have
   moved to the new classes. Split the currently grouped
   `.board-checklist`/`.sharing-items` rules so deleting pin checklist styles
   does not change board-sharing forms.
8. Do not globally widen `--page-width` merely because the standalone sketches
   use `40rem`; retain Cork's existing page measure unless manual comparison
   shows the picker cannot fit at normal widths.

## Tests

Extend `test/pins_test.py` around rendered, user-visible contracts.

1. Update the existing new/edit checked-board assertions only as required by
   the new markup, preserving coverage that the originating/current Placement
   boards are checked.
2. Verify both forms render:
   - the correct available count;
   - the Search placeholder and accessible label;
   - Stimulus controller/target/action wiring;
   - every accessible board as a repeated `board_id` checkbox;
   - no selected-chip or picker-status copy.
3. Create owned private/shared boards and a board owned by another user but
   shared with the current user; verify `Private` and deterministic
   `Shared · …` labels include the correct other viewers.
4. Verify inaccessible boards and unrelated user names do not leak into the
   picker markup.
5. Keep the existing POST tests as regression coverage that hidden-by-filter
   checked inputs would still be accepted and that zero selected boards is
   rejected server-side.

There is no JavaScript unit-test harness in this project. Test the server-rendered
contract in Python and cover the controller's browser behavior during manual
verification rather than adding a new JS test stack solely for this controller.

## Verification

Run:

- `mise run test`
- `mise run lint`

Using the already-running development server, verify both new and edit forms in
light and dark color schemes and at desktop and narrow widths:

1. The initial list contains all accessible boards and the edit form retains all
   current checks.
2. Partial and mixed-case title searches filter immediately.
3. A no-match query shows the empty state; clearing it restores the rows.
4. Filtering never changes checked state, including for checked rows hidden by
   the query.
5. Clicking anywhere in a row toggles its checkbox and gives the selected-row
   treatment.
6. Long board titles and several viewer names wrap without horizontal overflow.
7. Keyboard focus remains visible, search has an accessible name, and the
   scrollable list is usable without a pointer.
8. Save and Cancel retain their existing destinations on both forms.
9. The pin details (`pins.show`) and board sharing screens have no visual or
   behavioral regressions from the picker CSS refactor.
