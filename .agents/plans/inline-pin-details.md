# Inline pin details

## Goal

Implement the expandable pin treatment represented by `sketch/118-inline-pin-details.html` on a Board page. A Pin's existing **Details** link remains a usable non-JavaScript link, while Turbo and a small Stimulus controller progressively enhance it into an inline panel fetched from `GET /pins/{id}`.

The inline action labels are exactly **View** and **Edit**. Do not add an “also on N boards” summary to Pin rows. Remove the visible Board backlink/context from both the new-Pin and edit-Pin page headers.

## Presentation data

Update `app/http/boards.py` so `boards.show` preserves each Pin's current `Placement` instead of reducing the placement join to a bare list of Pins. Build one row value per Placement containing the Pin and a compact URL label.

- Derive the compact label from the URL hostname for display in the Pin list, dropping a leading `www.` to match the sketch.
- Keep the Pin title linked to the complete external URL; shortening affects visible list text only.
- Fall back to the complete URL when no hostname can be derived, so unusual stored values remain identifiable.
- Keep sorting by the Pin's creation time and continue submitting the current Board as the delete return target.

Extend `pins.show` in `app/http/pins.py` to prepare the data needed by the details page and its embedded Turbo Frame:

1. Load all Placements for the accessible Pin.
2. Retain only Placements whose Boards are accessible to the current viewer; do not disclose inaccessible Board titles through chips.
3. Preserve the existing referring-Board context selection, using the deterministic fallback when needed.
4. Load the contextual Placement's `adder_id` as a `User`; the **Added by** row displays only that user's name.
5. Pass the accessible Boards for chip rendering, together with ownership state for the conditional Edit action.

Do not branch on a Turbo-specific request header or introduce a fragment endpoint. `GET /pins/{id}` always renders the normal page containing a matching Pin-specific `<turbo-frame>`; Turbo can extract that frame when the page is requested from a Board row. No model, schema, migration, or new route is required.

## Shared Board chip

Add `app/views/boards/_chip.html` as the canonical Board chip partial.

- Render a real link to `/boards/{board.id}` inside the chip; the current Board is not a non-link special case.
- Use a shared `.board-chip` class with compact bordered, selected-surface styling consistent with the sketch and both color schemes.
- Make links rendered inside a Turbo Frame navigate the top-level page rather than replacing the Pin detail frame.
- Use this partial for every accessible Board in the inline panel and on the full Pin details page, replacing any ad hoc Board-link treatment introduced there.

## Board Pin rows and Turbo interaction

Restructure each item in `app/views/boards/show.html` around a summary plus a Pin-specific empty `<turbo-frame>`.

- Show the linked title, shortened hostname/URL, creation date, and **Details** toggle in the summary.
- Retain the existing owner-only action menu and delete dialog.
- Do not render placement-count copy such as “Only on this board” or “Also on N boards.”
- Give each frame a stable unique ID such as `pin-{pin.id}-details`; use the same ID in the response returned by `pins.show`.
- Render the Details control as a normal `<a href="/pins/{id}">` and set `data-turbo-frame` to the matching Pin-specific frame ID. Do not replace it with a button or make JavaScript responsible for navigation: without JavaScript it follows the canonical details URL, while Turbo requests that same page and extracts its embedded frame when JavaScript is available.

Add `app/assets/scripts/controllers/pin_details_controller.js` and register it in `app/assets/scripts/main.js`.

- On an unexpanded-row click, ensure an empty matching `<turbo-frame>` is present, allow the anchor's normal Turbo-targeted visit to proceed, mark the row expanded, and change only the anchor text to **Hide details**.
- While Turbo fetches, keep the row structurally stable; the matching frame embedded in the returned details page supplies the panel.
- On an expanded-row click, prevent the anchor navigation, remove the populated Turbo Frame from the row, remove expanded state, and restore the anchor text to **Details**.
- On the next click, create a fresh empty frame before allowing the anchor visit, so Turbo fetches the details page again rather than restoring cached inline content.
- Keep state scoped to each row so several Pins can be expanded independently. The interaction is deliberately: click to fetch/show, click to remove/hide, click to fetch/show fresh.

## Pin details view and embedded frame

Edit `app/views/pins/show.html` so the complete page contains both its visible standalone details layout and a hidden Pin-specific `<turbo-frame>` containing the inline-panel representation. Use the same frame ID targeted by the corresponding Board row.

This keeps the two presentations free to differ without introducing a frame-only route: without JavaScript, the normal anchor opens the complete visible details page; with Turbo, the response parser finds the hidden matching frame and copies its contents into the visible destination frame on the Board. Hide the source frame only in the full-page context (for example, with `hidden` or a page-context selector); do not put hidden state on the extracted inner panel or the Board's destination frame. Verify against the installed Turbo version that source-frame visibility attributes are not propagated when its contents replace the destination.

Add a focused partial under `app/views/pins/` for the inline frame's inner rows. The embedded inline panel follows the sketch's connected rows:

- **URL**: the complete saved URL, linked externally and honoring the viewer's `open_in_new_tab` preference.
- **Added by**: the contextual `Placement.adder_id` user's name only.
- **Note**: escaped plain text with line breaks preserved, or the existing `No note.` empty state.
- **Boards**: one shared Board chip per accessible Placement.
- Footer actions: **View** links to `/pins/{id}` at the top level; **Edit** links to `/pins/{id}/edit` at the top level and is present only for the Pin creator.

The visible full Pin page may retain or independently revise its current section/header composition; it does not need to render the inline footer actions. Expose the accessible Board chips and contextual placement attribution there without making access rules broader, and keep its normal page title and canonical URL. Within the hidden inline frame, internal footer links and Board chips must target the top-level page so **View**, **Edit**, and Board navigation do not occur inside the destination frame.

## Pin form headers

Update `app/views/pins/new.html` and `app/views/pins/edit.html` so their page headers contain only **New pin** and **Edit**, respectively. Remove the `#page-context` Board label and link from both pages.

- Keep the originating Board available to the new form for its preselected checkbox, hidden `return_to`, and Cancel destination.
- Keep the edit form's validated `return_to` value and Cancel behavior; removing the visible backlink must not change where save or cancel returns.
- Stop loading or passing a singular contextual `board` from `pins.edit` if it has no remaining consumer after the template change. The Pin's plural Placement set remains the source for checked Boards and return-URL validation.

## Styling

Update `app/assets/styles/main.css` with narrowly scoped styles based on the sketch:

- compact summary spacing, metadata, hostname truncation, and expanded-row background;
- an inset bordered inline panel with two-column label/value rows, divided footer, and URL truncation;
- reusable Board chip layout and wrapping;
- preserved whitespace for notes;
- narrow-screen stacking for detail labels and values without interfering with the action menu.

Reuse existing theme tokens, buttons, frame rules, focus treatment, and dark-mode semantic colors. Do not copy standalone sketch colors into feature styles.

## Tests

Extend `test/boards_test.py` to verify observable Board-page output:

1. Each placement renders the corresponding Pin once with a normal `/pins/{id}` Details anchor whose `data-turbo-frame` value matches the row's empty Turbo Frame.
2. The visible list label uses the shortened hostname while the external link retains the complete URL.
3. No “also on” placement-count text is rendered.
4. Existing owner-only menus and Board-context delete return values remain intact.

Extend `test/pins_test.py` to verify Pin-details behavior:

1. A normal `GET /pins/{id}` renders complete visible details plus a hidden matching frame containing URL, note, contextual adder name, Board chips, and **View**/**Edit** actions, allowing Turbo to extract it without a special response branch.
2. A shared viewer gets **View** but not **Edit**.
3. The referring Board selects the correct Placement and adder when different users added the same Pin to different Boards.
4. Only Boards accessible to the viewer are disclosed as chips.
5. A normal details request still renders a complete page and unauthorized Pin access remains not found.
6. Empty notes retain their explicit empty state.
7. New and edit Pin pages no longer render a visible `Board:` backlink while retaining their expected checkbox selection, return target, and Cancel destination.

Because there is no browser-side JavaScript test harness, manually verify first-load, frame removal on hide, a fresh network fetch on every reopen, multiple expanded rows, normal-anchor navigation without JavaScript, keyboard focus, long URLs/notes, narrow layout, and light/dark modes.

## Verification

Run:

- `mise run test`
- `mise run lint`

Do not start another development server; use the already-running server for manual browser checks.
