from helios.http import URL
from luna.test.assertion import assert_eq

from app import Archival, Board, Pin, Placement, Share, User
from test.support import TestApplication


def test_participant_moves_a_placement():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		participant = app.store.create(User, name="Participant")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		app.store.create(Share, board_id=board.id, user_id=participant.id)
		first_pin = app.store.create(
			Pin,
			title="First pin",
			url=URL.parse("https://first.example"),
			creator_id=owner.id,
		)
		second_pin = app.store.create(
			Pin,
			title="Second pin",
			url=URL.parse("https://second.example"),
			creator_id=owner.id,
		)
		first = Placement.create(app.store, first_pin, board, owner)
		second = Placement.create(app.store, second_pin, board, owner)
		app.sign_in(participant)

		res = app.client.post(
			f"/placements/{second.id}/moves",
			form={"above_id": str(first.id)},
		)

		assert_eq(res.status_code, 204)
		assert_eq(
			[placement.id for placement in Placement.arrange(app.store, board)],
			[first.id, second.id],
		)


def test_rejects_malformed_moves():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		first_pin = app.store.create(
			Pin,
			title="First pin",
			url=URL.parse("https://first.example"),
			creator_id=owner.id,
		)
		second_pin = app.store.create(
			Pin,
			title="Second pin",
			url=URL.parse("https://second.example"),
			creator_id=owner.id,
		)
		first = Placement.create(app.store, first_pin, board, owner)
		second = Placement.create(app.store, second_pin, board, owner)
		app.sign_in(owner)

		for form in [
			{"above_id": str(first.id)},
			{"below_id": str(first.id)},
			{"above_id": str(second.id), "below_id": str(second.id)},
			{},
		]:
			res = app.client.post(f"/placements/{first.id}/moves", form=form)

			assert_eq(res.status_code, 400)
			assert_eq(
				[
					app.store.find_one(Placement, placement.id).position
					for placement in [first, second]
				],
				[0, 0],
			)


def test_move_next_to_a_deleted_placement_conflicts():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		first_pin = app.store.create(
			Pin,
			title="First pin",
			url=URL.parse("https://first.example"),
			creator_id=owner.id,
		)
		second_pin = app.store.create(
			Pin,
			title="Second pin",
			url=URL.parse("https://second.example"),
			creator_id=owner.id,
		)
		first = Placement.create(app.store, first_pin, board, owner)
		second = Placement.create(app.store, second_pin, board, owner)
		deleted_id = second.id
		app.store.delete(second)
		app.sign_in(owner)

		res = app.client.post(
			f"/placements/{first.id}/moves",
			form={"above_id": str(deleted_id)},
		)

		assert_eq(res.status_code, 409)
		assert_eq(app.store.find_one(Placement, first.id).position, 0)


def test_moving_a_deleted_placement_is_not_found():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		first_pin = app.store.create(
			Pin,
			title="First pin",
			url=URL.parse("https://first.example"),
			creator_id=owner.id,
		)
		second_pin = app.store.create(
			Pin,
			title="Second pin",
			url=URL.parse("https://second.example"),
			creator_id=owner.id,
		)
		first = Placement.create(app.store, first_pin, board, owner)
		second = Placement.create(app.store, second_pin, board, owner)
		deleted_id = second.id
		app.store.delete(second)
		app.sign_in(owner)

		res = app.client.post(
			f"/placements/{deleted_id}/moves",
			form={"above_id": str(first.id)},
		)

		assert_eq(res.status_code, 404)
		assert_eq(app.store.find_one(Placement, first.id).position, 0)


def test_outsider_cannot_move_placements():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		outsider = app.store.create(User, name="Outsider")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		first_pin = app.store.create(
			Pin,
			title="First pin",
			url=URL.parse("https://first.example"),
			creator_id=owner.id,
		)
		second_pin = app.store.create(
			Pin,
			title="Second pin",
			url=URL.parse("https://second.example"),
			creator_id=owner.id,
		)
		first = Placement.create(app.store, first_pin, board, owner)
		second = Placement.create(app.store, second_pin, board, owner)
		app.sign_in(outsider)

		res = app.client.post(
			f"/placements/{second.id}/moves",
			form={"above_id": str(first.id)},
		)

		assert_eq(res.status_code, 404)
		assert_eq(
			[
				app.store.find_one(Placement, placement.id).position
				for placement in [first, second]
			],
			[0, 0],
		)


def test_moving_an_archived_placement_conflicts():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		first_pin = app.store.create(
			Pin,
			title="First pin",
			url=URL.parse("https://first.example"),
			creator_id=owner.id,
		)
		second_pin = app.store.create(
			Pin,
			title="Second pin",
			url=URL.parse("https://second.example"),
			creator_id=owner.id,
		)
		first = Placement.create(app.store, first_pin, board, owner)
		second = Placement.create(app.store, second_pin, board, owner)
		Archival.create(app.store, second, owner)
		app.sign_in(owner)

		res = app.client.post(
			f"/placements/{second.id}/moves",
			form={"above_id": str(first.id)},
		)

		assert_eq(res.status_code, 409)
		assert_eq(
			[
				app.store.find_one(Placement, placement.id).position
				for placement in [first, second]
			],
			[0, 0],
		)
