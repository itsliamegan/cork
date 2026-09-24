from helios.database import NotFoundError
from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Access, Board, Pin, Placement, Share, User
from test.support import TestStore


def test_board_is_open_to_its_creator_and_shared_users():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		bob = store.create(User, name="Bob")
		eve = store.create(User, name="Eve")
		board = store.create(Board, title="Reading", creator_id=alice.id)
		store.create(Share, board_id=board.id, user_id=bob.id)

		allowed = [
			Access(store, user).allows_board(board) for user in [alice, bob, eve]
		]

		assert_eq(allowed, [True, True, False])


def test_find_board_hides_inaccessible_boards():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		eve = store.create(User, name="Eve")
		board = store.create(Board, title="Reading", creator_id=alice.id)

		found = Access(store, alice).find_board(board.id)

		assert_eq(found.id, board.id)
		with assert_raises(NotFoundError):
			Access(store, eve).find_board(board.id)


def test_pin_is_open_through_any_board_it_is_placed_on():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		bob = store.create(User, name="Bob")
		private = store.create(Board, title="Private", creator_id=alice.id)
		shared = store.create(Board, title="Shared", creator_id=alice.id)
		store.create(Share, board_id=shared.id, user_id=bob.id)
		pin = store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=alice.id
		)
		for board in [private, shared]:
			Placement.create(store, pin, board, alice)

		found = Access(store, bob).find_pin(pin.id)

		assert_eq(found.id, pin.id)


def test_pin_is_open_to_the_creator_of_a_board_it_is_placed_on():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		bob = store.create(User, name="Bob")
		board = store.create(Board, title="Reading", creator_id=bob.id)
		store.create(Share, board_id=board.id, user_id=alice.id)
		pin = store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=alice.id
		)
		Placement.create(store, pin, board, alice)

		allowed = Access(store, bob).allows_pin(pin)

		assert_that(allowed)


def test_pin_is_hidden_from_users_without_a_placed_board():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		eve = store.create(User, name="Eve")
		board = store.create(Board, title="Reading", creator_id=alice.id)
		filed = store.create(
			Pin, title="Filed", url="https://example.com", creator_id=alice.id
		)
		unfiled = store.create(
			Pin, title="Unfiled", url="https://example.org", creator_id=alice.id
		)
		Placement.create(store, filed, board, alice)
		access = Access(store, eve)

		allowed = [access.allows_pin(filed), access.allows_pin(unfiled)]

		assert_eq(allowed, [False, False])
		with assert_raises(NotFoundError):
			access.find_pin(filed.id)


def test_unfiled_pin_is_open_to_its_creator():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		pin = store.create(
			Pin, title="Unfiled", url="https://example.com", creator_id=alice.id
		)

		allowed = Access(store, alice).allows_pin(pin)

		assert_that(allowed)


def test_find_boards_returns_owned_and_shared_boards():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		bob = store.create(User, name="Bob")
		owned = store.create(Board, title="Owned", creator_id=alice.id)
		shared = store.create(Board, title="Shared", creator_id=bob.id)
		store.create(Board, title="Private", creator_id=bob.id)
		store.create(Share, board_id=shared.id, user_id=alice.id)

		boards = Access(store, alice).find_boards()

		assert_eq({board.id for board in boards}, {owned.id, shared.id})
