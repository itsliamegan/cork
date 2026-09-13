# Navbar account identity

## Goal

Show the signed-in user's name in the signed-in site header while preserving
**Settings** as an unmistakable navigation link. Implement option D from
`designs/55-navbar-account-identity.html`:

`Liam E. / Settings`

The name uses regular-weight muted text, the slash is a quiet separator, and
Settings keeps its existing underlined-link treatment. Bold remains reserved for
the Cork wordmark and active navigation state.

## Scope and decisions

- Show the identity on every signed-in page, not only the boards index. The
  shared base layout already owns the header, and a stable account indicator is
  more predictable than one that disappears after navigating away from the front
  page.
- Keep the name as plain text. It is status information, not another link.
- Keep Settings as a separate link with its existing active state on the Settings
  page.
- Do not add an avatar, initials badge, popover, account menu, or JavaScript.
- Leave the sign-in page header unchanged; it overrides the base layout's signed-in
  navigation block.
- Use the complete stored display name. At narrow widths, truncate unusually long
  names rather than abbreviating or hiding the identity.

## Template data

1. Standardize signed-in render contexts on a `current_user` value containing
   `ctx.auth.user`.
2. Add `current_user` to every render performed by the guarded handlers in
   `app/http/boards.py`, `app/http/pins.py`, and `app/http/settings.py`. Keep this
   explicit in each handler rather than mutating Jinja globals, which are shared
   by the Helios `Views` instance and therefore unsuitable for request-specific
   state.
3. Where a template currently receives only `current_user_id`, pass
   `current_user` instead and compare against `current_user.id`. This avoids
   carrying two forms of the same viewer identity.
4. In `app/views/settings/show.html`, replace the page-specific `user` assignment
   with `current_user` for the account name and preference value. Keep `owner`
   assignments on board forms because that name describes a separate template
   role.
5. Do not pass `current_user` from `auths.new`; the sign-in template suppresses the
   entire `site_navigation` block.

## Header markup

1. Update `app/views/layouts/base.html` inside `#site-actions`.
2. Before the Settings link, render the escaped display name from
   `current_user.name` in a non-interactive element.
3. Add a separate slash element between the name and Settings. Mark the slash
   `aria-hidden="true"` because it is visual punctuation rather than meaningful
   content.
4. Preserve the current Settings link, destination, active class, and link text.

The resulting accessible reading order should be the user's name followed by the
Settings link, without presenting the name as an action.

## Styling and responsive behavior

1. Add narrowly scoped identity and separator classes in
   `app/assets/styles/main.css`.
2. Render the identity at `var(--font-size-label)`, regular weight, and
   `var(--color-text-muted)` to match option D without introducing another bold
   element.
3. Render the slash in a quieter existing neutral/border color. Do not add a new
   design token solely for the separator.
4. Reuse the existing `#site-actions` flex layout and spacing, adjusting its gaps
   only if needed to match the spike.
5. Give the actions group and identity the necessary `min-width: 0`, overflow,
   ellipsis, and no-wrap rules so long names truncate before they can displace
   Cork or Boards. Keep Settings non-shrinking and fully visible.
6. Preserve existing light/dark theme behavior by using semantic color tokens
   rather than fixed colors.

## Verification

There is currently no Cork test suite, so verify through static checks and the
already-running development server.

1. Run `mise run lint`.
2. Sign in as each existing user and confirm the correct name appears on the
   boards index.
3. Visit the board show, board create/edit, pin create/edit, and Settings pages and
   confirm the same identity remains in the header without undefined template
   values.
4. Confirm Settings remains visibly underlined and clickable, while the name and
   slash are not interactive.
5. On `/settings`, confirm the existing active treatment applies only to Settings
   and the identity remains regular weight.
6. Visit `/sign-in` while signed out and confirm its navigation-free header is
   unchanged and no missing-user value is rendered.
7. Check narrow and desktop viewport widths, including a temporarily long display
   name, and confirm the name truncates while Cork, Boards, and Settings remain
   legible and usable.
8. Check light and dark color schemes and keyboard focus on Settings.
