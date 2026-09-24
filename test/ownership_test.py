from helios.database import NotFoundError
from luna.test.assertion import assert_eq, assert_raises

from app import Board, Ownership, Pin, Share, User
from test.support import TestStore


def test_only_the_creator_owns_a_shared_board():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		bob = store.create(User, name="Bob")
		board = store.create(Board, title="Reading", creator_id=alice.id)
		store.create(Share, board_id=board.id, user_id=bob.id)

		found = Ownership(store, alice).find_board(board.id)

		assert_eq(found.id, board.id)
		with assert_raises(NotFoundError):
			Ownership(store, bob).find_board(board.id)


def test_only_the_creator_owns_a_pin():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		bob = store.create(User, name="Bob")
		pin = store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=alice.id
		)

		found = Ownership(store, alice).find_pin(pin.id)

		assert_eq(found.id, pin.id)
		with assert_raises(NotFoundError):
			Ownership(store, bob).find_pin(pin.id)
