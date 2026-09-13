# Pin details and note

## Goal

Give every pin a canonical internal details page and one optional, owner-authored
note. Keep the pin title on a board linked to the saved external URL, while a
separate, visible **Details** link opens the Cork resource.

The details page is the read surface for a pin. The edit page remains the write
surface, so users never need to enter an editing context just to read a note.

## Scope and decisions

- A pin has one plain-text `note`, not a collection of notes or comments.
- The note belongs to the pin and is visible to everyone who can access the
  pin's board.
- Only the pin's creator can change the note, using the existing edit form and
  update endpoint.
- Notes are plain text: no Markdown, attribution, history, notifications, or
  separate timestamps.
- An empty note is valid and is represented by an empty string.
- The note is not collected on the new-pin form in this iteration; a pin is
  created with an empty note and its creator can add one through Edit.
- Comments, per-user notes, and collaborative note editing are out of scope.

## Data model and compatibility

1. Add `note` to `Pin.attrs` in `app/data.py` as a string with an empty-string
   default.
2. Use the model default when creating pins, so `pins.create` does not need to
   supply a note while the new-pin form remains unchanged.
3. Rely on the default to load existing `Pin` records in `data/store.json` that
   do not yet contain the attribute. Helios fills a missing attribute when it
   has a non-`None` default, and the next store save will persist `note: ""`.
   No one-off data-file migration is required.

## Pin access

1. Add a `find_accessible_pin` helper in `app/data.py` alongside the existing
   board access helpers.
2. Have the helper load the pin and verify access through its parent board using
   `find_accessible_board`/`can_access_board` semantics.
3. Treat a pin with no board, a missing parent board, or an inaccessible parent
   board as unavailable rather than allowing direct access through a guessed
   pin URL.
4. Continue using `find_owned` for edit and update. Details access must not imply
   edit access.

## Details route and handler

1. Register `GET /pins/{id}` in the `/pins` route group in
   `app/http/__init__.py`.
2. Add `pins.show` in `app/http/pins.py`.
3. In the handler:
   - Load the pin through the accessible-pin path.
   - Load its board for context and navigation.
   - Load the pin creator for attribution metadata.
   - Pass the signed-in user's ID so the template can conditionally show Edit.
   - Render `pins.show`.
4. Return the same not-found behavior used by the rest of the application when
   the pin does not exist or its board is inaccessible.

## Details view

Create `app/views/pins/show.html` with the boards navigation active.

1. Use the pin title as the page title and show the board as linked context back
   to `/boards/{board.id}`.
2. Put the primary actions in the page header:
   - **Visit link** points to the pin's external URL and is available to every
     viewer.
   - **Edit** points to `/pins/{pin.id}/edit` and appears only when
     `pin.user_id == current_user_id`.
3. Render a details frame containing:
   - The saved URL as a visible, usable link.
   - The pin creator and creation date.
   - A Note section.
4. Render note text with escaped HTML and preserved line breaks. Do not treat it
   as markup.
5. Show a muted `No note.` empty state when the note is empty so the details
   page remains structurally consistent.
6. Reuse existing page-header, frame, metadata, button, and empty-state styles
   where possible. Add narrowly scoped styles to `app/assets/styles/main.css`
   only for details layout and preserving note whitespace.

## Board affordance

Update `app/views/boards/show.html` without changing the pin title's current
behavior.

1. Keep the pin title and URL wrapped by the external `pin.url` link.
2. Add a persistent text link labelled **Details** in each pin's metadata area,
   next to the creation date.
3. Show Details to every user who can view the board, including users who do
   not own the pin.
4. Keep Edit and Delete in the owner-only action menu; do not add Details to
   that menu.
5. Adjust the pin metadata styles so the date and Details link are readable at
   narrow widths and do not compete with the owner action menu.

## Edit and update flow

1. Add a Note textarea to `app/views/pins/edit.html` after the existing pin
   fields.
   - Populate it with `pin.note`.
   - Do not mark it required.
   - Use the existing form-field styling, with a modest multi-line default
     height.
2. Add `note` to the update form in `app/http/pins.py` using an optional string
   parser.
3. Normalize an omitted or empty submitted value to `""` before assigning it to
   the model.
4. Preserve the existing ownership check and title, URL, and board validation.
5. On a successful update, redirect to `/pins/{pin.id}` rather than the board.
   This remains correct if the update moved the pin to another accessible
   board.
6. Change the edit form's Cancel link to `/pins/{pin.id}` so both save and
   cancel return to the read surface.

## Verification

There is currently no Cork test suite, so perform static and manual checks
without starting another server process.

1. Run a Python compile check over `app` after the changes.
2. Open an existing pin whose stored JSON predates `note` and verify the store
   loads successfully and the details page shows `No note.`.
3. As the pin creator:
   - Open Details from the board.
   - Follow Visit link to the external URL.
   - Open Edit from Details, add a multi-line note, and save.
   - Verify the redirect returns to Details and preserves line breaks.
   - Clear the note, save, and verify the empty state returns.
   - Cancel an edit and verify it returns to Details without changes.
4. Move a pin to another accessible board while editing and verify save returns
   to the same pin's details page with the new board context.
5. As a user with shared access to the board:
   - Verify Details and the note are visible.
   - Verify Edit is absent.
   - Verify direct requests to the edit/update endpoints remain unavailable.
6. As an unrelated signed-in user, verify a guessed `/pins/{id}` URL does not
   expose the pin, note, URL, creator, or board metadata.
7. Verify a pin's title on `boards.show` still opens the external URL, while its
   Details link opens `/pins/{id}`.
8. Verify existing pin creation and deletion workflows still work and that a
   newly created pin starts with an empty note.
9. Check details, edit, and board pages at both desktop and narrow viewport
   widths, including a long URL and a long multi-line note.
