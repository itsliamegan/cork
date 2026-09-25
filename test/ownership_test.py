from helios.database import NotFoundError
from luna.test.assertion import assert_eq, assert_raises

from app import Board, Ownership, Pin, Share, User
from test.support import TestStore


def test_only_the_creator_owns_a_shared_board():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)

		found = Ownership(store, creator).find_board(board.id)

		assert_eq(found.id, board.id)
		with assert_raises(NotFoundError):
			Ownership(store, participant).find_board(board.id)


def test_only_the_creator_owns_a_pin():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		stranger = store.create(User, name="Stranger")
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)

		found = Ownership(store, creator).find_pin(pin.id)

		assert_eq(found.id, pin.id)
		with assert_raises(NotFoundError):
			Ownership(store, stranger).find_pin(pin.id)
