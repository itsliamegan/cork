# Placement-backed pins

## Goal

Separate the relationship between a pin and a board into a `Placement` model,
laying the backend foundation for a later multi-board interface without changing
Cork's current user-visible behavior.

This is a data-model refactor rather than delivery of the complete multi-board
feature. The store will be able to represent several placements for one pin,
but the application will continue to create and manage exactly one placement
per pin until the add-to-board and remove-from-board interface is designed.

## Scope and decisions

- Replace `Pin.board_id` with a `Placement` record.
- Rename creator references as part of the same store migration:
  - `Board.user_id` becomes `Board.creator_id`.
  - `Pin.user_id` becomes `Pin.creator_id`.
  - A placement records its contributor as `Placement.adder_id`.
- Keep `Share.user_id` and `Ordering.user_id` unchanged. Those fields identify
  the user to whom the relationship or preference applies, not the record's
  creator.
- Creating a pin creates one placement on the selected board.
- The existing pin edit dropdown moves that one placement to the selected board.
- Do not add placement routes. There is no placement creation or removal action
  in this phase.
- Continue deleting a board's pins. The later user-facing multi-board release
  will change board deletion to remove only that board's placements and preserve
  the pins.
- Continue requiring a board on the new and edit forms. Unfiled pins and a pins
  index are out of scope.
- Preserve the existing board ownership behavior even though the field is named
  `creator_id`: only a board's creator can edit, share, or delete it.
- Preserve the existing pin ownership behavior: only a pin's creator can edit
  or delete it.
- Make no visible frontend changes. A few template expressions must change to
  consume the renamed fields and placement supplied by handlers, but the forms,
  controls, routes, labels, and rendered behavior remain the same.

## Data model

Update the model declarations and `schema` in `app/data.py`.

```text
Board
- title
- creator_id

Pin
- url
- title
- note
- creator_id

Placement
- pin_id
- board_id
- adder_id
```

`Placement` receives the standard model `id` and `created_at` fields from
Helios. Do not add `position`, soft deletion, or a placement-specific note in
this phase.

Although the schema permits several `Placement` records with the same `pin_id`,
current application operations must maintain exactly one. Add a shared helper
near the existing access helpers in `app/data.py` that finds a pin's sole
placement and fails clearly if the store contains zero or more than one. Use it
from pin show, edit, update, and delete rather than repeating unchecked
`find_by(...)[0]` calls.

The JSON store has no foreign keys or uniqueness constraints, so creation and
deletion code remains responsible for keeping pins and placements consistent.

## Creator checks and board access

The generic `find_owned` helper in `app/data.py` currently assumes every owned
model has `user_id`. Update or replace it so the Board and Pin authorization
paths compare `creator_id` instead. All callers in `app/http/boards.py` and
`app/http/pins.py` must use the revised helper.

`find_all_owned` also assumes `user_id` and currently has no callers. It may be
removed as part of this change or updated only if there is a concrete use for
it.

Update the board access helpers in `app/data.py`:

- `can_access_board` should compare `board.creator_id` to the signed-in user,
  while continuing to check `Share.user_id` for recipients.
- `find_all_accessible_boards` should likewise use `Board.creator_id` for the
  creator branch and leave share lookup unchanged.
- `find_accessible_board` otherwise remains unchanged.

Update the owned/private-board partition in `boards.index` and all board sharing
validation in `boards.edit` and `boards.update` to use `board.creator_id`.

## Pin visibility

Preserve the current visibility rule rather than introducing the broader rule
from `cork-architecture.md`.

`find_accessible_pin` in `app/data.py` currently follows `Pin.board_id` to an
accessible board. Change it to:

1. Load the pin.
2. Find its sole placement through the shared placement helper.
3. Verify access to `placement.board_id` through `find_accessible_board`.
4. Return not-found when the board is inaccessible, as it does today.

This placement lookup is necessary for the existing direct `/pins/{id}` route;
once `Pin.board_id` is removed, the placement is the only source of its board
and therefore of shared visibility.

Do not make creator access independent of board access in this phase. Under the
exactly-one-placement invariant this preserves existing behavior.

## Pin handlers

Update `app/http/pins.py` while preserving all existing routes and forms.

### `pins.create`

After validating the selected board:

1. Create the `Pin` with `creator_id=auth.user.id` and no board field.
2. Create its `Placement` with the new pin ID, selected board ID, and
   `adder_id=auth.user.id`.
3. Keep the existing redirect to the selected board.

Complete all form and board validation before creating either record.

### `pins.show`

- Continue loading through `find_accessible_pin`.
- Find the pin's sole placement and load its board from `placement.board_id`.
- Load attribution from `pin.creator_id` instead of `pin.user_id`.
- Continue passing the same visible board and creator context to
  `pins.show.html`.

### `pins.edit`

- Continue restricting the handler to the pin creator.
- Find the sole placement and use it to load the current board.
- Pass the placement to `pins.edit.html` so the existing dropdown can select
  `placement.board_id`.
- Update `_pin_return_url` to validate a board return path against the current
  placement rather than `pin.board_id`.

### `pins.update`

- Load the creator-owned pin and its sole placement.
- Validate the selected accessible board as it does today.
- Update URL, title, and note on the pin.
- Move the placement by assigning the selected board ID to
  `placement.board_id`.
- Save both changed records and preserve the current redirect behavior.

No placement ID is needed in the submitted form while the application enforces
one placement per pin.

### `pins.delete`

- Derive the return board from the sole placement.
- Delete the placement and then the pin.
- Preserve the existing redirect to the board.

## Board handlers

Update `app/http/boards.py`.

### `boards.create`, `boards.index`, `boards.edit`, and `boards.update`

Replace Board creator reads and writes with `creator_id`. Leave all `Share`
records and submitted `user_id` fields unchanged.

### `boards.show`

Replace `store.find_by(Pin, board_id=board.id)` with a placement join:

1. Load placements whose `board_id` matches the board.
2. Load each referenced pin.
3. Pass the resulting pin list to the existing template.

The template currently sorts by each pin's `created_at`. Keep that behavior for
this phase; placement ordering and manual pin ordering are separate work.

### `boards.delete`

Preserve current behavior:

1. Load the board's placements.
2. Delete every referenced pin and its placement.
3. Delete the board's shares and orderings as today.
4. Delete the board.

Because current application behavior guarantees one placement per pin, this is
equivalent to the existing board cascade. The future release that starts
creating multiple placements must revise this handler in the same release;
deleting a multiply placed pin globally would otherwise be unsafe.

## Template compatibility

No new page or control is required, but direct field references must follow the
new model names:

- `app/views/boards/index.html`: use `board.creator_id` for the creator-only
  action check.
- `app/views/boards/show.html`: use `board.creator_id` and `pin.creator_id` for
  action visibility.
- `app/views/pins/show.html`: use `pin.creator_id` for the Edit action.
- `app/views/pins/edit.html`: select the current dropdown option using
  `placement.board_id` instead of `pin.board_id`.

These are data-binding changes only. Do not alter the rendered structure,
wording, styling, or client-side behavior.

## Store migration

A one-off migration is required. Helios decodes model attributes strictly, so
neither version of the application can load the other version's Board and Pin
representation. Deployment must therefore treat the code change and data
migration as one coordinated operation.

### Transformation requirements

The migration must produce a store accepted by the new schema while preserving
all existing model IDs, timestamps, content, sharing relationships, and personal
board orderings.

- Every Board creator reference must move from `user_id` to `creator_id`.
- Every Pin creator reference must move from `user_id` to `creator_id`.
- Every legacy pin-board relationship must become exactly one Placement that
  refers to the same pin, board, and pin creator as its adder.
- Migrated Pins must no longer contain `board_id`.
- New Placement records must have unique model IDs and valid aware creation
  timestamps. Using the corresponding pin timestamp preserves the historical
  meaning better than recording migration time.
- `Share.user_id`, `Ordering.user_id`, and every unrelated model and attribute
  must remain unchanged.
- Record ordering in the JSON array is not semantically significant, but the
  migration should produce deterministic output apart from generated placement
  IDs.

### Input validation

The complete input must be validated before the destination file is changed.
The migration must reject with a useful error when:

- the top-level JSON value or a model record has an unexpected shape;
- a Board or Pin is missing an ID, creator, or required discriminator;
- a legacy Pin has a null or missing `board_id`;
- a Pin refers to a board or creator that does not exist;
- IDs are duplicated;
- creator fields use both old and new names;
- Placement records are already present alongside legacy `Pin.board_id` fields;
- the store is otherwise a mixture of source and destination formats.

Null-board pins should be reported by ID so they can be assigned or removed
manually before deployment. The script must not silently drop them, invent a
board, or leave them without a placement.

Define explicit behavior for a fully migrated input. Prefer recognizing it and
reporting that no migration is necessary over attempting to migrate it again.
This makes an accidental second invocation safe while still rejecting ambiguous
mixed data.

### File-safety and operational requirements

- Accept an explicit store path so production and copied data can be targeted
  deliberately; any default must match Cork's existing command-line script
  conventions.
- Read and transform the raw JSON without importing `app.data` or decoding it
  through either Cork schema.
- Perform all parsing, validation, and serialization before replacing the
  source file.
- Write to a temporary file in the same directory and publish it with
  `os.replace`, preserving the original file mode.
- Remove temporary files after a failed write and return a non-zero exit status
  for every validation or persistence failure.
- Print a concise summary containing the path and counts of migrated Boards,
  Pins, and created Placements, without printing private pin contents.
- Do not create its own backup as an undocumented side effect. Deployment must
  take and verify the normal store backup immediately before migration.
- Run while Cork is stopped. Although the application persistence lock protects
  normal requests, stopping the service makes the incompatible-schema cutover
  explicit and prevents an old worker from overwriting migrated data.

### Verification and rollback requirements

Test the migration against temporary copies rather than the live development
store. Coverage should establish that:

- representative old-format data becomes loadable with the new `schema`;
- all original IDs and user-visible values survive unchanged;
- each Pin has exactly one correctly linked Placement;
- Share and Ordering records survive byte-for-byte at the value level;
- invalid, null-board, mixed, and duplicate-ID inputs fail without changing the
  source file;
- a fully migrated input is handled safely;
- output remains valid JSON and retains the source file's permissions.

The deployment runbook should record the pre-migration backup and the commands
used to validate the migrated store before restarting Cork. Rollback means
restoring that backup and the previous application revision together; reverting
only the code or only the data will leave an unreadable schema mismatch.

## Tests

Update existing fixtures and assertions throughout `test/`:

- Construct Boards with `creator_id`.
- Construct Pins with `creator_id` and a corresponding Placement.
- Assert creator fields under their new names.
- Keep `Share.user_id` and `Ordering.user_id` expectations unchanged.

Extend `test/pins_test.py` to verify observable behavior:

1. Pin creation stores one Pin and one Placement with the selected board and
   signed-in user as adder.
2. Updating the board dropdown changes `Placement.board_id` and does not replace
   the Pin.
3. A shared-board recipient can still open pin details through placement-derived
   visibility.
4. An unrelated user still receives not-found for a direct pin URL.
5. Deleting a pin removes its placement.

Extend `test/boards_test.py` to verify:

1. Board creation records `creator_id`.
2. Board show renders pins joined through placements.
3. Existing creator-only board operations remain restricted.
4. Deleting a board removes its placements and pins, as well as its shares and
   orderings.

Add focused migration coverage using a temporary JSON file. Assert field
renames, placement contents, preservation of unrelated rows, rejection of a
null-board pin, and safe handling of already-migrated or mixed input.

Run `mise run test` and `mise run lint` after implementation.

## Deferred work

The following belongs to the later user-facing multi-board release:

- Routes for creating and removing placements.
- Add-to-board and remove-from-board controls.
- More than one placement per pin in normal application operation.
- Placement-specific route or form context.
- A pins index and unfiled pins.
- Showing all boards and viewers associated with a pin.
- Changing board deletion to preserve pins and remove only placements.
- Separate remove-placement and delete-pin actions.
- Manual placement ordering, comments, seen state, soft deletion, memberships,
  URL normalization, and changes to board ownership.
