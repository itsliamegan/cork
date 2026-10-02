from helios.http import URL
from luna.test.assertion import assert_eq, assert_not, assert_that

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
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=viewer.id,
		)
		newer = store.create(
			Pin,
			title="Beauvoir",
			url=URL.parse("https://plato.stanford.edu/entries/beauvoir/"),
			creator_id=viewer.id,
		)
		placed = store.create(
			Pin,
			title="Camus",
			url=URL.parse("https://plato.stanford.edu/entries/camus/"),
			creator_id=other_creator.id,
		)
		Placement.create(store, placed, board, other_creator)

		pins = Ownership(store, viewer).find_pins()

		assert_eq({pin.id for pin in pins}, {older.id, newer.id})


def test_only_the_adder_added_a_placement():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		pin_creator = store.create(User, name="Pin creator")
		adder = store.create(User, name="Adder")
		board = store.create(Board, title="Reading", creator_id=board_creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=pin_creator.id,
		)
		placement = Placement.create(store, pin, board, adder)

		assert_that(Ownership(store, adder).added(placement))
		assert_not(Ownership(store, pin_creator).added(placement))
		assert_not(Ownership(store, board_creator).added(placement))
