from helios.database import DatabaseError
from luna.test.assertion import assert_eq, assert_raises

from app import Access, Board, Move, Ordering, Share, User
from app.move import OutOfDate
from test.support import TestStore


def test_arrange_splits_boards_into_private_and_shared_sections():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		participant = store.create(User, name="Participant")
		other_creator = store.create(User, name="Other creator")
		private = store.create(Board, title="Private", creator_id=viewer.id)
		owned = store.create(Board, title="Owned", creator_id=viewer.id)
		received = store.create(Board, title="Received", creator_id=other_creator.id)
		store.create(Share, board_id=owned.id, user_id=participant.id)
		store.create(Share, board_id=received.id, user_id=viewer.id)

		private_boards, shared_boards = Ordering.arrange(store, Access(store, viewer))

		assert_eq(private_boards, [private])
		assert_eq(shared_boards, [received, owned])


def test_owned_private_boards_enter_their_section_when_created():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		older = store.create(Board, title="Older", creator_id=viewer.id)
		newer = store.create(Board, title="Newer", creator_id=viewer.id)

		private_boards, _ = Ordering.arrange(store, Access(store, viewer))

		assert_eq(private_boards, [newer, older])


def test_owned_shared_boards_enter_their_section_when_first_shared():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		participant = store.create(User, name="Participant")
		latecomer = store.create(User, name="Latecomer")
		first_shared = store.create(Board, title="First shared", creator_id=viewer.id)
		last_shared = store.create(Board, title="Last shared", creator_id=viewer.id)
		store.create(Share, board_id=first_shared.id, user_id=participant.id)
		store.create(Share, board_id=last_shared.id, user_id=participant.id)
		store.create(Share, board_id=first_shared.id, user_id=latecomer.id)

		_, shared_boards = Ordering.arrange(store, Access(store, viewer))

		assert_eq(shared_boards, [last_shared, first_shared])


def test_received_boards_enter_their_section_when_shared_with_the_user():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		participant = store.create(User, name="Participant")
		other_creator = store.create(User, name="Other creator")
		older = store.create(Board, title="Older", creator_id=other_creator.id)
		newer = store.create(Board, title="Newer", creator_id=other_creator.id)
		store.create(Share, board_id=newer.id, user_id=viewer.id)
		store.create(Share, board_id=older.id, user_id=viewer.id)
		store.create(Share, board_id=newer.id, user_id=participant.id)

		_, shared_boards = Ordering.arrange(store, Access(store, viewer))

		assert_eq(shared_boards, [older, newer])


def test_boards_without_a_row_come_before_boards_with_one():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		older = store.create(Board, title="Older", creator_id=viewer.id)
		newer = store.create(Board, title="Newer", creator_id=viewer.id)
		positioned = store.create(Board, title="Positioned", creator_id=viewer.id)
		store.create(Ordering, user_id=viewer.id, board_id=positioned.id, position=0)

		private_boards, _ = Ordering.arrange(store, Access(store, viewer))

		assert_eq(private_boards, [newer, older, positioned])


def test_boards_with_a_row_follow_their_positions():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		philosophy = store.create(Board, title="Philosophy", creator_id=viewer.id)
		essays = store.create(Board, title="Essays", creator_id=viewer.id)
		for position, board in enumerate([philosophy, reading, essays]):
			store.create(
				Ordering, user_id=viewer.id, board_id=board.id, position=position
			)

		private_boards, _ = Ordering.arrange(store, Access(store, viewer))

		assert_eq(private_boards, [philosophy, reading, essays])


def test_a_user_orders_each_board_once():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		store.create(Ordering, user_id=viewer.id, board_id=reading.id, position=0)

		with assert_raises(DatabaseError):
			store.create(Ordering, user_id=viewer.id, board_id=reading.id, position=1)

		assert_eq(len(store.find_all(Ordering)), 1)


def test_only_the_users_own_rows_apply():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_viewer = store.create(User, name="Other viewer")
		older = store.create(Board, title="Older", creator_id=viewer.id)
		newer = store.create(Board, title="Newer", creator_id=viewer.id)
		store.create(Ordering, user_id=other_viewer.id, board_id=newer.id, position=1)
		store.create(Ordering, user_id=other_viewer.id, board_id=older.id, position=0)

		private_boards, _ = Ordering.arrange(store, Access(store, viewer))

		assert_eq(private_boards, [newer, older])


def test_arrange_ignores_rows_for_inaccessible_boards():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		hidden = store.create(Board, title="Hidden", creator_id=other_creator.id)
		for position, board in enumerate([hidden, reading]):
			store.create(
				Ordering, user_id=viewer.id, board_id=board.id, position=position
			)

		private_boards, shared_boards = Ordering.arrange(store, Access(store, viewer))

		assert_eq(private_boards, [reading])
		assert_eq(shared_boards, [])


def test_move_writes_rows_for_the_whole_section():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		first = store.create(Board, title="First", creator_id=viewer.id)
		second = store.create(Board, title="Second", creator_id=viewer.id)
		third = store.create(Board, title="Third", creator_id=viewer.id)
		store.create(Ordering, user_id=viewer.id, board_id=first.id, position=0)
		access = Access(store, viewer)

		Ordering.move(store, access, Move(first.id, None, third.id))

		private_boards, _ = Ordering.arrange(store, access)
		assert_eq(private_boards, [first, third, second])
		positions = {
			ordering.board_id: ordering.position
			for ordering in store.find_by(Ordering, user_id=viewer.id)
		}
		assert_eq(positions, {first.id: 0, third.id: 1, second.id: 2})


def test_move_leaves_the_other_section_alone():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		participant = store.create(User, name="Participant")
		first = store.create(Board, title="First", creator_id=viewer.id)
		second = store.create(Board, title="Second", creator_id=viewer.id)
		shared = store.create(Board, title="Shared", creator_id=viewer.id)
		unarranged = store.create(Board, title="Unarranged", creator_id=viewer.id)
		for board in [shared, unarranged]:
			store.create(Share, board_id=board.id, user_id=participant.id)
		store.create(Ordering, user_id=viewer.id, board_id=shared.id, position=7)

		Ordering.move(store, Access(store, viewer), Move(first.id, None, second.id))

		positions = {
			ordering.board_id: ordering.position
			for ordering in store.find_by(Ordering, user_id=viewer.id)
		}
		assert_eq(positions, {first.id: 0, second.id: 1, shared.id: 7})


def test_move_deletes_rows_for_inaccessible_boards():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		first = store.create(Board, title="First", creator_id=viewer.id)
		second = store.create(Board, title="Second", creator_id=viewer.id)
		hidden = store.create(Board, title="Hidden", creator_id=other_creator.id)
		store.create(Ordering, user_id=viewer.id, board_id=hidden.id, position=0)

		Ordering.move(store, Access(store, viewer), Move(first.id, None, second.id))

		board_ids = {
			ordering.board_id for ordering in store.find_by(Ordering, user_id=viewer.id)
		}
		assert_eq(board_ids, {first.id, second.id})


def test_move_next_to_a_board_in_the_other_section_is_out_of_date():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		participant = store.create(User, name="Participant")
		private = store.create(Board, title="Private", creator_id=viewer.id)
		shared = store.create(Board, title="Shared", creator_id=viewer.id)
		store.create(Share, board_id=shared.id, user_id=participant.id)

		with assert_raises(OutOfDate):
			Ordering.move(
				store, Access(store, viewer), Move(private.id, None, shared.id)
			)

		assert_eq(store.find_by(Ordering, user_id=viewer.id), [])


def test_move_of_a_board_that_is_no_longer_accessible_is_out_of_date():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		hidden = store.create(Board, title="Hidden", creator_id=other_creator.id)

		with assert_raises(OutOfDate):
			Ordering.move(
				store, Access(store, viewer), Move(hidden.id, None, reading.id)
			)

		assert_eq(store.find_by(Ordering, user_id=viewer.id), [])
