from luna.test.assertion import assert_eq

from app import Board, Ordering, User
from test.support import TestApplication


def test_orders_boards():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		reading = app.store.create(Board, title="Reading", creator_id=viewer.id)
		philosophy = app.store.create(Board, title="Philosophy", creator_id=viewer.id)
		app.sign_in(viewer)

		res = app.client.post(
			"/boards/ordering",
			form={
				"_method": "PUT",
				"board_ids": [str(philosophy.id), str(reading.id)],
			},
		)

		assert_eq(res.status_code, 204)
		orderings = app.store.find_by(Ordering, user_id=viewer.id)
		orderings.sort(key=lambda ordering: ordering.position)
		assert_eq(
			[ordering.board_id for ordering in orderings],
			[philosophy.id, reading.id],
		)


def test_rejects_incomplete_orderings():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		stranger = app.store.create(User, name="Stranger")
		reading = app.store.create(Board, title="Reading", creator_id=viewer.id)
		app.store.create(Board, title="Philosophy", creator_id=viewer.id)
		private = app.store.create(
			Board, title="Stranger's Reading", creator_id=stranger.id
		)
		app.sign_in(viewer)

		for board_ids in [[reading.id], [reading.id, private.id]]:
			res = app.client.post(
				"/boards/ordering",
				form={
					"_method": "PUT",
					"board_ids": [str(board_id) for board_id in board_ids],
				},
			)

			assert_eq(res.status_code, 400)
			assert_eq(app.store.find_by(Ordering, user_id=viewer.id), [])
