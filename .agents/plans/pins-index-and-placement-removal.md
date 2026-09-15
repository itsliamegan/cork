# Pins index and placement removal

## Goal

Give every Pin a canonical home independent of its Board Placements, then make
Board-level removal and Pin-level deletion distinct operations.

The resulting interface has one destructive verb for each resource context:

- A Pin row on `boards.show` represents a Placement and offers **Remove from
  this board**.
- A Pin row on `pins.index` represents the Pin and offers **Delete pin**.
- `boards.edit` offers **Delete board**.
- `pins.edit` offers **Delete pin**.

Removing a Placement must never delete its Pin. Removing the final Placement
leaves an unfiled Pin on the Pins index. Deleting a Board removes its Placements
but never its Pins. Deleting a Pin removes it and all of its Placements.

## Product decisions

### Canonical Pin collection

- Add a signed-in user's **Pins** index at `GET /pins/`.
- The index contains every Pin created by the current user, including Pins with
  no Placements.
- Do not include Pins merely because they are visible through a shared Board.
  Those remain discoverable through that Board.
- Add **Pins** to the persistent navigation and use the existing active-nav
  treatment. Keep the application root redirecting to Boards unless separately
  reconsidered.
- Add a **New pin** action to the Pins index.
- Keep **New pin** on `boards.show`; that entry point preselects the current
  Board, while the index entry point starts with no selected Boards.

### Client-side Pin filtering and scale

The Pins index must remain usable when a user owns hundreds of Pins.

- Render every owned Pin on the initial `GET /pins/` response. Do not require a
  query before showing the collection.
- Add a client-side search field above the list and filter immediately on each
  input event without navigation or form submission.
- Match the trimmed query case-insensitively against each Pin's title, complete
  URL, and note. Do not match Board titles, sharing labels, creator names, or
  presentation-only state copy.
- Reuse the existing generic `filter` Stimulus controller and provide each Pin
  row's combined searchable text through `data-filter-text`. Keep the Board
  picker title-only by continuing to give its rows title-only filter text.
- Filtering changes only each row's `hidden` property. It must not remove,
  reorder, clone, or mutate Pin actions or Turbo Frames.
- Show a dedicated `No pins match this search.` state when a non-empty query
  matches nothing. Keep the collection's `No pins yet.` state distinct.
- Give the search input an accessible name, `type="search"`, a concise
  `Search pins` placeholder, and no `name`; filtering is entirely client-side
  and does not introduce a `q` URL parameter.
- Without JavaScript, all owned Pins remain rendered and usable. Search is a
  progressive enhancement; do not make access to any Pin depend on filtering.
- Do not paginate the Pins index initially. Cork loads the complete JSON store
  for every request, and hundreds of text-only Pin rows do not justify page
  state, pagination links, or search/pagination coordination merely to reduce
  response and DOM size.
- Reconsider pagination only after measuring an actual response-size, rendering,
  or navigation problem. If introduced later, search must move server-side so
  it operates over the complete collection rather than one page.

### Resource semantics

Use these invariants throughout handlers, templates, confirmation copy, and
tests:

1. A Pin may have zero or more Placements.
2. A Placement always belongs to exactly one Pin and one Board.
3. Removing a Placement never removes the Pin.
4. Deleting a Board removes all of that Board's Placements, Shares, Orderings,
   and the Board, but no Pins.
5. Deleting a Pin is creator-only and removes all Placements before removing the
   Pin.
6. A Pin creator can access their Pin even when it is unfiled or all of its
   Placements are on inaccessible Boards.
7. A non-creator can access a Pin only through at least one Placement on a Board
   they can access.

### Placement removal permission

A user may remove a Placement when they can access its Board and they are any
of:

- the Pin creator;
- the Placement adder;
- the Board creator.

Treat failed access and failed role checks as not-found, consistent with the
rest of Cork. Do not let an arbitrary participant remove another person's
Placement solely because the Board is shared with them.

A Pin creator who has lost access to a containing Board retains global Pin
deletion through `pins.index` or `pins.edit`, but the inaccessible Placement is
not silently removed by an ordinary edit.

### Wording

Keep the verbs resource-specific:

- **Remove from this board** in a Board Pin row, with confirmation text naming
  the Board and stating that the Pin will remain in Pins and on any other
  Boards.
- **Delete pin** in Pin-owned contexts, with confirmation text stating that the
  Pin will be deleted from Pins and every Board.
- **Delete board** on `boards.edit`, with confirmation text stating that its
  Pins will remain in Pins and on any other Boards.

Never make **Remove from this board** conditionally turn into **Delete pin** for
a final Placement.

## Data helpers and access

Update `app/data.py`.

### Placement lookup

- Change `find_pin_placements` to return zero or more Placements without raising
  when the result is empty.
- Remove the invalid-data invariant and its test that every Pin must have at
  least one Placement.
- Adapt `find_contextual_placement` to return `Placement | None` when given an
  empty list, or only call it after an explicit non-empty check. Prefer making
  optionality explicit so unfiled Pin pages cannot fail accidentally.
- Add a clearly named placement-removal authorization helper if it avoids
  repeating the three-role rule. The helper should load or receive the Pin,
  Placement, and Board needed to evaluate the rule and should not broaden Board
  visibility.

### Pin visibility

Update `find_accessible_pin`:

1. Load the Pin.
2. Return it immediately when the signed-in user is its creator.
3. Otherwise, return it when any Placement belongs to an accessible Board.
4. Raise not-found when neither condition applies.

Keep Board-title disclosure separate from Pin access. A creator may own and open
a Pin without being allowed to see every Board on which it appears.

### Index lookup

Add a helper only if useful for consistency; otherwise query
`store.find_by(Pin, creator_id=current_user.id)` directly in `pins.index`.
Load and return the complete owned collection; do not accept search or pagination
parameters in the handler. Order Pins newest first using `created_at`, matching
Board Pin lists. Keep this as presentation ordering rather than adding a stored
Pin ordering model.

## Routes and handlers

### Route table

Update `app/http/__init__.py`:

- Add `GET /pins/` for `pins.index`.
- Add `GET /pins/new` for a canonical unfiled-capable new-Pin form.
- Retain `GET /boards/{id}/pins/new` as the Board-context entry point.
- Add `DELETE /placements/{id}` in a small
  `app/http/placements.py` handler module.

Use the Placement ID rather than a Pin/Board pair for removal because the action
mutates a Placement resource. `boards.show` must therefore retain each
Placement in its row presentation data.

### `pins.index`

Implement an owned-Pin index that:

- loads and renders all Pins created by the signed-in user;
- does not load Pins merely visible through shared Boards;
- does not perform server-side search or pagination;
- loads their Placements in one pass and groups them by Pin ID;
- loads only Boards accessible to the viewer for Board chips;
- distinguishes a genuinely unfiled Pin from one that has Placements whose
  Boards are no longer accessible;
- renders title, compact external URL, creation date, accessible Board chips,
  and an explicit unfiled state;
- renders a client-side search control and wires every row to the existing
  `filter` controller using title, complete URL, and note as its search text;
- provides View/Edit navigation and a creator-only **Delete pin** action;
- submits `return_to=/pins/` from each delete form.

Do not reveal inaccessible Board titles. When an owned Pin has inaccessible
Placements, show neutral copy such as `Also on 1 unavailable board` if needed to
avoid incorrectly calling it unfiled.

### New Pin

Adapt the existing `pins.new` handler and template to support two entry points:

- `/pins/new`: no originating Board, no checkbox selected, Cancel and
  `return_to` point to `/pins/`.
- `/boards/{id}/pins/new`: validate the Board, preselect it, and preserve the
  current Board Cancel and return behavior.

A small shared rendering helper or separate thin handlers may be used; avoid
making templates infer context from malformed values.

Update `pins.create`:

- Parse `board_id` as an optional repeated UUID list.
- Deduplicate selections.
- Validate every selected Board before creating anything.
- Create the Pin even when no Boards are selected.
- Create one Placement per selected Board with the signed-in user as adder.
- Accept `/pins/` as a safe return target.
- Accept an originating Board return target only when that Board was selected
  and remains accessible.
- Fall back to `/pins/` rather than indexing into the selected Board list.

### Edit Pin

Keep `pins.edit` creator-only. Present the Board checklist as a bulk
**Appears on** editor and allow every visible checkbox to be unchecked.

Partition existing Placements into:

- Placements on Boards currently accessible to the Pin creator, which the
  checklist may add or remove.
- Placements on inaccessible Boards, which the form must preserve.

Update `pins.update` to reconcile only accessible Placements:

1. Parse an optional repeated `board_id` list.
2. Deduplicate and validate every submitted Board as accessible before mutation.
3. Retain inaccessible existing Placements regardless of omitted checkbox
   values.
4. Retain checked accessible Placements without replacing their IDs, timestamps,
   or adders.
5. Delete unchecked accessible Placements.
6. Create Placements for newly checked Boards with the editor as adder.
7. Save Pin fields after complete validation.

Allow the resulting Pin to have no Placements. Add explanatory text when
inaccessible Placements are being retained, without disclosing their Board
names.

Add a separate **Delete pin** section and confirmation to `pins.edit`. Do not
nest its delete form inside the update form; use a separately identified form
and a button with the HTML `form` attribute, or place the delete form after the
edit form.

### Pin details

Adapt `pins.show` and both standalone/inline details presentations for unfiled
Pins:

- Contextual Placement and adder are optional.
- Render **Added by** only when a contextual accessible Placement exists.
- Render accessible Board chips as today.
- Show `Not on any boards` only when the Pin truly has no Placements.
- If an owned Pin has only inaccessible Placements, use neutral unavailable
  copy rather than claiming it is unfiled or disclosing Board titles.
- Keep Edit creator-only.
- Ensure direct access by an unfiled Pin's creator succeeds and non-creators
  cannot open it.

Do not add Placement removal buttons to the Pin details panel in this phase;
Board context is the unambiguous removal surface.

### `placements.delete`

Implement deletion in `app/http/placements.py`:

1. Load the Placement, referenced Pin, and referenced Board.
2. Verify the current user can access the Board.
3. Authorize when the user is the Pin creator, Placement adder, or Board
   creator.
4. Delete only the Placement.
5. Redirect to the containing Board.

The operation behaves identically for the final Placement: the Pin survives and
appears as unfiled on its creator's Pins index. Do not accept a caller-provided
redirect target when the containing Board is already known from the Placement.

### Pin deletion

Keep `DELETE /pins/{id}` creator-only and delete every Placement before the Pin.
Change return handling so:

- `/pins/` is accepted and is the default;
- `/pins/{id}` and `/pins/{id}/edit` are not used as post-delete destinations;
- a Board return is accepted only when it is accessible and contained the Pin
  before deletion;
- malformed, stale, or inaccessible return targets fall back to `/pins/`.

Remove the global Pin-delete action and dialog from `boards.show`; that page now
removes the row's Placement instead.

### Board show

Update `boards.show` to build one row per Placement containing both the
Placement and Pin. Keep newest-first Pin ordering and the current compact URL
presentation.

For each row:

- retain the normal external title link and Details interaction;
- show **Edit pin** only to the Pin creator, where appropriate;
- show **Remove from this board** only when the current user satisfies the
  three-role removal rule;
- submit the Placement ID to `DELETE /placements/{id}`;
- use a removal confirmation that makes Pin survival explicit;
- do not expose **Delete pin** from the Board row.

Several Placements for the same Pin on one Board should not normally exist.
Continue rendering stored rows deterministically rather than adding unrelated
schema work, and ensure normal create/update paths do not create duplicates.

### Board deletion and edit

Update `boards.delete`:

1. Load the creator-owned Board.
2. Delete all Placements on the Board.
3. Delete its Shares and Orderings.
4. Delete the Board.
5. Never inspect remaining Pin Placements and never delete a Pin.

Move the **Delete board** action from `boards.index` to `boards.edit` so global
resource deletion lives on the resource's edit page. Keep Edit and Sharing
navigation on owned Board rows. Add a separate delete form/dialog outside the
Board update form and update the confirmation copy to state that Pins survive.

## Templates and navigation

Add `app/views/pins/index.html` and update:

- `app/views/layouts/app.html` for the Pins navigation item;
- `app/views/boards/show.html` for Placement rows and removal;
- `app/views/boards/index.html` to remove Board deletion;
- `app/views/boards/edit.html` to add Board deletion;
- `app/views/pins/new.html` for optional origin and zero selections;
- `app/views/pins/edit.html` for **Appears on**, zero selections, retained
  unavailable Placement copy, and Pin deletion;
- `app/views/pins/show.html` and `app/views/pins/_details.html` for optional
  Placement context and unfiled state.

Extract narrowly scoped confirmation or Pin-row partials only if duplication
becomes difficult to keep consistent. Do not introduce a generic component
system solely for these screens.

Reuse existing frame, menu, dialog, button, Pin row, Board-chip, and filter
styles. Add only narrowly scoped styles needed by the Pins index search row,
no-match and unfiled states, and edit-page destructive sections. Preserve
light/dark theme tokens and narrow layout behavior. Ensure `[hidden]` Pin rows
do not participate in layout.

## Persistence and migration

No stored-data migration is required. The existing schema already permits Pins
without Placements, and all currently valid Pins and Placements remain valid.
This release changes application invariants and deletion behavior rather than
record shape.

Before deployment, take the normal store backup. Pins deleted by the old
Board-deletion or Pin-deletion behavior cannot be reconstructed by this change.

Update `.agents/notes/cork-overview.md` so it no longer describes a single
Board assignment, mandatory Placement, or Board deletion cascading into Pins.
Record the owned-only Pins index, its client-side title/URL/note filtering and
unfiled state, the absence of initial pagination, the new access rule, and the
three-role Placement removal permission. Update other current-state notes only
where they would
otherwise contradict shipped behavior; do not rewrite historical design
analysis as though it were current documentation.

## Tests

### Pin index and visibility

Extend `test/pins_test.py` to verify:

1. The Pins navigation item and `GET /pins/` are available to signed-in users.
2. The index contains all Pins created by the viewer, including unfiled Pins.
3. It excludes Pins merely visible through someone else's shared Board.
4. Owned Pins remain directly accessible with zero Placements or only
   inaccessible Placements.
5. Non-creators cannot access an unfiled Pin.
6. Accessible Board chips render without leaking inaccessible Board titles.
7. The initial response renders every owned Pin without requiring a query and
   does not render pagination controls.
8. The search input has an accessible name and the expected `filter` controller,
   targets, action, and title/URL/note search text for every row.
9. The no-match state is initially hidden and differs from the empty collection
   state.
10. Delete forms return to `/pins/` and deleting a Pin removes all Placements.

### Optional Board selection

Verify:

1. `/pins/new` renders no checked Board and returns/cancels to `/pins/`.
2. Board-context new Pin still preselects and returns to its Board.
3. Creating with no `board_id` creates an unfiled Pin.
4. Creating with several Boards still creates one Placement per unique Board.
5. Unknown and inaccessible selections fail without creating a Pin or
   Placement.
6. Editing can remove every accessible Placement and leave the Pin intact.
7. Editing preserves inaccessible Placements while reconciling accessible ones.
8. Retained Placements preserve their IDs, timestamps, and adders.

### Placement removal

Add focused tests for `DELETE /placements/{id}`:

1. The Pin creator can remove the Placement.
2. The Placement adder can remove it.
3. The Board creator can remove it.
4. An unrelated shared participant receives not-found.
5. A user without Board access receives not-found even if they were formerly
   the adder.
6. Removal deletes only the selected Placement.
7. Removing the final Placement retains an unfiled Pin.
8. The response redirects to the containing Board.
9. Board rows show or hide the removal action according to the same permission
   rule used by the handler.

### Board deletion

Extend `test/boards_test.py` to verify:

1. `boards.show` renders one row per Placement and submits its Placement ID.
2. No global **Delete pin** action appears in a Board row.
3. Deleting a Board removes all its Placements, Shares, and Orderings.
4. Every affected Pin survives, including Pins whose final Placement was on the
   deleted Board.
5. The Board index no longer renders deletion controls.
6. The owned Board edit page renders a functioning **Delete board** control and
   accurate survival copy.

### Unfiled details and regressions

Verify:

- standalone and inline Pin details render without a contextual Placement;
- contextual adder attribution still follows an accessible referring Board;
- unavailable Placements are not mislabeled as unfiled;
- Board-picker filtering preserves optional checkbox state;
- existing shared-Board viewing, Pin creation, Board ordering, safe redirects,
  and open-in-new-tab behavior remain intact.

Test observable output, mutations, authorization failures, and redirects rather
than private helper call order.

## Implementation sequence

1. Relax Placement lookup and update Pin visibility for creator-owned unfiled
   Pins.
2. Add the complete owned Pins index, client-side filtering, navigation,
   canonical new-Pin route, and optional Board selection.
3. Make Pin edit reconciliation zero-safe and preserve inaccessible Placements.
4. Add Placement deletion with the three-role authorization rule and switch
   Board rows from global deletion to contextual removal.
5. Change Board deletion to preserve every Pin and move its delete control to
   `boards.edit`.
6. Move Pin deletion to the Pins index and `pins.edit`, then harden return
   handling and confirmation copy.
7. Adapt standalone and inline details to optional Placement context.
8. Update current-state documentation and complete manual interaction review.

Keep each step behaviorally complete: do not expose final-Placement removal
until the Pins index exists and Pins with zero Placements can be opened.

## Verification

Run:

- `mise run test`
- `mise run lint`

Using the already-running development server, manually verify desktop and narrow
layouts in light and dark modes:

1. Create an unfiled Pin from Pins and find it again.
2. Create a Pin from a Board and confirm that Board is preselected.
3. Remove a multi-placed Pin from one Board and confirm it remains elsewhere.
4. Remove a final Placement and confirm the Pin moves cleanly to the unfiled
   state.
5. Exercise removal as Pin creator, Placement adder, and Board creator, and
   verify an unrelated participant has no action.
6. Delete a Board and confirm all affected Pins survive.
7. Delete a Pin from both Pins index and Pin edit and confirm it disappears from
   every Board.
8. Confirm every dialog clearly distinguishes Remove, Delete pin, and Delete
   board.
9. Confirm inaccessible Board names never appear in the Pins index, Pin details,
   or edit form.
10. With hundreds of Pins, confirm index load and scrolling remain comfortable,
    title/URL/note searches filter immediately, clearing search restores every
    row, and no-match and empty states are distinct.
11. Disable JavaScript and confirm every owned Pin remains visible and usable.
