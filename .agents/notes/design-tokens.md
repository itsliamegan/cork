# Design-token decisions

## Direction

The compact header/frame direction is working. Preserve the restrained, practical workbench character: hierarchy should primarily come from rules, alignment, surfaces, and muted metadata rather than pervasive bold type or large controls.

- Use bold for the brand, page title, frame/section titles, and item titles.
- Compact buttons are appropriate. Their visual lightness should be balanced with a medium/semibold button weight, rather than larger padding.
- Keep Cork's palette functional, not decorative.

## Token layers

Use three layers, from primitive to semantic to component-specific usage.

1. **Primitives** describe a value family and are normally numeric: spacing, type, weights, rules, radii, measures, and palette ramps.
2. **Semantic tokens** describe purpose: canvas, muted text, action, page gutter, and so on.
3. **Component tokens** are only useful when a reusable component has a deliberate, distinct decision. Do not create them for isolated values.

Leave an isolated literal local until it repeats or represents a named system decision.

## Numeric primitives

Keep a compact numeric scale for:

```css
--space-1 … --space-9
--type-1 … --type-7
--weight-regular
--weight-semibold
--weight-bold
--rule-1
--rule-2
--rule-3
--radius-0
--radius-1
--measure-1
--measure-2
```

A useful compact type rhythm is approximately a 1.125 ratio around `1rem`:

```css
--type-1: 0.70rem;
--type-2: 0.79rem;
--type-3: 0.89rem;
--type-4: 1rem;
--type-5: 1.125rem;
--type-6: 1.27rem;
--type-7: 1.42rem;
```

Use only the steps that solve a real role. Small optical adjustments (for example, a `1.45rem` page title) are acceptable when the intended hierarchy calls for them.

## Palette primitives and semantic colors

Because Cork defines its own palette, use small numeric color ramps before semantic assignments. Cork only needs a neutral ramp plus action-blue and danger-red ramps—not a broad decorative palette.

```css
/* Palette primitives */
--neutral-0: #fff;
--neutral-50: #f1f1f1;
--neutral-200: #d5d5d5;
--neutral-400: #999;
--neutral-500: #888;
--neutral-650: #626262;
--neutral-950: #111;

--blue-700: #0f61a9;
--blue-800: #0b477c;
--red-700: #9b1c1c;
--red-800: #751616;

/* Semantic roles */
--color-canvas: var(--neutral-0);
--color-surface: var(--neutral-50);
--color-surface-control: var(--neutral-0);
--color-text: var(--neutral-950);
--color-text-muted: var(--neutral-650);
--color-text-on-action: var(--neutral-0);
--color-border-quiet: var(--neutral-200);
--color-border-default: var(--neutral-400);
--color-border-control: var(--neutral-500);
--color-action: var(--blue-700);
--color-border-action: var(--blue-800);
--color-danger: var(--red-700);
--color-border-danger: var(--red-800);
```

Also provide `--color-focus`, `--color-backdrop`, and, when needed, distinct link and visited-link roles. Dark mode should remap semantic roles to palette primitives, leaving component CSS unchanged.

Use emphasis adjectives consistently:

- **muted** is secondary content, especially text.
- **quiet** is low-emphasis structural separation, especially dividers.
- **strong** is an intentionally emphatic structural boundary.
- **default** is an ordinary baseline state.
- **action** and **danger** express functional intent.

Do not use `muted` and `quiet` interchangeably. If `strong` is used, it must be visibly stronger than default/control borders; otherwise name the role specifically, such as `--color-border-frame`.

## Names and component families

Primitive names describe the value family; semantic names describe what a value is for.

- `control` is a clear shared family for buttons, inputs, selects, and textareas: `--radius-control`, `--padding-control-block`, and `--color-border-control` are good names when those controls deliberately share the value.
- `component` is too broad for token names. Prefer the structural role: `--font-size-frame-title`, `--rule-frame-header`, or `--rule-section-header`.
- A **frame** is the specific in-page connected structural primitive.
- **panel** can describe the bounded-surface family shared by frames, popovers, and dialogs, e.g. `--radius-panel`.
- An **overlay** is a layered panel, e.g. `--color-surface-overlay`, `--color-border-overlay`, and `--color-backdrop`.
- Use dialog/popover-specific tokens when their treatments really differ, such as `--rule-dialog` or `--rule-popover`.

Prefer category order in color token names: `--color-border-action`, not `--color-action-border`.

## Current implementation follow-ups

- Use existing global decisions instead of parallel literals: `--measure-app`, `--page-gutter`, `--height-site-header`, and control/frame padding aliases should either be applied consistently or removed.
- Replace the duplicate `--page-width` with a width derived from application measure and gutter:

```css
width: min(var(--measure-app), calc(100% - 2 * var(--page-gutter)));
```

- Avoid ad-hoc shared values such as the current `3.2rem` header height when `--height-site-header` exists; the accepted direction calls for approximately `2.8rem`.
- Keep one-off values such as a single icon sizing literal local until they become a genuine shared decision.
- Add a visible focus treatment and complete dark-mode semantic overrides before migrating more screens.
