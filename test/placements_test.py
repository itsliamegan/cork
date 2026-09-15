from luna.test.assertion import assert_eq, assert_raises, assert_that

from app.data import Board, Pin, Placement, Share, User
from test.support import TestApplication


def test_placement_is_unique_for_each_pin_and_board_pair():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		reading = app.store.create(Board, title="Reading", creator_id=user.id)
		essays = app.store.create(Board, title="Essays", creator_id=user.id)
		first_pin = app.store.create(
			Pin, title="First pin", url="https://first.example", creator_id=user.id
		)
		second_pin = app.store.create(
			Pin, title="Second pin", url="https://second.example", creator_id=user.id
		)

		Placement.create(app.store, first_pin, reading, user)
		with assert_raises(ValueError):
			Placement.create(app.store, first_pin, reading, user)
		Placement.create(app.store, first_pin, essays, user)
		Placement.create(app.store, second_pin, reading, user)

		assert_eq(len(app.store.find_all(Placement)), 3)


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
			f"/boards/{board.id}/placements",
			form={
				"_method": "PUT",
				"placement_id": [str(older.id), str(newer.id)],
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
		assert_eq(ordered_res.text.count('title="Drag to reorder"'), 2)


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
				f"/boards/{board.id}/placements",
				form={
					"_method": "PUT",
					"placement_id": [
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
			f"/boards/{board.id}/placements",
			form={
				"_method": "PUT",
				"placement_id": [str(placement.id) for placement in placements],
			},
		)
		assert_eq(res.status_code, 404)


def test_pin_creator_placement_adder_and_board_creator_can_remove_placements():
	with TestApplication() as app:
		board_creator = app.store.create(User, name="Board creator")
		pin_creator = app.store.create(User, name="Pin creator")
		adder = app.store.create(User, name="Adder")
		board = app.store.create(Board, title="Reading", creator_id=board_creator.id)
		for user in [pin_creator, adder]:
			app.store.create(Share, board_id=board.id, user_id=user.id)

		roles = [pin_creator, adder, board_creator]
		for role in roles:
			pin = app.store.create(
				Pin,
				title=f"Pin removed by {role.name}",
				url="https://example.com",
				creator_id=pin_creator.id,
			)
			placement = app.store.create(
				Placement, pin_id=pin.id, board_id=board.id, adder_id=adder.id
			)
			app.sign_in(role)

			res = app.client.post(
				f"/placements/{placement.id}", form={"_method": "DELETE"}
			)

			assert_eq(res.status_code, 302)
			assert_eq(res.headers["Location"], f"/boards/{board.id}")
			assert_eq(app.store.find_by(Placement, pin_id=pin.id), [])
			assert_eq(app.store.find_one(Pin, pin.id).id, pin.id)


def test_unrelated_participant_cannot_remove_another_users_placement():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		creator = app.store.create(User, name="Creator")
		adder = app.store.create(User, name="Adder")
		participant = app.store.create(User, name="Participant")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		app.store.create(Share, board_id=board.id, user_id=participant.id)
		pin = app.store.create(
			Pin, title="Pin", url="https://example.com", creator_id=creator.id
		)
		placement = app.store.create(
			Placement, pin_id=pin.id, board_id=board.id, adder_id=adder.id
		)
		app.sign_in(participant)

		show_res = app.client.get(f"/boards/{board.id}")
		delete_res = app.client.post(
			f"/placements/{placement.id}", form={"_method": "DELETE"}
		)

		assert_eq(show_res.status_code, 200)
		assert_that(">Remove</button>" not in show_res.text)
		assert_eq(delete_res.status_code, 404)
		assert_eq(app.store.find_one(Placement, placement.id).id, placement.id)


def test_adder_without_current_board_access_cannot_remove_placement():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		creator = app.store.create(User, name="Creator")
		former_adder = app.store.create(User, name="Former adder")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Pin", url="https://example.com", creator_id=creator.id
		)
		placement = app.store.create(
			Placement,
			pin_id=pin.id,
			board_id=board.id,
			adder_id=former_adder.id,
		)
		app.sign_in(former_adder)

		res = app.client.post(f"/placements/{placement.id}", form={"_method": "DELETE"})

		assert_eq(res.status_code, 404)
		assert_eq(app.store.find_one(Placement, placement.id).id, placement.id)
