from luna.test.assertion import assert_eq

from app import Board, Ownership, Pin, Placement, Share, User
from test.support import TestStore


def test_find_boards_returns_only_created_boards():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		created = store.create(Board, title="Created", creator_id=viewer.id)
		shared = store.create(Board, title="Shared", creator_id=other_creator.id)
		store.create(Share, board_id=shared.id, user_id=viewer.id)

		boards = Ownership(store, viewer).find_boards()

		assert_eq([board.id for board in boards], [created.id])


def test_find_pins_returns_only_created_pins():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		board = store.create(Board, title="Reading", creator_id=viewer.id)
		older = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=viewer.id,
		)
		newer = store.create(
			Pin,
			title="Beauvoir",
			url="https://plato.stanford.edu/entries/beauvoir/",
			creator_id=viewer.id,
		)
		placed = store.create(
			Pin,
			title="Camus",
			url="https://plato.stanford.edu/entries/camus/",
			creator_id=other_creator.id,
		)
		Placement.create(store, placed, board, other_creator)

		pins = Ownership(store, viewer).find_pins()

		assert_eq({pin.id for pin in pins}, {older.id, newer.id})
