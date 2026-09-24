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
