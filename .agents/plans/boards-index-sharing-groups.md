# Group boards by sharing status

## Goal

Change `boards.index` so its two groups describe sharing state rather than who
created a board:

- **Private boards**: boards owned by the signed-in user with no `Share`
  records.
- **Shared boards**: accessible boards with at least one `Share` record,
  including both boards owned by the signed-in user and boards shared with
  them by another owner.

A board shared with multiple people must still appear only once. Existing
access and ownership rules remain unchanged.

## Implementation

1. Update `app/http/boards.py:index` to load the accessible boards as it does
   today, collect the IDs of boards that have any share, and partition the
   accessible boards into `private_boards` and `shared_boards`.
   - An owned board belongs in `private_boards` only when its ID has no share.
   - Every accessible board with a share belongs in `shared_boards`.
   - Pass both collections and `current_user_id` to the view.
   - Keep `find_all_accessible_boards` unchanged because the pin forms still
     need one ungrouped list of all accessible boards.
2. Update `app/views/boards/index.html` to render the two explicit collections
   rather than filtering one list by owner.
   - Rename the sections to “Private boards” and “Shared boards.”
   - Use matching empty states: “No private boards.” and “No shared boards.”
   - Preserve reverse-chronological ordering within each group.
3. Render board owner actions based on ownership rather than section.
   - Private boards always retain Edit, Sharing, and Delete actions.
   - Shared boards owned by the signed-in user retain those same actions.
   - Boards owned by someone else continue to omit owner-only actions.
   - Prefer a small template macro/shared row block so board details and the
     action markup do not diverge between the two groups.

## Verification

With at least two users, verify the index for these cases:

1. An owned board with no recipients appears only under Private boards and has
   owner actions.
2. An owned board with one or more recipients appears only under Shared boards
   and still has owner actions.
3. A board owned by another user and shared with the current user appears only
   under Shared boards and has no owner actions.
4. An inaccessible board does not appear in either group.
5. Removing the last recipient from an owned board moves it from Shared boards
   to Private boards; adding the first recipient moves it back.
6. Each group is newest-first, duplicate `Share` data cannot duplicate a board
   row, and each empty state appears when its group has no boards.
7. Board links and edit/sharing/delete workflows continue to work from their
   new section.

There is currently no project test suite, so verification is manual unless a
separate test harness is introduced.
