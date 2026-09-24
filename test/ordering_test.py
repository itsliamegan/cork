from helios.database import DatabaseError
from luna.test.assertion import assert_eq, assert_raises

from app import Board, Ordering, User
from test.support import TestStore


def test_unpositioned_boards_come_first_newest_first():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		older = store.create(Board, title="Older", creator_id=alice.id)
		newer = store.create(Board, title="Newer", creator_id=alice.id)
		positioned = store.create(Board, title="Positioned", creator_id=alice.id)
		store.create(Ordering, user_id=alice.id, board_id=positioned.id, position=0)

		boards = Ordering.arrange(store, alice, [older, positioned, newer])

		assert_eq([board.title for board in boards], ["Newer", "Older", "Positioned"])


def test_positioned_boards_follow_their_positions():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		reading = store.create(Board, title="Reading", creator_id=alice.id)
		philosophy = store.create(Board, title="Philosophy", creator_id=alice.id)
		essays = store.create(Board, title="Essays", creator_id=alice.id)
		for position, board in enumerate([philosophy, reading, essays]):
			store.create(
				Ordering, user_id=alice.id, board_id=board.id, position=position
			)

		boards = Ordering.arrange(store, alice, [reading, philosophy, essays])

		assert_eq(
			[board.title for board in boards], ["Philosophy", "Reading", "Essays"]
		)


def test_a_user_orders_each_board_once():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		reading = store.create(Board, title="Reading", creator_id=alice.id)
		store.create(Ordering, user_id=alice.id, board_id=reading.id, position=0)

		with assert_raises(DatabaseError):
			store.create(Ordering, user_id=alice.id, board_id=reading.id, position=1)

		assert_eq(len(store.find_all(Ordering)), 1)


def test_only_the_users_own_orderings_apply():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		bob = store.create(User, name="Bob")
		older = store.create(Board, title="Older", creator_id=alice.id)
		newer = store.create(Board, title="Newer", creator_id=alice.id)
		store.create(Ordering, user_id=bob.id, board_id=newer.id, position=0)
		store.create(Ordering, user_id=bob.id, board_id=older.id, position=1)

		boards = Ordering.arrange(store, alice, [older, newer])

		assert_eq([board.title for board in boards], ["Newer", "Older"])


def test_orderings_for_boards_not_given_are_ignored():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		reading = store.create(Board, title="Reading", creator_id=alice.id)
		hidden = store.create(Board, title="Hidden", creator_id=alice.id)
		store.create(Ordering, user_id=alice.id, board_id=hidden.id, position=0)

		boards = Ordering.arrange(store, alice, [reading])

		assert_eq([board.title for board in boards], ["Reading"])
