from luna.test.assertion import assert_that

from app import Access, Board, Pin, Placement, Removal, Share, User
from test.support import TestStore


def test_pin_creator_adder_and_board_creator_may_remove_a_placement():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		pin_creator = store.create(User, name="Pin creator")
		adder = store.create(User, name="Adder")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=board_creator.id)
		for user in [pin_creator, adder, participant]:
			store.create(Share, board_id=board.id, user_id=user.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=pin_creator.id,
		)
		placement = Placement.create(store, pin, board, adder)
		removal = Removal(placement, pin, board)

		assert_that(removal.is_authorized(Access(store, pin_creator)))
		assert_that(removal.is_authorized(Access(store, adder)))
		assert_that(removal.is_authorized(Access(store, board_creator)))
		assert_that(not removal.is_authorized(Access(store, participant)))


def test_adder_without_current_board_access_may_not_remove_a_placement():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		former_adder = store.create(User, name="Former adder")
		board = store.create(Board, title="Reading", creator_id=board_creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=board_creator.id,
		)
		placement = Placement.create(store, pin, board, former_adder)

		access = Access(store, former_adder)

		authorized = Removal(placement, pin, board).is_authorized(access)

		assert_that(not authorized)
