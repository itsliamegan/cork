from luna.test.assertion import assert_eq, assert_that

from app import Board, Pin, Placement, Share, User
from test.support import TestApplication


def test_board_placements_default_to_newest_first_and_can_be_reordered():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		participant = app.store.create(User, name="Participant")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		app.store.create(Share, board_id=board.id, user_id=participant.id)
		older_pin = app.store.create(
			Pin,
			title="Older pin",
			url="https://older.example",
			creator_id=owner.id,
		)
		newer_pin = app.store.create(
			Pin,
			title="Newer pin",
			url="https://newer.example",
			creator_id=owner.id,
		)
		older = app.store.create(
			Placement,
			pin_id=older_pin.id,
			board_id=board.id,
			adder_id=owner.id,
		)
		newer = app.store.create(
			Placement,
			pin_id=newer_pin.id,
			board_id=board.id,
			adder_id=owner.id,
		)
		app.sign_in(participant)

		initial_res = app.client.get(f"/boards/{board.id}")
		update_res = app.client.post(
			f"/boards/{board.id}/pins/ordering",
			form={
				"_method": "PUT",
				"placement_ids": [str(older.id), str(newer.id)],
			},
		)
		ordered_res = app.client.get(f"/boards/{board.id}")

		assert_eq(older.position, 0)
		assert_eq(newer.position, 0)
		assert_that(
			initial_res.text.index("Newer pin") < initial_res.text.index("Older pin")
		)
		assert_eq(update_res.status_code, 204)
		assert_eq(app.store.find_one(Placement, older.id).position, 0)
		assert_eq(app.store.find_one(Placement, newer.id).position, 1)
		assert_that(
			ordered_res.text.index("Older pin") < ordered_res.text.index("Newer pin")
		)


def test_rejects_incomplete_duplicate_and_inaccessible_placement_orders():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		outsider = app.store.create(User, name="Outsider")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		placements = []
		for index in range(2):
			pin = app.store.create(
				Pin,
				title=f"Pin {index}",
				url=f"https://example.com/{index}",
				creator_id=owner.id,
			)
			placements.append(
				app.store.create(
					Placement,
					pin_id=pin.id,
					board_id=board.id,
					adder_id=owner.id,
					position=index,
				)
			)
		app.sign_in(owner)

		for placement_ids in [
			[placements[0].id],
			[placements[0].id, placements[0].id],
		]:
			res = app.client.post(
				f"/boards/{board.id}/pins/ordering",
				form={
					"_method": "PUT",
					"placement_ids": [
						str(placement_id) for placement_id in placement_ids
					],
				},
			)
			assert_eq(res.status_code, 400)
			assert_eq(
				[
					app.store.find_one(Placement, placement.id).position
					for placement in placements
				],
				[0, 1],
			)

		app.sign_in(outsider)
		res = app.client.post(
			f"/boards/{board.id}/pins/ordering",
			form={
				"_method": "PUT",
				"placement_ids": [str(placement.id) for placement in placements],
			},
		)
		assert_eq(res.status_code, 404)
