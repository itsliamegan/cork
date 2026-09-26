from luna.test.assertion import assert_eq, assert_that

from app import Board, Share, User
from test.support import TestStore


def test_exists_only_for_the_user_a_board_is_shared_with():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		stranger = store.create(User, name="Stranger")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		other = store.create(Board, title="Essays", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)

		assert_that(Share.exists(store, board, participant))
		assert_that(not Share.exists(store, other, participant))
		assert_that(not Share.exists(store, board, stranger))


def test_exists_is_false_for_the_creator_of_an_unshared_board():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		board = store.create(Board, title="Reading", creator_id=creator.id)

		shared = Share.exists(store, board, creator)

		assert_that(not shared)


def test_find_board_ids_returns_only_boards_shared_with_the_user():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		store.create(Board, title="Created", creator_id=viewer.id)
		reading = store.create(Board, title="Reading", creator_id=other_creator.id)
		essays = store.create(Board, title="Essays", creator_id=other_creator.id)
		store.create(Board, title="Private", creator_id=other_creator.id)
		for board in [reading, essays]:
			store.create(Share, board_id=board.id, user_id=viewer.id)

		board_ids = Share.find_board_ids(store, viewer)

		assert_eq(sorted(board_ids), sorted([reading.id, essays.id]))


def test_find_boards_returns_only_boards_shared_with_the_user():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		store.create(Board, title="Created", creator_id=viewer.id)
		shared = store.create(Board, title="Shared", creator_id=other_creator.id)
		store.create(Board, title="Private", creator_id=other_creator.id)
		store.create(Share, board_id=shared.id, user_id=viewer.id)

		boards = Share.find_boards(store, viewer)

		assert_eq([board.id for board in boards], [shared.id])
