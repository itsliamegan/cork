from luna.test.assertion import assert_eq

from app import Board, Pin, Placement, Share, User
from test.support import TestApplication


def test_authorized_user_removes_placement_but_keeps_pin():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		adder = app.store.create(User, name="Adder")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		app.store.create(Share, board_id=board.id, user_id=adder.id)
		pin = app.store.create(
			Pin, title="Pin", url="https://example.com", creator_id=owner.id
		)
		placement = app.store.create(
			Placement, pin_id=pin.id, board_id=board.id, adder_id=adder.id
		)
		app.sign_in(adder)

		res = app.client.post(f"/placements/{placement.id}", form={"_method": "DELETE"})

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
		assert_eq(delete_res.status_code, 404)
		assert_eq(app.store.find_one(Placement, placement.id).id, placement.id)
