# Limited multi-board pins

## Goal

Allow a Pin to have multiple Placements and replace the pin form's single-board dropdown with a board checkbox list.

This is intentionally narrower than the multi-board feature described in `cork-architecture.md`. Pins must continue to have at least one Placement, and deleting all of a Pin's Placements must also delete the Pin. Do not add unfiled pins, placement-specific actions, a pins index, board disclosure on pin details, or broader creator visibility.

## Placement lookup and visibility

Update `app/data.py`:

- Replace `find_sole_placement` with a helper that returns all Placements for a Pin and fails clearly when none exist.
- Update `find_accessible_pin` so access through any Placement's Board is sufficient.
- Preserve the current limited permission model: Pin creators do not gain board-independent access.
- Provide a deterministic way to choose one contextual Placement where existing screens still display a singular Board. Prefer the referring Board when applicable and otherwise use a stable fallback.

The schema already permits multiple Placement records for one Pin, so no model or store migration is required.

## Pin handlers

Update `app/http/pins.py`.

### Form validation

For create and update forms:

- Parse repeated `board_id` values as a required list of UUIDs.
- Deduplicate the selected IDs.
- Require at least one selected Board.
- Validate every selected Board as accessible before mutating the Store.
- Reject empty, unknown, or inaccessible selections without making partial changes.

### Creation

- Create one Pin after all input has been validated.
- Create one Placement per selected Board with the signed-in user as `adder_id`.
- Keep the Board from `/boards/{id}/pins/new` selected by default.
- Preserve the redirect to that originating Board.

### Update

- Load all existing Placements for the creator-owned Pin.
- Retain existing Placements for Boards that remain checked, preserving their IDs, timestamps, and adders.
- Create Placements for newly checked Boards.
- Delete Placements for unchecked Boards.
- Save the Pin's URL, title, and note only after the complete submission has been validated.
- Continue restricting edits to the Pin creator.

Because the form requires at least one Board, an update cannot leave a Pin without a Placement.

### Show, edit, return URLs, and deletion

- Adapt show and edit handlers to plural Placements while retaining one contextual Board for the existing page header.
- Allow a Board return URL when it identifies any Board containing the Pin.
- Prefer the referring Board as context; otherwise choose the stable fallback Placement.
- When explicitly deleting a Pin, delete all of its Placements before deleting the Pin.
- Preserve board-level deletion redirects by submitting a hidden return target from the Board page.

## Checkbox interface

Update:

- `app/views/pins/new.html`
- `app/views/pins/edit.html`
- `app/assets/styles/main.css`

Changes:

- Keep title, URL, and note under the **Details** frame header.
- Move Board selection after the note textarea.
- Add a separate frame header titled **Boards**.
- Render each accessible Board as a checkbox using repeated `name="board_id"` fields.
- On the new-Pin page, check the originating Board by default.
- On the edit page, check every Board on which the Pin has a Placement.
- Add narrowly scoped Board-checklist styles based on the existing sharing checklist without coupling the new controls to sharing-specific class names.
- Use server-side validation as the authoritative guarantee that at least one Board is selected.

Update `app/views/boards/show.html` to include the current Board as a hidden return target in each Pin deletion form. This does not add a visible action or change the distinction between removing a Placement and deleting a Pin.

## Board deletion

Update `app/http/boards.py`:

1. Collect and delete every Placement belonging to the Board.
2. For each affected Pin, delete it only when no Placements remain.
3. Continue deleting the Board's Shares, Orderings, and Board record.

This keeps multiply placed Pins when one Board is deleted while preserving the invariant that no Pin remains after its final Placement is removed.

## Remove obsolete migration artifacts

Delete:

- `bin/migrate_placement_backed_pins.py`
- `test/placement_migration_test.py`

No replacement migration is needed because the deployed Placement-backed schema already supports multiple records per Pin.

Do not update `.agents/notes/cork-overview.md`.

## Tests

Extend `test/pins_test.py` to verify observable behavior:

1. Creating a Pin with multiple checked Boards creates one Placement per Board.
2. The originating Board is checked on the new form.
3. Every current Placement is checked on the edit form and other accessible Boards are unchecked.
4. Updating a Pin adds and removes Placements without replacing retained Placements.
5. Empty, unknown, and inaccessible Board selections fail without partial mutation.
6. A user can open Pin details through any accessible Placement.
7. An unrelated user still receives not-found.
8. Explicit Pin deletion removes every Placement.
9. A stored Pin with no Placements fails clearly as invalid data.

Extend `test/boards_test.py` to verify:

1. Board show continues to render Pins through Placements.
2. Deleting one Board removes its Placement but retains a Pin that has another Placement.
3. Deleting a Board deletes a Pin when that Board held its final Placement.
4. Existing Share and Ordering deletion behavior remains intact.

Update existing single-Placement assertions where necessary to express the new one-or-more-Placement invariant.

## Deferred work

Do not add:

- Placement-specific routes or controls.
- Separate “Remove from this board” and “Delete pin” actions.
- An unfiled-Pin state or Pins index.
- A list of all Boards or viewers on Pin details.
- Board-independent access for a Pin's creator.
- Placement notes, ordering, comments, seen state, or soft deletion.
- A schema migration.

## Verification

Run:

- `mise run test`
- `mise run lint`
