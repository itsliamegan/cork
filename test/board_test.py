from helios.http import URL
from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Access, Board, Ordering, Pin, Placement, Share, User
from app.access import NotPermitted
from test.support import TestStore


def test_deleting_board_removes_placements_shares_and_orderings():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
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
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=creator.id,
		)
		Placement.create(store, pin, reading, creator)
		kept = Placement.create(store, pin, essays, creator)

		store.delete(reading)

		assert_eq([placement.id for placement in store.find_all(Placement)], [kept.id])
		assert_eq([stored.id for stored in store.find_all(Pin)], [pin.id])


def test_only_the_creator_may_edit_or_delete_a_board():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)

		assert_that(board.is_editable_by(Access(store, creator)))
		assert_that(board.is_deletable_by(Access(store, creator)))
		assert_that(not board.is_editable_by(Access(store, participant)))
		assert_that(not board.is_deletable_by(Access(store, participant)))


def test_creator_edits_a_board_and_its_shares():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		former_participant = store.create(User, name="Former participant")
		new_participant = store.create(User, name="New participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=former_participant.id)

		board.edit(
			store,
			Access(store, creator),
			title="Philosophy",
			users=[new_participant],
		)

		assert_eq(store.find_one(Board, board.id).title, "Philosophy")
		assert_eq(
			[share.user_id for share in store.find_by(Share, board_id=board.id)],
			[new_participant.id],
		)


def test_participant_may_not_edit_a_board():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)

		with assert_raises(NotPermitted):
			board.edit(
				store,
				Access(store, participant),
				title="Philosophy",
				users=[],
			)

		assert_eq(store.find_one(Board, board.id).title, "Reading")
		assert_eq(
			[share.user_id for share in store.find_by(Share, board_id=board.id)],
			[participant.id],
		)


def test_participant_may_not_delete_a_board():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)

		with assert_raises(NotPermitted):
			board.delete(store, Access(store, participant))

		assert_eq([stored.id for stored in store.find_all(Board)], [board.id])


def test_create_shares_a_new_board_with_chosen_users():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")

		board = Board.create(store, creator, title="Reading", users=[participant])

		assert_eq(board.creator_id, creator.id)
		assert_eq(board.title, "Reading")
		assert_eq(
			[share.user_id for share in store.find_by(Share, board_id=board.id)],
			[participant.id],
		)
