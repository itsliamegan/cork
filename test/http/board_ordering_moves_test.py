from luna.test.assertion import assert_eq

from app import Access, Board, Ordering, Share, User
from test.support import TestApplication


def test_moves_a_board():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		reading = app.store.create(Board, title="Reading", creator_id=viewer.id)
		philosophy = app.store.create(Board, title="Philosophy", creator_id=viewer.id)
		app.sign_in(viewer)

		res = app.client.post(
			f"/boards/{reading.id}/ordering/moves",
			form={"below_id": str(philosophy.id)},
		)

		assert_eq(res.status_code, 204)
		private, _ = Ordering.arrange(app.store, Access(app.store, viewer))
		assert_eq([board.id for board in private], [reading.id, philosophy.id])


def test_rejects_malformed_moves():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		reading = app.store.create(Board, title="Reading", creator_id=viewer.id)
		philosophy = app.store.create(Board, title="Philosophy", creator_id=viewer.id)
		app.sign_in(viewer)

		for form in [
			{"above_id": str(reading.id)},
			{"below_id": str(reading.id)},
			{"above_id": str(philosophy.id), "below_id": str(philosophy.id)},
			{},
		]:
			res = app.client.post(f"/boards/{reading.id}/ordering/moves", form=form)

			assert_eq(res.status_code, 400)
			assert_eq(app.store.find_by(Ordering, user_id=viewer.id), [])


def test_move_next_to_a_board_in_the_other_section_conflicts():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		participant = app.store.create(User, name="Participant")
		private = app.store.create(Board, title="Private", creator_id=viewer.id)
		shared = app.store.create(Board, title="Shared", creator_id=viewer.id)
		app.store.create(Share, board_id=shared.id, user_id=participant.id)
		app.sign_in(viewer)

		res = app.client.post(
			f"/boards/{private.id}/ordering/moves",
			form={"below_id": str(shared.id)},
		)

		assert_eq(res.status_code, 409)
		assert_eq(app.store.find_by(Ordering, user_id=viewer.id), [])


def test_outsider_cannot_move_a_board():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		stranger = app.store.create(User, name="Stranger")
		reading = app.store.create(Board, title="Reading", creator_id=viewer.id)
		private = app.store.create(Board, title="Private", creator_id=stranger.id)
		app.sign_in(viewer)

		res = app.client.post(
			f"/boards/{private.id}/ordering/moves",
			form={"below_id": str(reading.id)},
		)

		assert_eq(res.status_code, 404)
		assert_eq(app.store.find_by(Ordering, user_id=viewer.id), [])
