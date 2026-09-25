from luna.test.assertion import assert_eq

from app import Board, Ordering, Pin, Placement, Share, User
from test.support import TestStore


def test_deleting_board_removes_placements_shares_and_orderings():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		Placement.create(store, pin, board, creator)
		store.create(Share, board_id=board.id, user_id=participant.id)
		store.create(Ordering, user_id=creator.id, board_id=board.id, position=0)

		store.delete(board)

		assert_eq(store.find_all(Placement), [])
		assert_eq(store.find_all(Share), [])
		assert_eq(store.find_all(Ordering), [])
		assert_eq([stored.id for stored in store.find_all(Pin)], [pin.id])


def test_deleting_board_keeps_placements_on_other_boards():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		reading = store.create(Board, title="Reading", creator_id=creator.id)
		essays = store.create(Board, title="Essays", creator_id=creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		Placement.create(store, pin, reading, creator)
		kept = Placement.create(store, pin, essays, creator)

		store.delete(reading)

		assert_eq([placement.id for placement in store.find_all(Placement)], [kept.id])
		assert_eq([stored.id for stored in store.find_all(Pin)], [pin.id])
