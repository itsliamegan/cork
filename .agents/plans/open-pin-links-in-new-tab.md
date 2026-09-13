# Open pin links in a new tab

## Goal

Add a per-user preference that controls whether links to a Pin's saved external
URL open in the current tab or a new tab. Preserve the current same-tab behavior
unless the user opts in.

## Scope and decisions

- Persist the preference on the `User`, so it follows the selected account rather
  than a browser session.
- The preference applies to the signed-in viewer. On a shared board, each viewer's
  own setting controls link behavior regardless of who owns the board or pin.
- Apply it only to links that visit `pin.url`; Cork navigation and action links
  continue opening in the current tab.
- Default existing and newly created users to same-tab behavior.
- Use normal server-rendered forms and the existing artificial PUT mechanism; no
  JavaScript is needed.

## Data model and compatibility

1. Add `open_in_new_tab` to `User.attrs` in `app/data.py` as a
   `types.Bool()` attribute with `default = False`.
2. Rely on the model default when loading existing user records that do not yet
   contain the attribute. The next store save will persist the default, so no
   one-off edit to `data/store.json` is required.
3. Keep user creation compatible by using the default rather than requiring every
   caller to provide the preference.

## Settings update endpoint

1. Register `PUT /settings` in `app/http/__init__.py` alongside the existing
   settings show route and behind the signed-in guard.
2. Add `settings.update` in `app/http/settings.py`.
3. Validate `open_in_new_tab` with `parser.Bool()` so a checked checkbox
   becomes `True`, an omitted checkbox becomes `False`, and unexpected values
   produce a `400 Bad Request`.
4. Assign the validated value to `ctx.auth.user`; the store component will persist
   the mutated user after the response.
5. Redirect back to `/settings` after a successful update.

## Settings interface

1. Add a **Preferences** section to `app/views/settings/show.html` between Account
   and Session.
2. Render a POST form targeting `/settings` with a hidden `_method=PUT` field.
3. Include a checkbox named `open_in_new_tab`, checked from the user's
   saved value, with clear copy such as **Open pin links in a new tab**.
4. Include a Save button rather than autosaving, keeping the interaction usable
   without JavaScript and consistent with the rest of Cork.
5. Reuse the existing frame, setting-row, checkbox, and button styles where
   practical. Add only narrowly scoped CSS in `app/assets/styles/main.css` if the
   preference row needs alignment or responsive adjustments.

## Pin link rendering

1. Pass the signed-in user's `open_in_new_tab` preference from
   `boards.show` in `app/http/boards.py` to `app/views/boards/show.html`.
2. When the preference is enabled, render the external `.pin-link` with
   `target="_blank"` and `rel="noopener noreferrer"`.
3. When disabled, omit those attributes so the existing same-tab behavior is
   unchanged.
4. If another Pin read surface that links directly to `pin.url` is added (for
   example, the separately planned Pin details page), pass and apply the same
   viewer preference there as well.

## Verification

There is currently no Cork test suite, so use compile/static checks and manual
browser verification without starting another server process.

1. Run a Python compile check over `app`.
2. Load the existing store before any migration and confirm users without the new
   JSON field receive `False` without errors.
3. Confirm Settings initially shows the checkbox unchecked for an existing user.
4. Enable the setting, save, and confirm the redirect returns to Settings with the
   checkbox still checked and the value persisted in `data/store.json`.
5. Confirm Pin URL links now include the new-tab attributes and open in a new tab.
6. Disable the setting and confirm Pin URL links return to normal same-tab
   behavior.
7. Sign in as a second user and verify their setting is independent, including
   when both users view the same shared board.
8. Submit an invalid checkbox value directly and verify the update returns
   `400 Bad Request` without changing the saved preference.
9. Check the Settings layout at desktop and narrow viewport widths and verify the
   checkbox has a visible keyboard focus state and an associated clickable label.
