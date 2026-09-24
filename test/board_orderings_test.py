from luna.test.assertion import assert_eq, assert_that

from app.data import Board, Ordering, User
from test.support import TestApplication


def test_orders_boards():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		reading = app.store.create(Board, title="Reading", creator_id=alice.id)
		philosophy = app.store.create(Board, title="Philosophy", creator_id=alice.id)
		essays = app.store.create(Board, title="Essays", creator_id=alice.id)
		app.sign_in(alice)

		res = app.client.post(
			"/boards/ordering",
			form={
				"_method": "PUT",
				"board_id": [
					str(philosophy.id),
					str(reading.id),
					str(essays.id),
				],
			},
		)

		assert_eq(res.status_code, 204)

		orderings = app.store.find_by(Ordering, user_id=alice.id)
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
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		reading = app.store.create(Board, title="Reading", creator_id=alice.id)
		philosophy = app.store.create(Board, title="Philosophy", creator_id=alice.id)
		private = app.store.create(Board, title="Bob's Reading", creator_id=bob.id)
		app.store.create(
			Ordering,
			user_id=alice.id,
			board_id=reading.id,
			position=0,
		)
		app.store.create(
			Ordering,
			user_id=alice.id,
			board_id=philosophy.id,
			position=1,
		)
		app.sign_in(alice)

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
					"board_id": [str(board_id) for board_id in board_ids],
				},
			)

			assert_eq(res.status_code, 400)

			orderings = app.store.find_by(Ordering, user_id=alice.id)
			orderings.sort(key=lambda ordering: ordering.position)
			assert_eq(
				[ordering.board_id for ordering in orderings],
				[reading.id, philosophy.id],
			)
