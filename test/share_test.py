from luna.test.assertion import assert_eq, assert_raises

from app import Board, Ordering, Share, User
from test.support import TestStore


def test_replace_adds_and_removes_shares_and_keeps_retained_ones():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		kept = store.create(User, name="Kept")
		removed = store.create(User, name="Removed")
		added = store.create(User, name="Added")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		retained = store.create(Share, board_id=board.id, user_id=kept.id)
		store.create(Share, board_id=board.id, user_id=removed.id)

		Share.replace(store, board, [kept, added])

		shares = {
			share.user_id: share for share in store.find_by(Share, board_id=board.id)
		}
		assert_eq(set(shares), {kept.id, added.id})
		assert_eq(shares[kept.id].id, retained.id)


def test_replace_with_no_users_unshares_the_board():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)

		Share.replace(store, board, [])

		assert_eq(store.find_by(Share, board_id=board.id), [])


def test_replace_leaves_other_boards_shares_alone():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		reading = store.create(Board, title="Reading", creator_id=creator.id)
		essays = store.create(Board, title="Essays", creator_id=creator.id)
		store.create(Share, board_id=reading.id, user_id=participant.id)
		other = store.create(Share, board_id=essays.id, user_id=participant.id)

		Share.replace(store, reading, [])

		shares = store.find_by(Share, board_id=essays.id)
		assert_eq([share.id for share in shares], [other.id])


def test_replace_shares_once_per_user():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)

		Share.replace(store, board, [participant, participant])

		shares = store.find_by(Share, board_id=board.id)
		assert_eq([share.user_id for share in shares], [participant.id])


def test_replace_refuses_the_creator_without_changes():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		share = store.create(Share, board_id=board.id, user_id=participant.id)

		with assert_raises(ValueError):
			Share.replace(store, board, [creator])

		shares = store.find_by(Share, board_id=board.id)
		assert_eq([stored.id for stored in shares], [share.id])


def test_replace_resets_the_owners_row_when_a_board_is_first_shared():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Ordering, user_id=creator.id, board_id=board.id, position=0)

		Share.replace(store, board, [participant])

		assert_eq(store.find_by(Ordering, board_id=board.id), [])


def test_replace_resets_the_owners_row_when_a_board_is_unshared():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)
		store.create(Ordering, user_id=creator.id, board_id=board.id, position=0)

		Share.replace(store, board, [])

		assert_eq(store.find_by(Ordering, user_id=creator.id), [])


def test_replace_keeps_the_owners_row_while_a_board_stays_shared():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		removed = store.create(User, name="Removed")
		added = store.create(User, name="Added")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=removed.id)
		ordering = store.create(
			Ordering, user_id=creator.id, board_id=board.id, position=0
		)

		Share.replace(store, board, [added])

		orderings = store.find_by(Ordering, board_id=board.id)
		assert_eq([stored.id for stored in orderings], [ordering.id])


def test_replace_keeps_recipients_rows_when_a_board_is_unshared():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)
		ordering = store.create(
			Ordering, user_id=participant.id, board_id=board.id, position=0
		)

		Share.replace(store, board, [])

		orderings = store.find_by(Ordering, board_id=board.id)
		assert_eq([stored.id for stored in orderings], [ordering.id])
