# Wireframe and existing design-system evaluation

## Overall assessment

The systems share a strong base:

- Compact, neutral, flat presentation.
- Restrained controls and metadata.
- Rows connected by quiet dividers.
- No reliance on shadows or decorative color.
- Emphasis on scanning rather than explanatory copy.

The main difference is compositional grammar.

**The existing system creates hierarchy structurally:** attached headers, strong
rules, and compound frames explicitly declare relationships.

**The wireframes create hierarchy spatially:** headings and metadata float near
their content, while whitespace and smaller local containers imply
relationships.

The wireframe's outer gray `.frame` is treated here primarily as a
representation of the application viewport, not necessarily as a proposal to
put the whole application inside a rounded panel.

## Important differences

| Area | Existing system | Wireframes |
| --- | --- | --- |
| Application shell | Full-width gray global header separated from the page | Navigation visually participates in the local page and ends with a quiet rule |
| Page identity | Large page title followed by a strong `3px` rule | Often supplied by active navigation; board detail uses an open title without a rule |
| Section titles | Attached header bars inside frames | Small labels floating just above containers |
| Containment | One compound frame containing related sections | Several independent lists, tiles, cards, and controls |
| Relationship cue | Borders and physical attachment | Proximity and whitespace |
| Vertical rhythm | Compact and nearly continuous | Compact within components, but more air between groups |
| Record collections | Rows share one outer contour | Some shared lists, but board-detail pins are detached cards |
| Actions | Page actions beside the page title; row actions in menus | Creation actions appear in navigation; some item actions expand inside the item |
| State | Primarily text, controls, and menus | Placement pills, filter chips, inline sharing status, selected-card expansion |
| Width | Deliberate `35rem` application measure | Approximately `40–42rem` of usable screen content |

### Hierarchy

The existing system generally has three visibly distinct layers:

1. Global navigation.
2. Ruled page title.
3. Attached component title.

That is clear and robust, but it can become mechanical. A page headed
**Boards**, followed by a frame headed **Private boards**, followed by another
attached header for **Shared boards**, spends considerable visual weight
describing its own structure.

The wireframes flatten that hierarchy:

- Active navigation establishes the destination.
- A light label establishes the current group.
- The content itself receives most of the emphasis.

This is especially effective on Home and Boards, where the records matter more
than the page title.

The risk is that a floating label has less authority. Without disciplined
spacing and alignment, it can look like incidental metadata rather than the
heading of the following collection.

### Attached versus free-floating text

The existing system treats attachment almost as a semantic guarantee: if a
heading names some rows, it touches those rows and shares their outer frame.

The wireframes use proximity instead:

```text
Shared
[ bordered list ]
```

rather than:

```text
[ attached Shared header
  divided rows          ]
```

Both are valid, but they communicate slightly different things:

- **Attached headings** make the heading part of a component or control.
- **Floating headings** describe content at the page level.

That distinction is useful. The existing system currently uses attached
headings for both jobs.

### Spacing

The wireframes are not uniformly spacious. Their rows are still fairly dense.
The additional space is mostly **between conceptual groups**—roughly
`1.25–1.5rem`—rather than inside every record.

That is a good distinction. It makes the page calmer without turning each row
into a large dashboard card.

The existing system's connected frames minimize those pauses. This works well
for forms and settings, but can make a browse page feel like one long
administrative control.

### Cards and frames

The existing "frames, not cards" rule emphasizes relationships among records.
The wireframes allow items to appear more independently:

- Recent boards are tiles.
- Board-detail pins are individual cards.
- The unfiled destination is a standalone card.
- The selected pin owns its expanded actions.

This helps when an item has its own state or scope. For example, the distinction
between "Remove from seminar reading" and "Delete pin" benefits from being
visibly enclosed with the selected pin.

Applying this to every ordinary pin, however, would weaken list scanning and
move Cork closer to the detached-card pattern the existing system intentionally
rejected.

## Solution 1: Adapt the wireframes to the existing system

This preserves the existing hierarchy and treats the wireframes primarily as
information-architecture proposals.

### Application shell

- Add **Home**, **Boards**, and **Pins** to the existing global header.
- Keep identity and Settings at the right.
- Keep the ruled page header on every screen.
- Put `New board` and `New pin` beside the page title rather than in global
  navigation.
- Retain the `35rem` measure and current compact spacing.

### Home

Use one compound frame:

1. Attached `New since you were here` header.
2. Connected activity rows.
3. Attached `Recently active` header.
4. Recent-board rows or divided grid cells.
5. A quiet final divided row for `7 pins not on a board`.

Making the unfiled link a footer-like row preserves its intentionally low
emphasis better than giving it its own titled component.

### Filing a pin

Treat the board picker as a real anchored popover:

- The pin remains a row in its list.
- `Add to board` opens the popover.
- Search is the first connected region.
- Board options are divided rows.
- The consequence message is the final attached region.

This already fits the existing popover and compound-frame grammar very well.
Placement labels could use compact `3px`-radius tags instead of fully rounded
pills.

### Board detail

- Keep the board name in the ruled page header.
- Put sharing information in the existing page-context position.
- Use one `Pins` frame with connected pin rows.
- Show `also on N boards` as muted row metadata.
- When a pin is selected, reveal an internally divided action region inside
  that row.
- Do not give every pin its own detached card.

### Boards

This is almost exactly the existing compound-frame pattern:

- Ruled `Boards` page header with `New board`.
- One outer frame.
- Attached `Shared` header and rows.
- Attached `Private` header and rows.

The only notable content change is placing Shared first and adding
membership/new-activity metadata.

### Pins

Use one frame:

1. Attached header with total count.
2. Connected search/filter region.
3. Connected pin rows.

Filters should use compact segmented or toggle controls. Board placements appear
as small tags within each row, and `Add to board` remains the aligned row action.

### Advantages

- Very coherent with forms, settings, dialogs, and existing screens.
- Reuses nearly all current primitives.
- Preserves dense list scanning.
- Lowest implementation and regression risk.

### Disadvantages

- Home risks looking over-framed.
- Several attached headers would carry more weight than their content deserves.
- Repeating `Boards` in navigation, the page title, and a nearby section
  structure is redundant.
- It suppresses the calm, content-first character that makes the wireframes
  appealing.
- The strong page rule plus strong component rules may become visually busy as
  Cork gains more browse-oriented screens.

## Solution 2: Minimally expand the design system for the wireframes

Add a **browse-page composition** without replacing the current frame system.

### 1. Keep the existing foundations

Retain:

- Compact control and row dimensions.
- The current application shell.
- Restrained radii.
- Flat surfaces and no shadows.
- Connected frames for forms, settings, dialogs, and pickers.
- The existing typography and color hierarchy.

A slightly wider browse measure could be introduced—around `40rem`—while forms
remain at `35rem`. This would accommodate member lists, placement labels, and
right-aligned activity state without making every screen wider.

### 2. Add open section headings

Introduce a page-level section pattern:

```text
Section label
    0.4–0.5rem
Collection
    1.25–1.5rem
Next section label
```

The label:

- Aligns exactly with the collection edge.
- Remains compact and semibold.
- Has no surface or rule.
- Is much closer to its collection than to the preceding content.

This lets `Shared`, `Private`, `Recently active`, and
`New since you were here` float without becoming ambiguous.

Attached frame headers remain appropriate when the heading is part of a control
or compound transaction, such as `Details`, `Sharing`, or a board picker.

### 3. Add an open page-introduction variant

The mandatory strong page rule should become contextual:

- **Task pages**—New, Edit, Settings, and confirmation flows—retain the ruled
  page header.
- **Browse and entity pages** may use an open title with directly attached
  metadata and no strong rule.
- A primary destination may omit a redundant visible title when its active
  navigation label is sufficient.

This is the most consequential change, but it addresses the central difference
rather than merely restyling cards.

### 4. Relax "frames, not cards" with a narrow rule

Replace the absolute prohibition with:

> Collections normally share one frame. An item may receive its own boundary
> when it is independently navigable, arranged as a summary tile, or owns
> expanded item-scoped state or actions.

That allows:

- Recent-board summary tiles.
- The quiet unfiled shortcut.
- A selected pin with its removal/deletion controls.

Ordinary activity and pin lists should still use one connected frame. Detached
cards should not become the default row treatment.

### 5. Add semantic tags and filters

Fully rounded shapes can be allowed for two narrow purposes:

- Board-placement labels.
- Selected filters.

These are not buttons masquerading as pills; their shape distinguishes
many-to-many classification and transient filtering from ordinary controls.

### 6. Keep actions out of the global navigation

Do not adopt the wireframes' context-sensitive `New board`/`New pin` button
inside the site navigation. It competes with identity and Settings and becomes
crowded at the current width.

Instead:

- Place the action beside an open page title when one exists.
- Otherwise use a compact page-tools row immediately before the first section.

This preserves a stable global shell while adopting the wireframes' content
hierarchy.

### Advantages

- Preserves Cork's compact, practical character.
- Gives browse pages enough air without making forms spacious.
- Lets headings express their actual semantic level.
- Better supports new concepts such as activity groups, filters, multi-board
  placement, and item-scoped actions.
- Avoids forcing every new feature into the form-oriented compound-frame
  grammar.

### Disadvantages

- Introduces two page-header treatments and two section-heading treatments.
- Requires clear documentation to prevent arbitrary mixing.
- Detached records and pills could gradually drift toward a generic card-based
  application if their exceptions are not enforced.
- Slightly more design and implementation work than translating everything
  into existing frames.

## Evaluation and preference

**Solution 2 is preferred, with strict boundaries.**

The existing system is strongest when several regions form one control or
transaction:

- Forms.
- Board sharing.
- Settings.
- Pickers.
- Dialogs.

The wireframe system is strongest when the user is surveying several related
but distinct groups:

- Activity.
- Shared versus private boards.
- Pin-placement state.
- Recent resources.

Forcing the latter into attached headers and compound frames would preserve
consistency at the expense of information hierarchy. Conversely, moving
entirely to the wireframe system would be premature: the wireframes cover browse
interactions well, but do not yet provide an equally convincing grammar for
forms, settings, validation, authentication, and dialogs.

The governing rule should be:

> **Use physical attachment for transactional relationships; use proximity for
> descriptive relationships.**

Thus:

- `Details` attached to fields: yes.
- Picker search, options, and consequence attached together: yes.
- `Shared` describing a collection: free-floating.
- Board title with sharing metadata: free-floating.
- Ordinary pins: connected list.
- A pin with expanded item-scoped actions: locally bounded.
- Large gaps inside records: no.
- Moderate gaps between conceptual groups: yes.

This is an evolution of the current system, not a move to an entirely new one.
It keeps the established density and structural discipline while correcting the
existing tendency to make every heading and relationship equally explicit.
