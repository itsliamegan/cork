# Reorderable boards

## Goal

Let each signed-in user arrange the boards visible on `/boards/` with native HTML
Drag and Drop. Ordering is a personal view preference: rearranging a board must
not change another user's board index, including when the board is shared.

Use `designs/56-board-reordering.html` as a rough visual starting point rather
than a final specification. Preserve the existing Private boards and Shared
boards grouping; a board may move within its current group, but not between
groups because group membership is determined by sharing state.

## Lessons from the Fizzy reference

Adopt the useful shape of Fizzy's implementation:

- use native `draggable` and `DataTransfer` rather than implementing pointer
  tracking;
- add the dragged styling on the next animation frame so the browser captures a
  clean drag image;
- update the DOM immediately, persist asynchronously, and always clean up drag
  state;
- keep behavior in a small Stimulus controller and let the template provide IDs
  and the persistence URL.

Do not copy Fizzy's controller literally. Fizzy primarily moves items between
containers and ignores drops in the source container, while Cork needs to sort
items within a list. Cork also does not need counters, container CSS-variable
swapping, Turbo Stream responses, frame reloads, or the optional audio behavior.
Use a portable string in `DataTransfer` rather than passing a DOM element.

## Data model and ordering rules

1. Add a generic `Int` codec to `../helios/src/helios/store/types.py`, parallel
   to the existing `Str`, `Bool`, and `UUID` codecs, and cover integer JSON
   encoding/decoding in `../helios/test/store_test.py`. An ordering position is
   intrinsically numeric; do not encode it as a string merely to avoid extending
   the small store type set.
2. Add an `Ordering` model in `app/data.py` with three required attributes:
   - `user_id: UUID` — the viewer whose preference this is;
   - `board_id: UUID` — the accessible board being positioned;
   - `position: Int` — its zero-based position in that viewer's board index.
3. Register `Ordering` in Cork's schema. Existing JSON needs no migration because
   the absence of ordering records means the user has not customized the list.
4. Treat `(user_id, board_id)` as the model's logical unique key even though the
   JSON store cannot enforce composite uniqueness. A future SQL representation
   should be an `orderings` table with foreign keys to users and boards, an
   integer position, a primary/unique key on `(user_id, board_id)`, and a unique
   constraint on `(user_id, position)`. The foreign keys should cascade on
   deletion once SQL owns lifecycle enforcement.
5. Add a helper in `app/data.py` that orders an accessible board collection for
   a user from their `Ordering` records.
   - Ignore records for boards that are deleted or no longer accessible.
   - Collapse duplicate records defensively and use position order with a stable
     board-date tie-breaker if malformed data contains equal positions.
   - Put accessible boards with no ordering record first, newest first. This
     preserves the useful behavior that a newly created or newly shared board
     appears at the top of its section.
   - Follow those unseen boards with positioned boards in the user's chosen
     order.
6. In `boards.index`, order the complete accessible collection first and then
   partition it into Private boards and Shared boards. Filtering an already
   ordered collection preserves the user's relative order in each section.
7. Remove the template's `sort(attribute="created_at", reverse=True)` calls so
   Jinja does not overwrite the server-provided order.
8. Do not eagerly remove ordering records when sharing access changes.
   Inaccessible records are harmless and ignored; if access returns, retaining
   the prior personal position is reasonable. A successful later reorder
   replaces that user's ordering set and removes their stale records. When a
   board itself is deleted, delete all `Ordering` records for that board along
   with its pins and shares so the data remains suitable for eventual foreign
   keys.

This is slightly more verbose in the JSON store than an ID array on `User`, but
it preserves relational semantics now. At Cork's current scale, the extra rows
are insignificant compared with the store's existing whole-file save on every
request.

## Ordering resource and endpoint

Treat the signed-in user's ordering rows as a REST collection rather than adding
an action-style route beneath boards. The frontend may represent a move as a
source row plus a drop location, but it maps that state to a complete collection
representation for persistence.

1. Add `app/http/orderings.py` and register `PUT /orderings` in
   `app/http/__init__.py` behind the existing signed-in guard.
   - `GET /boards/` remains responsible for rendering boards in effective order.
   - `PUT /orderings` idempotently replaces the current user's ordering
     collection; do not add RPC-style `/boards/order` or `/reorder` endpoints.
2. Implement `orderings.update` following Cork's existing REST handler naming.
3. Represent the collection as repeated `board_id` values in desired order and
   parse them with the existing `Form`/`parser.List(parser.UUID())` support.
4. Validate the submitted representation before changing any rows:
   - IDs must be unique;
   - the submitted ID set must exactly equal the signed-in user's currently
     accessible board IDs;
   - reject malformed, missing, duplicated, inaccessible, or extra IDs with
     `400 Bad Request` and leave the preference unchanged.
5. After all validation succeeds, replace the signed-in user's complete
   `Ordering` set:
   - delete their existing ordering records, including stale and duplicate rows;
   - create one record per submitted board ID with sequential zero-based
     positions;
   - do not touch another user's ordering records.
6. Return `204 No Content`. The Helios store component will write the changed
   records to `data/store.json` after the response.

The collection representation contains all board IDs in their current page
order, not only the section that changed. Replacing the complete per-user set is
simple, idempotent, and restores its logical uniqueness in the JSON store. In
SQL, perform the equivalent upsert/delete work in a transaction under a
uniqueness constraint.

## Template wiring

Update `app/views/boards/index.html` without changing the board links or existing
owner action menus:

1. Attach one `board-order` Stimulus controller to the frame and provide
   `/orderings` as its collection URL value.
2. Mark each `<ol>` as a list target and each board `<li>` as an item target with
   its board ID.
3. Add the `⠿` reorder handle from the spike as a native button at the start of
   each board row. Make only the handle draggable so dragging does not compete
   with the board link or overflow action button. Give it concise title text
   explaining that it can be dragged or operated with the arrow keys.
4. Give the handle the native `draggable="true"` attribute and wire its
   `dragstart`, `dragend`, and keyboard events to the controller. Wire
   `dragover`, `drop`, and relevant leave events on each list.
5. Render handles for every accessible board. Reordering is the viewer's
   preference, so it does not require ownership of the underlying board.
6. Keep a drop-indicator element controller-owned or create it dynamically;
   do not render the spike's forced dragging state in the production template.

## Stimulus controller

Create `app/assets/scripts/controllers/board_order_controller.js`, then start a
Stimulus application and register `board-order` from
`app/assets/scripts/main.js`. Reuse the already-loaded Stimulus CDN global rather
than adding another frontend dependency.

The controller should:

1. On `dragstart`:
   - resolve the board row from the dragged handle;
   - remember its source list and original sibling for rollback;
   - set the board ID as `text/plain`, set `effectAllowed` to `move`, and use the
     complete row as the drag image if needed;
   - add the dragged class on the next animation frame.
2. On `dragover`:
   - call `preventDefault()` only for the source list, thereby rejecting
     cross-section drops;
   - compare the pointer's vertical coordinate with the midpoint of each
     non-dragged row;
   - move a single drop indicator before the matching row or to the end of the
     list.
3. On `drop`:
   - replace the indicator with the dragged row;
   - serialize every item target in current document order;
   - send a same-origin `PUT` using `URLSearchParams` with repeated `board_id`
     fields. Do not use `FormData`, because Helios currently parses only
     `application/x-www-form-urlencoded` request bodies;
   - accept the empty `204` response; no Turbo Stream response or page reload is
     needed on success.
4. On request failure or a non-success response, restore the row to its original
   position and remove all temporary state. A subsequent Turbo navigation or
   refresh will therefore agree with persisted state.
5. On `dragend`, clean up the indicator, classes, and controller references even
   when the drop was cancelled or occurred outside a valid list.
6. Prevent overlapping persistence operations. While a save is pending, reject
   another drag/keyboard move or serialize saves so a slower earlier request
   cannot overwrite a newer order.

## Keyboard behavior

Native drag and drop does not provide keyboard sorting. Make the visible handle
keyboard-focusable and support Up/Down Arrow on it:

1. Move the board one position within its current section; do not cross a section
   header.
2. Keep focus on the moved handle and persist the same full-page ID sequence used
   by pointer drops.
3. Prevent the page from scrolling only when a supported reorder key is handled.
4. Disable or ignore another move while persistence is pending and restore the
   original position if persistence fails.

Use a native button for the handle so it participates in the tab order and has
normal focus behavior. Browser-test drag initiation from the button on each
target platform, but do not add a separate JavaScript pointer-drag system.

## Styling

Move the approved parts of `designs/56-board-reordering.html` into
`app/assets/styles/main.css`, adapting them to live states:

- reserve the slim `0.5rem` handle gutter and reduced adjacent gap so board
  titles shift by less than the first spike;
- keep the Unicode handle at metadata size and muted in normal use;
- reveal it on row hover/focus for hover-capable devices and keep it subtly
  visible on `hover: none` devices;
- apply a no-shadow dragged treatment using existing surface and border tokens;
- show a blue insertion rule at the pending destination;
- retain visible focus styling and `grab`/`grabbing` cursors;
- preserve light/dark behavior through semantic tokens.

Treat the transform, opacity, and exact drop-rule geometry in the spike as values
to tune during browser testing, especially near the frame's clipped edges.

## Verification

### Automated

Add focused tests under `test/` using Helios's existing test runner where
practical:

1. The new Helios `Int` codec round-trips integer model attributes through JSON.
2. No `Ordering` records returns the current newest-first order.
3. A complete ordering is respected independently for two users viewing the same
   shared board.
4. New/unpositioned boards appear first newest-first; stale, duplicate, and
   equal-position records do not duplicate or hide accessible boards.
5. The endpoint accepts a complete accessible sequence, replaces only the
   signed-in user's rows, and produces unique sequential positions.
6. Missing, duplicate, malformed, extra, and inaccessible IDs return `400` and do
   not mutate existing ordering records.
7. Deleting a board deletes its ordering records for every user.

Run the Helios tests after adding `Int`, then run Cork's `uv run test`, a Python
compile check over `app`, and `mise run lint`.

### Browser

1. Reorder the first, middle, and last board within each section and confirm the
   insertion indicator tracks row midpoints.
2. Refresh and sign out/in to confirm persistence; sign in as another user to
   confirm their ordering is independent.
3. Confirm dragging cannot move a board between Private and Shared sections and
   cannot be initiated from the title link or action menu.
4. Confirm a cancelled drag and a simulated failed request restore the original
   order and clear all temporary styling.
5. Use the keyboard handle to move rows up/down, verify focus follows the row,
   and verify boundary moves do nothing.
6. Test board creation, deletion, newly granted access, and removed access against
   an existing preference.
7. Test desktop Chrome/Firefox/Safari and current iOS Safari/Android Chrome,
   paying particular attention to long-press initiation versus page scrolling.
8. Check narrow and desktop widths, light and dark modes, hover/focus visibility,
   the native drag image, and the existing board/action links.
