from helios.database import DatabaseError
from luna.test.assertion import assert_eq, assert_raises

from app import Access, Board, Ordering, Share, User
from test.support import TestStore


def test_unpositioned_boards_come_first_newest_first():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		store.create(Board, title="Older", creator_id=viewer.id)
		store.create(Board, title="Newer", creator_id=viewer.id)
		positioned = store.create(Board, title="Positioned", creator_id=viewer.id)
		store.create(Ordering, user_id=viewer.id, board_id=positioned.id, position=0)

		boards = Ordering.arrange(store, Access(store, viewer))

		assert_eq([board.title for board in boards], ["Newer", "Older", "Positioned"])


def test_positioned_boards_follow_their_positions():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		philosophy = store.create(Board, title="Philosophy", creator_id=viewer.id)
		essays = store.create(Board, title="Essays", creator_id=viewer.id)
		for position, board in enumerate([philosophy, reading, essays]):
			store.create(
				Ordering, user_id=viewer.id, board_id=board.id, position=position
			)

		boards = Ordering.arrange(store, Access(store, viewer))

		assert_eq(
			[board.title for board in boards], ["Philosophy", "Reading", "Essays"]
		)


def test_a_user_orders_each_board_once():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		store.create(Ordering, user_id=viewer.id, board_id=reading.id, position=0)

		with assert_raises(DatabaseError):
			store.create(Ordering, user_id=viewer.id, board_id=reading.id, position=1)

		assert_eq(len(store.find_all(Ordering)), 1)


def test_only_the_users_own_orderings_apply():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_viewer = store.create(User, name="Other viewer")
		older = store.create(Board, title="Older", creator_id=viewer.id)
		newer = store.create(Board, title="Newer", creator_id=viewer.id)
		store.create(Ordering, user_id=other_viewer.id, board_id=newer.id, position=0)
		store.create(Ordering, user_id=other_viewer.id, board_id=older.id, position=1)

		boards = Ordering.arrange(store, Access(store, viewer))

		assert_eq([board.title for board in boards], ["Newer", "Older"])


def test_arrange_includes_shared_boards_and_skips_inaccessible_ones():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		shared = store.create(Board, title="Shared", creator_id=other_creator.id)
		hidden = store.create(Board, title="Hidden", creator_id=other_creator.id)
		store.create(Share, board_id=shared.id, user_id=viewer.id)
		for position, board in enumerate([hidden, shared, reading]):
			store.create(
				Ordering, user_id=viewer.id, board_id=board.id, position=position
			)

		boards = Ordering.arrange(store, Access(store, viewer))

		assert_eq([board.title for board in boards], ["Shared", "Reading"])


def test_replace_orders_boards_as_given():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		philosophy = store.create(Board, title="Philosophy", creator_id=viewer.id)
		store.create(Ordering, user_id=viewer.id, board_id=reading.id, position=0)
		store.create(Ordering, user_id=viewer.id, board_id=philosophy.id, position=1)
		access = Access(store, viewer)

		Ordering.replace(store, access, [philosophy, reading])

		boards = Ordering.arrange(store, access)
		assert_eq([board.title for board in boards], ["Philosophy", "Reading"])
		assert_eq(len(store.find_by(Ordering, user_id=viewer.id)), 2)


def test_replace_leaves_other_users_orderings_alone():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_viewer = store.create(User, name="Other viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		other = store.create(
			Ordering, user_id=other_viewer.id, board_id=reading.id, position=0
		)

		Ordering.replace(store, Access(store, viewer), [])

		orderings = store.find_by(Ordering, user_id=other_viewer.id)
		assert_eq([ordering.id for ordering in orderings], [other.id])


def test_replace_refuses_duplicate_boards_without_changes():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		ordering = store.create(
			Ordering, user_id=viewer.id, board_id=reading.id, position=0
		)

		with assert_raises(ValueError):
			Ordering.replace(store, Access(store, viewer), [reading, reading])

		orderings = store.find_by(Ordering, user_id=viewer.id)
		assert_eq([stored.id for stored in orderings], [ordering.id])


def test_replace_refuses_inaccessible_boards_without_changes():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		stranger = store.create(User, name="Stranger")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		private = store.create(Board, title="Private", creator_id=stranger.id)
		ordering = store.create(
			Ordering, user_id=viewer.id, board_id=reading.id, position=0
		)

		with assert_raises(ValueError):
			Ordering.replace(store, Access(store, viewer), [reading, private])

		orderings = store.find_by(Ordering, user_id=viewer.id)
		assert_eq([stored.id for stored in orderings], [ordering.id])
