from luna.test.assertion import assert_eq, assert_that

from app import Board, Ordering, User
from test.support import TestApplication


def test_orders_boards():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		reading = app.store.create(Board, title="Reading", creator_id=viewer.id)
		philosophy = app.store.create(Board, title="Philosophy", creator_id=viewer.id)
		essays = app.store.create(Board, title="Essays", creator_id=viewer.id)
		app.sign_in(viewer)

		res = app.client.post(
			"/boards/ordering",
			form={
				"_method": "PUT",
				"board_ids": [
					str(philosophy.id),
					str(reading.id),
					str(essays.id),
				],
			},
		)

		assert_eq(res.status_code, 204)

		orderings = app.store.find_by(Ordering, user_id=viewer.id)
		orderings.sort(key=lambda ordering: ordering.position)
		assert_eq(
			[ordering.board_id for ordering in orderings],
			[philosophy.id, reading.id, essays.id],
		)

		res = app.client.get("/boards/")

		assert_that(res.text.index("Philosophy") < res.text.index("Reading"))
		assert_that(res.text.index("Reading") < res.text.index("Essays"))


def test_rejects_invalid_orderings():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		stranger = app.store.create(User, name="Stranger")
		reading = app.store.create(Board, title="Reading", creator_id=viewer.id)
		philosophy = app.store.create(Board, title="Philosophy", creator_id=viewer.id)
		private = app.store.create(
			Board, title="Stranger's Reading", creator_id=stranger.id
		)
		app.store.create(
			Ordering,
			user_id=viewer.id,
			board_id=reading.id,
			position=0,
		)
		app.store.create(
			Ordering,
			user_id=viewer.id,
			board_id=philosophy.id,
			position=1,
		)
		app.sign_in(viewer)

		invalid_orders = [
			# Duplicate
			[reading.id, reading.id],
			# Incomplete
			[reading.id],
			[reading.id, private.id],
		]

		for board_ids in invalid_orders:
			res = app.client.post(
				"/boards/ordering",
				form={
					"_method": "PUT",
					"board_ids": [str(board_id) for board_id in board_ids],
				},
			)

			assert_eq(res.status_code, 400)

			orderings = app.store.find_by(Ordering, user_id=viewer.id)
			orderings.sort(key=lambda ordering: ordering.position)
			assert_eq(
				[ordering.board_id for ordering in orderings],
				[reading.id, philosophy.id],
			)
