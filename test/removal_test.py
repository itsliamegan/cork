from luna.test.assertion import assert_eq

from app import Board, Pin, Placement, Removal, Share, User
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
			Pin, title="Sartre", url="https://example.com", creator_id=pin_creator.id
		)
		placement = Placement.create(store, pin, board, adder)
		removal = Removal(placement, pin, board)

		authorized = [
			removal.is_authorized(store, user)
			for user in [pin_creator, adder, board_creator, participant]
		]

		assert_eq(authorized, [True, True, True, False])


def test_adder_without_current_board_access_may_not_remove_a_placement():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		former_adder = store.create(User, name="Former adder")
		board = store.create(Board, title="Reading", creator_id=owner.id)
		pin = store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=owner.id
		)
		placement = Placement.create(store, pin, board, former_adder)

		authorized = Removal(placement, pin, board).is_authorized(store, former_adder)

		assert_eq(authorized, False)
