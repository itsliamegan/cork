from helios.database import NotFoundError
from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Access, Board, Pin, Placement, Share, User
from test.support import TestStore


def test_board_is_accessible_to_its_creator_and_participants_only():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		stranger = store.create(User, name="Stranger")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)

		assert_that(Access(store, creator).allows_board(board))
		assert_that(Access(store, participant).allows_board(board))
		assert_that(not Access(store, stranger).allows_board(board))


def test_find_board_hides_inaccessible_boards():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		stranger = store.create(User, name="Stranger")
		board = store.create(Board, title="Reading", creator_id=creator.id)

		found = Access(store, creator).find_board(board.id)

		assert_eq(found.id, board.id)
		with assert_raises(NotFoundError):
			Access(store, stranger).find_board(board.id)


def test_pin_is_accessible_through_any_board_it_is_placed_on():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		private = store.create(Board, title="Private", creator_id=creator.id)
		shared = store.create(Board, title="Shared", creator_id=creator.id)
		store.create(Share, board_id=shared.id, user_id=participant.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		for board in [private, shared]:
			Placement.create(store, pin, board, creator)

		found = Access(store, participant).find_pin(pin.id)

		assert_eq(found.id, pin.id)


def test_pin_is_accessible_to_the_creator_of_a_board_it_is_placed_on():
	with TestStore() as store:
		pin_creator = store.create(User, name="Pin creator")
		board_creator = store.create(User, name="Board creator")
		board = store.create(Board, title="Reading", creator_id=board_creator.id)
		store.create(Share, board_id=board.id, user_id=pin_creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=pin_creator.id,
		)
		Placement.create(store, pin, board, pin_creator)

		allowed = Access(store, board_creator).allows_pin(pin)

		assert_that(allowed)


def test_pin_is_inaccessible_to_users_without_a_placed_board():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		stranger = store.create(User, name="Stranger")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		filed = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		unfiled = store.create(
			Pin,
			title="Beauvoir",
			url="https://plato.stanford.edu/entries/beauvoir/",
			creator_id=creator.id,
		)
		Placement.create(store, filed, board, creator)
		access = Access(store, stranger)

		assert_that(not access.allows_pin(filed))
		assert_that(not access.allows_pin(unfiled))
		with assert_raises(NotFoundError):
			access.find_pin(filed.id)


def test_unfiled_pin_is_accessible_to_its_creator():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)

		allowed = Access(store, creator).allows_pin(pin)

		assert_that(allowed)


def test_find_boards_returns_created_and_shared_boards():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		created = store.create(Board, title="Created", creator_id=viewer.id)
		shared = store.create(Board, title="Shared", creator_id=other_creator.id)
		store.create(Board, title="Private", creator_id=other_creator.id)
		store.create(Share, board_id=shared.id, user_id=viewer.id)

		boards = Access(store, viewer).find_boards()

		assert_eq({board.id for board in boards}, {created.id, shared.id})


def test_find_board_ids_covers_created_and_shared_boards():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		created = store.create(Board, title="Created", creator_id=viewer.id)
		shared = store.create(Board, title="Shared", creator_id=other_creator.id)
		store.create(Board, title="Private", creator_id=other_creator.id)
		store.create(Share, board_id=shared.id, user_id=viewer.id)

		board_ids = Access(store, viewer).find_board_ids()

		assert_eq(sorted(board_ids), sorted([created.id, shared.id]))
