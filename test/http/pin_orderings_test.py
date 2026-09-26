from luna.test.assertion import assert_eq

from app import Board, Pin, Placement, Share, User
from test.support import TestApplication


def test_participant_reorders_placements():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		participant = app.store.create(User, name="Participant")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		app.store.create(Share, board_id=board.id, user_id=participant.id)
		first_pin = app.store.create(
			Pin,
			title="First pin",
			url="https://first.example",
			creator_id=owner.id,
		)
		second_pin = app.store.create(
			Pin,
			title="Second pin",
			url="https://second.example",
			creator_id=owner.id,
		)
		first = Placement.create(app.store, first_pin, board, owner)
		second = Placement.create(app.store, second_pin, board, owner)
		app.sign_in(participant)

		res = app.client.post(
			f"/boards/{board.id}/pins/ordering",
			form={
				"_method": "PUT",
				"placement_ids": [str(second.id), str(first.id)],
			},
		)

		assert_eq(res.status_code, 204)
		assert_eq(
			[
				app.store.find_one(Placement, placement.id).position
				for placement in [first, second]
			],
			[1, 0],
		)


def test_rejects_incomplete_placement_orders():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		first_pin = app.store.create(
			Pin,
			title="First pin",
			url="https://first.example",
			creator_id=owner.id,
		)
		second_pin = app.store.create(
			Pin,
			title="Second pin",
			url="https://second.example",
			creator_id=owner.id,
		)
		first = Placement.create(app.store, first_pin, board, owner)
		second = Placement.create(app.store, second_pin, board, owner)
		app.sign_in(owner)

		res = app.client.post(
			f"/boards/{board.id}/pins/ordering",
			form={
				"_method": "PUT",
				"placement_ids": [str(first.id)],
			},
		)

		assert_eq(res.status_code, 400)
		assert_eq(
			[
				app.store.find_one(Placement, placement.id).position
				for placement in [first, second]
			],
			[0, 0],
		)


def test_outsider_cannot_reorder_placements():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		outsider = app.store.create(User, name="Outsider")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		first_pin = app.store.create(
			Pin,
			title="First pin",
			url="https://first.example",
			creator_id=owner.id,
		)
		second_pin = app.store.create(
			Pin,
			title="Second pin",
			url="https://second.example",
			creator_id=owner.id,
		)
		first = Placement.create(app.store, first_pin, board, owner)
		second = Placement.create(app.store, second_pin, board, owner)
		app.sign_in(outsider)

		res = app.client.post(
			f"/boards/{board.id}/pins/ordering",
			form={
				"_method": "PUT",
				"placement_ids": [str(second.id), str(first.id)],
			},
		)

		assert_eq(res.status_code, 404)
		assert_eq(
			[
				app.store.find_one(Placement, placement.id).position
				for placement in [first, second]
			],
			[0, 0],
		)
