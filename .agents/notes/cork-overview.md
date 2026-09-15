# Cork: User Interface and Data Model Overview

Cork is a small, multi-user web application for saving URLs as **pins** and organizing them into **boards**. Boards can remain private or be shared with other Cork users. The interface is server-rendered, with Turbo used for navigation and small Stimulus controllers for interaction.

## User interfaces

### Sign in and navigation

The sign-in screen presents the existing users. A person selects their name to enter Cork; there is no username/password flow or user-management interface.

All other screens require a signed-in user. The persistent header identifies that user and links to **Boards**, **Pins**, and **Settings**. The application root continues to open Boards.

### Boards

The Boards index divides every board available to the current user into private and shared groups. Users can drag boards to save their own ordering. Owned rows have an overflow menu with Edit and Delete actions.

A board owner can edit its title and sharing selections. Deleting a board removes its Placements, Shares, and saved Orderings, but never deletes Pins. The confirmation explains that its Pins remain in Pins and on any other Boards.

A Board detail page lists one draggable row for each Placement. Placements are ordered by their explicit saved order, with reverse chronology breaking ties. Anyone with Board access can reorder the rows, view the Board, and create a Pin with that Board preselected. A permitted row action removes only that Placement and leaves the Pin in the canonical Pins collection and on its other Boards.

### Pins

The Pins index is the canonical collection of every Pin created by the signed-in user. It does not include Pins merely visible through somebody else's shared Board. Rows show the compact external URL, date, and a total Board count without exposing Board titles. The index provides View, Edit, and Delete actions and an entry point for creating a Pin without selecting a Board.

The complete owned collection is rendered initially without pagination. A client-side search filters rows immediately by Pin title, complete URL, or note; it does not search Board titles or other presentation text. An empty collection and a search with no matches have distinct states, and every Pin remains available when JavaScript is disabled.

A Pin records a title, URL, optional note, and creator independently of its Placements. It may appear on zero, one, or several Boards. The Board-context creation form preselects its Board; the canonical creation form starts with no selection. Editing reconciles Placements on Boards the creator can currently access and preserves Placements on unavailable Boards.

The Pin details screen shows its URL, creator, creation date, note, and accessible Boards. A contextual **Added by** value is shown only when there is an accessible Placement. Truly unfiled Pins say `Not on any boards`; unavailable Board names are never disclosed. The current user's preference determines whether external links open in the same tab or a new one.

Deleting a Pin is creator-only and removes all of its Placements before removing the Pin. The Delete action lives in the Pins index overflow menu, not on the edit page or in Board rows.

### Settings

Settings provides sign out and the preference for opening external Pin links in a new tab.

## Permissions and collaboration

Cork distinguishes ownership from access:

- A **Board creator** can view, rename, share, and delete the Board.
- A user with a **Share** can view the Board and add Pins to it, but cannot edit the Board.
- A **Pin creator** can access and edit their Pin even when it is unfiled or all its Placements are on unavailable Boards.
- A non-creator can access a Pin only through a Placement on a Board they can access.
- A Placement may be removed only by its Pin creator, Placement adder, or Board creator, and that person must still be able to access the Board.
- Only a Pin creator can delete the Pin globally.

Unauthorized resources and actions are treated as not found rather than forbidden.

## Data model

Every stored model has a UUID `id` and a `created_at` timestamp supplied by Helios.

### User

- `name`: display name.
- `open_in_new_tab`: external-link preference.

### Board

- `title`: Board name.
- `creator_id`: owning User.

A Board is private when it has no Share records.

### Pin

- `url`: external URL.
- `title`: display title.
- `note`: optional text, stored as an empty string by default.
- `creator_id`: creating and owning User.

### Placement

Joins one Pin to one Board. A Pin may have any number of Placements, including none, but a given Pin and Board may have only one Placement. Placement creation rejects an existing Pin/Board pair.

- `pin_id`: placed Pin.
- `board_id`: containing Board.
- `adder_id`: User who created the Placement.
- `order`: zero-based display order on its Board; defaults to zero.

### Share

- `board_id`: shared Board.
- `user_id`: User receiving access.

### Ordering

- `user_id`: User whose preference this is.
- `board_id`: accessible Board being positioned.
- `position`: zero-based position.

## Relationship summary

```text
User 1 ── creates ── * Board
User 1 ── creates ── * Pin
Pin   1 ── has ── 0..* Placement * ── belongs to ── 1 Board
User  1 ── adds ── 0..* Placement
User  * ── accesses ── * Board       (through Share)
User  * ── orders ── * Board         (through Ordering)
```

## Persistence

Application records are stored together in `data/store.json`. Session records are stored separately in `data/sessions.json`. Helios loads the JSON store for each request and writes it back afterward; Cork does not use a relational database, transactions, or database-enforced foreign keys.
