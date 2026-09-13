# Cork: User Interface and Data Model Overview

Cork is a small, multi-user web application for saving URLs as **pins** and organizing them into **boards**. Boards can remain private or be shared with other Cork users. The interface is server-rendered, with Turbo used for navigation and a small Stimulus controller used for drag-and-drop board ordering.

## User interfaces

### Sign in

The sign-in screen presents a list of existing users. A person selects their name to enter Cork; there is no username/password flow or user-management interface.

All other screens require a signed-in user. The persistent application header identifies that user and links to **Boards** and **Settings**.

### Board list

The Boards screen is Cork's main landing page. It divides every board available to the current user into two groups:

- **Private boards**: boards owned by the user and not shared with anyone.
- **Shared boards**: accessible boards that have been shared, including the user's own shared boards and boards shared with them.

Each board entry shows its title and creation date. Users can drag boards to reorder them within a group; Cork saves a separate ordering for each user. Owners also receive actions to edit sharing or delete a board. A prominent action opens the new-board form.

### Creating and managing boards

The new-board form asks for a title and optionally lets the creator share the board with any existing users. The creator is shown as its owner.

A board owner can later edit its title and sharing selections. Only the owner can edit or delete the board. Deletion is confirmed in a dialog and also removes the board's pins, shares, and saved user orderings.

### Board detail

A board's detail screen lists its pins newest first. Each entry displays:

- the pin title and external URL;
- the date it was saved;
- a link to Cork's pin-details screen.

Anyone with access to the board can view it and add a new pin. Only a pin's creator sees controls to edit or delete that pin. The board owner alone sees the board-edit action.

### Creating and editing pins

The pin form captures a title, URL, board, and optional free-text note. The board selector contains all boards accessible to the current user, so a new pin can be placed on an owned or shared board.

A pin's creator can edit its title, URL, note, and board assignment, or delete it. Moving a pin is limited to boards that creator can access. Pins are currently assigned to one board at a time.

### Pin detail

The pin-details screen shows the external URL, creator, creation date, and note, with a link back to its board. The current user's preference determines whether external pin links open in the same tab or a new one.

### Settings

The Settings screen shows the current identity and provides:

- a sign-out action, which returns to the user chooser;
- a preference for opening external pin links in a new tab.

## Permissions and collaboration

Cork distinguishes ownership from access:

- A **board owner** can view, rename, share, and delete the board.
- A user with a **share** can view the board and add pins to it, but cannot edit the board itself.
- A **pin creator** can edit, move, and delete that pin, even when it is on another user's shared board.
- Other users with access to the board can view the pin but cannot modify it.

Unauthorized resources are treated as not found rather than displayed as forbidden.

## Data model

Every stored model has a UUID `id` and a `created_at` timestamp supplied by Helios.

### User

Represents a person who can sign in.

- `name`: display name.
- `open_in_new_tab`: whether external pin links should open in a separate tab; defaults to false.

### Board

Represents a named collection of pins.

- `title`: board name.
- `user_id`: the owning User.

A board is private when it has no Share records. Its owner can grant access to one or more other users.

### Pin

Represents a saved external resource.

- `url`: external URL.
- `title`: display title.
- `note`: optional text, stored as an empty string by default.
- `board_id`: the containing Board; nullable in the schema, though current UI workflows require a board.
- `user_id`: the User who created and owns the pin.

The pin's creator and the board's owner may be different people.

### Share

Grants one user access to one board.

- `board_id`: shared Board.
- `user_id`: User receiving access.

A Share is a join record rather than a separate user-facing object. Board ownership itself does not require a Share record.

### Ordering

Stores a user's preferred board order.

- `user_id`: User whose preference this is.
- `board_id`: accessible Board being positioned.
- `position`: zero-based position in that user's ordering.

Orderings do not change board ownership or sharing. Each user can arrange the same set of shared boards differently. Accessible boards without a stored position appear before positioned boards, newest first.

## Relationship summary

```text
User 1 ── owns ── * Board
User 1 ── creates ── * Pin
Board 1 ── contains ── * Pin
User * ── accesses ── * Board     (through Share)
User * ── orders ── * Board       (through Ordering)
```

The current structure is a single-level organization model: a pin belongs to at most one board, and boards do not contain other boards.

## Persistence

Application records are stored together in `data/store.json`. Session records are stored separately in `data/sessions.json`. Helios loads the JSON store for each request and writes it back afterward; Cork does not use a relational database, transactions, or database-enforced foreign keys.
