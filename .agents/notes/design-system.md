# Cork visual design direction

The accepted visual direction is represented by these standalone mockups:

- `designs/26-compact-headered-list.html`
- `designs/27-compact-headered-form.html`
- `designs/28-compact-headered-dialog.html`
- `designs/29-compact-headered-sign-in.html`
- `designs/45-compact-headered-settings.html`
- `designs/54-compact-details-people.html`

`designs/24-dark-compound-sharing.html` is the initial reference for dark-mode
color relationships, but should adopt the more compact sizing of the later
mockups.

## Character

Cork should look like a small, practical tool used by friends. The interface is
compact, neutral, direct, and highly structured. Its influences are transit
signage, public-service design, and traditional desktop/workbench interfaces.
It should not resemble a spacious SaaS dashboard.

Hierarchy comes from typography, rules, connected frames, alignment, and
controlled background changes. The interface does not use simulated physical
depth.

## Foundations

### Typography

- Use `"Helvetica Neue", Helvetica, Arial, sans-serif` throughout.
- Default text is approximately `14px / 1.35`.
- Page titles are approximately `1.45rem`, bold, with tight line height.
- Document titles use regular dashes, not em dashes.
- Component headings are approximately `0.85rem`, bold.
- Labels and secondary navigation are approximately `0.75rem–0.78rem`.
- Metadata is approximately `0.68rem–0.72rem` and uses the muted foreground.
- Do not use oversized display typography.
- A second typeface may eventually be used for a narrow accent role, but is not
  part of the established system.

### Width and density

- The normal application measure is `35rem`.
- Use approximately `0.6rem` horizontal page padding.
- The global header is approximately `2.8rem` tall.
- Main content begins approximately `1.35rem` below the header.
- Controls generally use `0.34rem–0.4rem` vertical padding.
- Content rows are approximately `3rem–3.7rem` tall depending on their content.
- Prefer compact, deliberate spacing over explanatory text used to fill space.

### Light palette

- Page background: `#fff`
- Primary foreground: `#111`
- Muted foreground: `#626262`
- Off-gray surface/header: `#f1f1f1`
- Strong component border: approximately `#999`
- Quiet divider: approximately `#d5d5d5`
- Primary blue: `#0f61a9`
- Destructive foreground: approximately `#9b1c1c`

The global header is off-gray, not black. Color is functional rather than
decorative. Blue is reserved for links, focus, active navigation, and primary
actions.

## Page hierarchy

A normal page has:

1. The compact global header.
2. A page header with the page title, optional page-level actions, and an
   optional trailing contextual label for edit forms and subordinate
   operations.
3. One or more framed components.

The page header ends with a `3px` dark rule. This is the strongest rule on the
page and separates page identity from page content. Keeping context inside this
header prevents contextual pages from shifting the title and content downward.

Page titles should describe the current operation: `New pin`, `Edit`, or the
board title. Do not retain a generic parent title on create/edit pages.

Copy should be concise. Do not add SaaS-style explanatory sentences merely to
create rhythm. Keep text that communicates actual state, errors, consequences,
or distinctions such as `Owner` and item counts.

## Global header

- Off-gray background with a quiet lower border.
- Brand at the left, primary navigation beside it, settings/account at the
  right.
- Active navigation uses a `3px` blue lower rule.
- Header links use dark text in light mode.
- Avoid decorative icons or oversized branding.

## Frames, not cards

Boxes are an important compositional tool in Cork. Treat them as connected
frames rather than collections of independent cards.

A frame has:

- One `1px` outer border.
- A small `3px` radius on the outer silhouette.
- Connected internal regions separated by rules.
- No shadow.
- No large gaps between related regions.

Frames may contain headers, rows, fields, actions, and additional functional
sections. Nested regions should use internal dividers rather than another full
border. Only genuinely independent components should receive separate frames.

This preserves the original design's ability to compose and nest interface
regions without producing a dashboard of floating cards.

## Component headers

Component headers are part of the chosen style and should be retained.

- Use a narrow off-gray label bar.
- Keep padding around `0.35rem 0.65rem`.
- Use a bold, compact heading.
- End with a `2px` dark rule.
- Metadata such as a count may align to the right in small muted text.
- A blue left rule may mark an action-oriented section, but should be uncommon.

The headers avoid a Bootstrap-like appearance by being compact, connected to a
compound frame, and defined by strong rules. Avoid large padded gray headers on
separate rounded cards.

## Buttons and controls

- Buttons, inputs, and selects use a restrained `3px` radius.
- Secondary buttons are white with a medium gray border and dark text.
- Primary buttons use `#0f61a9`, a darker blue border, and white text.
- Destructive secondary buttons use a muted red label; destructive confirmation
  buttons may use a solid red treatment.
- Do not use pill shapes, gradients, or shadows.
- Links that act as buttons must be styled anchors; do not wrap a `<button>` in
  an `<a>`.
- Focus should use a clearly visible blue outline or translucent blue focus
  ring.

## Lists

- Place related list rows inside one frame.
- Use a compact component header for the list title and optional count.
- Separate rows with quiet `1px` rules.
- Keep the item title strongest, URL or description secondary, and timestamp
  smallest.
- Row actions align consistently at the far edge.
- Avoid giving every row its own card, background, or border.
- Empty states should occupy a valid list row or a dedicated frame region.

## Forms

- Place the form inside one frame.
- A compact component header such as `Details` is acceptable and part of the
  visual rhythm.
- Each field is a connected row separated by a quiet rule.
- On normal screens, align labels in a narrow first column and controls in the
  flexible second column.
- Stack labels above controls on narrow screens.
- Place actions in the final divided row; it does not need a distinct gray
  footer background.
- Use `Save` for the primary action on new and edit forms; the page title already
  communicates whether the operation creates or updates a record.
- Use validation and helper text only when it communicates something the user
  needs to act on.

## Compound screens

When a feature contains several closely related operations, compose them into
one frame. Board editing combines `Details` and `Sharing` in one outer frame.
The sharing section uses checkboxes for the pending access selection, identifies
the immutable owner, and applies changes with the form's shared `Save` action.
Each section has its own compact connected header, and the rows beneath it share
the same outer contour.

Keep board creation focused on the required title. Sharing is optional
configuration and belongs on the edit screen rather than the new-board screen
or a separate sharing page.

This is preferred to either extreme:

- several independent cards floating with gaps, or
- completely open sections that lose compositional rhythm.

## Popovers and dialogs

Popovers and dialogs are raised because they actually occupy a layer above the
page, but they still do not use shadows.

### Popovers

- White surface with a strong `1px–2px` border and `3px` radius.
- Use overlap and occlusion to communicate layering.
- Divide groups of actions with quiet rules.
- Keep menu items compact and full-width.
- Use a destructive text color for destructive actions.

### Dialogs

- Use a strong `2px` dark outline and `3px` radius.
- Use a dim backdrop to separate the dialog from the page.
- Do not use a box shadow.
- Use a narrow off-gray header with a `2px` dark lower rule when a title adds
  useful context; omit decorative or repetitive dialog headers.
- Separate the action row with a quiet rule.
- Dialog copy should state the specific consequence rather than use generic
  confirmation language.
- Keep confirmation actions compact and specific enough for their context;
  use `Delete`, not `OK` or a repeated resource name.

## Sign-in

- Use the same global header with branding only.
- Use a narrower frame, approximately `22rem`, positioned higher than center.
- Preserve the same component header, field-row, and action-row treatment.
- Keep the screen minimal; do not add marketing or onboarding copy.

## Dark mode

Dark mode should preserve the same hierarchy and remain neutral:

- Page background near `#151515`.
- Off-gray header/surface near `#242424`.
- Controls slightly darker than raised surfaces.
- Primary text near `#f1f1f1`; muted text near `#aaa`.
- Strong borders near `#707070`; quiet dividers near `#3e3e3e`.
- `#0f61a9` may remain the primary action fill and active-navigation rule.
- Text links need a lighter blue than `#0f61a9` to maintain contrast.
- Preserve rule weights, density, and component structure exactly across color
  schemes.

## Implementation order

Build the system from shared foundations upward. Complete each layer across light
and dark modes before using it to compose the next layer.

1. **Theme tokens**
   - Define semantic color roles for the canvas, surfaces, controls, text,
     borders, actions, danger states, focus, and backdrops.
   - Establish the fluid root type size, semantic type sizes, line heights, and
     font weights.
   - Establish the compact spacing scale, application measures, rule weights,
     and `3px` radiuses.
   - Prefer semantic aliases such as `--page-gutter` only when they coordinate
     a meaningful global decision. Do not create tokens for isolated values.

2. **Document foundations**
   - Apply the root type scale and default body typography, foreground, and
     canvas colors.
   - Normalize headings, lists, forms, and interactive elements.
   - Define link behavior and a consistent, visible focus treatment.
   - Keep borders and radiuses in pixels while type, spacing, and measures use
     `rem`, so the interface scales without softening its rules.

3. **Simple controls**
   - Implement buttons that work directly on either `<button>` or `<a>`.
   - Add primary, destructive, and icon-only variants.
   - Implement text inputs, selects, and textareas with shared dimensions,
     borders, disabled states, and focus states.
   - Remove nested interactive markup such as an anchor wrapping a button.

4. **Frame primitives**
   - Implement the outer frame, component header, metadata, connected content
     rows, and action row.
   - Make internal regions share the outer contour and use dividers rather than
     nested borders.
   - Treat this frame grammar as the main reusable structural primitive; lists,
     forms, sharing, settings, and sign-in should all build on it.

5. **Application shell**
   - Implement the global header, constrained content measure, and shared page
     gutter.
   - Add the contextual label and page header, including page actions and the
     strong lower rule.
   - Implement responsive behavior for narrow screens without reducing the base
     text below `16px`.

6. **Core compositions**
   - Build framed lists with connected rows, metadata, empty states, and aligned
     row actions.
   - Build framed forms with label/control grids, validation regions, and a
     final divided action row.
   - Build compound frames from multiple connected sections without adding
     gaps or duplicate outer borders.

7. **Layered components**
   - Implement compact popover menus with divided action groups.
   - Implement dialogs with a backdrop, strong outline, connected header, body,
     and action regions, and no shadow.
   - Verify keyboard operation, focus placement, accessible labels, and specific
     destructive-action copy.

8. **Feature composition**
   - Board and pin rows use parallel flex structures while retaining
     feature-specific class names.
   - Board editing is the reference compound-frame screen, combining details
     and sharing without a separate sharing route.
   - Settings uses compact frame rows for account and session information.
   - Sign-in uses the shared base layout with branding only and a narrow page
     modifier.
   - Keep feature classes limited to domain-specific content such as pin URLs,
     timestamps, board details, and sharing rows. They should not redefine the
     shared frame or control appearance.

The intended dependency direction is: tokens define hierarchy, foundations set
defaults, primitives define appearance, compositions define structure, and
feature classes describe domain content.

## Avoid

- Box shadows, including on popovers and dialogs.
- Multiple detached rounded cards with uniform gaps.
- Large radii and pill-shaped controls.
- Warm or cool tinting of the overall interface.
- Decorative color that does not communicate state or action.
- Gray header/body/footer treatment applied mechanically to every component.
- Excess explanatory or onboarding copy.
- Spacious dashboard layouts and oversized type.
- Invalid nested interactive elements.
- Accessibility-only labels or ARIA labeling attributes. Cork is an internal
  site; use concise visible text for controls instead. Keep native form labels
  associated with their controls.
