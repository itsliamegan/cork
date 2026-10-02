from helios.database import NotFoundError
from helios.http import URL
from luna.test.assertion import assert_eq, assert_raises

from app import Access, Archival, Board, Pin, Placement, Share, User
from test.support import TestStore


def test_board_is_accessible_to_its_creator_and_participants_only():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		stranger = store.create(User, name="Stranger")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)

		found_by_creator = Access(store, creator).find_board(board.id)
		found_by_participant = Access(store, participant).find_board(board.id)

		assert_eq(found_by_creator.id, board.id)
		assert_eq(found_by_participant.id, board.id)
		with assert_raises(NotFoundError):
			Access(store, stranger).find_board(board.id)


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
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
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
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=pin_creator.id,
		)
		Placement.create(store, pin, board, pin_creator)

		found = Access(store, board_creator).find_pin(pin.id)

		assert_eq(found.id, pin.id)


def test_pin_is_inaccessible_to_users_without_a_placed_board():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		stranger = store.create(User, name="Stranger")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		filed = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=creator.id,
		)
		unfiled = store.create(
			Pin,
			title="Beauvoir",
			url=URL.parse("https://plato.stanford.edu/entries/beauvoir/"),
			creator_id=creator.id,
		)
		Placement.create(store, filed, board, creator)
		access = Access(store, stranger)

		with assert_raises(NotFoundError):
			access.find_pin(filed.id)
		with assert_raises(NotFoundError):
			access.find_pin(unfiled.id)


def test_unfiled_pin_is_accessible_to_its_creator():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=creator.id,
		)

		found = Access(store, creator).find_pin(pin.id)

		assert_eq(found.id, pin.id)


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


def test_find_placement_returns_placements_on_owned_and_shared_boards():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		owned = store.create(Board, title="Owned", creator_id=viewer.id)
		shared = store.create(Board, title="Shared", creator_id=other_creator.id)
		store.create(Share, board_id=shared.id, user_id=viewer.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=other_creator.id,
		)
		on_owned = Placement.create(store, pin, owned, viewer)
		on_shared = Placement.create(store, pin, shared, other_creator)
		access = Access(store, viewer)

		found_on_owned = access.find_placement(on_owned.id)
		found_on_shared = access.find_placement(on_shared.id)

		assert_eq(found_on_owned.id, on_owned.id)
		assert_eq(found_on_shared.id, on_shared.id)


def test_find_placement_hides_placements_on_unseen_boards():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		former_adder = store.create(User, name="Former adder")
		stranger = store.create(User, name="Stranger")
		board = store.create(Board, title="Reading", creator_id=board_creator.id)
		Share.replace(store, board, [former_adder])
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=board_creator.id,
		)
		placement = Placement.create(store, pin, board, former_adder)
		Share.replace(store, board, [])

		with assert_raises(NotFoundError):
			Access(store, stranger).find_placement(placement.id)
		with assert_raises(NotFoundError):
			Access(store, former_adder).find_placement(placement.id)


def test_find_archival_returns_the_users_own_archival():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=owner.id)
		store.create(Share, board_id=board.id, user_id=participant.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=owner.id,
		)
		placement = Placement.create(store, pin, board, owner)
		archival = Archival.create(store, placement, participant)

		found = Access(store, participant).find_archival(archival.id)

		assert_eq(found.id, archival.id)


def test_find_archival_hides_another_users_archival():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=owner.id)
		store.create(Share, board_id=board.id, user_id=participant.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=owner.id,
		)
		placement = Placement.create(store, pin, board, owner)
		archival = Archival.create(store, placement, participant)

		with assert_raises(NotFoundError):
			Access(store, owner).find_archival(archival.id)


def test_find_archival_hides_own_archival_on_a_board_no_longer_shared():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=owner.id)
		Share.replace(store, board, [participant])
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=owner.id,
		)
		placement = Placement.create(store, pin, board, owner)
		archival = Archival.create(store, placement, participant)
		Share.replace(store, board, [])

		with assert_raises(NotFoundError):
			Access(store, participant).find_archival(archival.id)
