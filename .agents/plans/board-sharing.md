# Board sharing

## Goal

Allow a board's creator to share it with other users. Everyone with access to a
board can view it and post pins, while only each record's creator can edit or
delete that record.

## Data model

1. Add a `Share` model containing `board_id` and `user_id`, where `user_id`
   identifies the recipient.
2. Register `Share` in the store schema.
3. Treat `Board.user_id` as the board creator and `Pin.user_id` as the pin
   creator; do not duplicate the board creator on `Share`.
4. Enforce in application code that a user cannot share a board with themselves
   or create a duplicate share.

## Board access

1. Add helpers that distinguish ownership from access:
   - Owned boards have `Board.user_id` matching the signed-in user.
   - Accessible boards are either owned by the user or connected to them through
     a `Share`.
2. Continue requiring ownership to edit or delete a board and to manage its
   shares.
3. Allow any user with access to view a board and open its new-pin form.
4. List both owned and shared boards on the boards index, with enough view
   context to distinguish them and hide owner-only actions.

## Pin access

1. Load every pin belonging to an accessible board, regardless of who created
   the pin.
2. Allow a user to create a pin on any accessible board, recording that user as
   `Pin.user_id`.
3. Include all accessible boards in new/edit pin board selectors.
4. Continue requiring `Pin.user_id` to match the signed-in user before editing,
   moving, or deleting a pin.
5. Only render pin edit/delete controls for the pin's creator.

## Sharing workflow

1. Add routes and handlers for viewing a board's shares, creating a share, and
   removing a share.
2. Require board ownership in every sharing handler.
3. Provide an owner-only sharing page that lists current recipients and users
   who can be added.
4. Validate the board, recipient, self-sharing restriction, and duplicate
   restriction before creating a share.
5. Allow the owner to revoke an existing share without affecting pins previously
   created by that user.

## Deletion behavior

1. When deleting a board, delete all of its shares.
2. Delete all pins on the board, including pins created by shared users, before
   deleting the board.
3. Update the board deletion confirmation to make this consequence clear.

## Verification

1. Verify owners can view, edit, delete, and share their boards.
2. Verify recipients can view shared boards and add pins to them.
3. Verify recipients cannot edit, delete, or manage sharing for shared boards.
4. Verify users can edit or delete only their own pins, including on shared
   boards.
5. Verify unrelated users cannot view or post to a board.
6. Verify self-shares and duplicate shares are rejected.
7. Verify revoking access removes the board from the recipient's index without
   deleting their existing pins.
8. Verify deleting a board removes its shares and all associated pins.
