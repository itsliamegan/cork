from luna.test.assertion import assert_eq, assert_that

from app.data import Board, Pin, Placement, Share, User
from test.support import TestApplication


def test_creates_pin_and_placement():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		board = app.store.create(Board, title="Reading", creator_id=user.id)
		app.sign_in(user)

		res = app.client.post(
			"/pins/",
			form={
				"title": "Stanford Entry on Sartre",
				"url": "https://plato.stanford.edu/entries/sartre/",
				"note": "Pay particular attention to the Negation section.",
				"board_id": str(board.id),
			},
		)
		pins = app.store.find_all(Pin)
		placements = app.store.find_all(Placement)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{board.id}")
		assert_eq(len(pins), 1)
		assert_eq(pins[0].title, "Stanford Entry on Sartre")
		assert_eq(pins[0].note, "Pay particular attention to the Negation section.")
		assert_eq(pins[0].creator_id, user.id)
		assert_eq(len(placements), 1)
		assert_eq(placements[0].pin_id, pins[0].id)
		assert_eq(placements[0].board_id, board.id)
		assert_eq(placements[0].adder_id, user.id)

		res = app.client.get(f"/pins/{pins[0].id}")

		assert_eq(res.status_code, 200)
		assert_that("Pay particular attention to the Negation section." in res.text)


def test_updates_pin_and_moves_placement():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		reading = app.store.create(Board, title="Reading", creator_id=user.id)
		essays = app.store.create(Board, title="Essays", creator_id=user.id)
		pin = app.store.create(
			Pin,
			title="Stanford Entry on Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			note="Pay particular attention to the Negation section.",
			creator_id=user.id,
		)
		placement = app.store.create(
			Placement,
			pin_id=pin.id,
			board_id=reading.id,
			adder_id=user.id,
		)
		app.sign_in(user)

		res = app.client.post(
			f"/pins/{pin.id}",
			form={
				"_method": "PUT",
				"title": pin.title,
				"url": pin.url,
				"note": "Read Marxism section next?",
				"board_id": str(essays.id),
			},
		)
		updated_pin = app.store.find_one(Pin, pin.id)
		updated_placement = app.store.find_one(Placement, placement.id)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/pins/{pin.id}")
		assert_eq(updated_pin.id, pin.id)
		assert_eq(updated_pin.note, "Read Marxism section next?")
		assert_eq(updated_placement.board_id, essays.id)


def test_shared_board_recipient_can_open_pin_details():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		board = app.store.create(Board, title="Reading", creator_id=alice.id)
		app.store.create(Share, board_id=board.id, user_id=bob.id)
		pin = app.store.create(
			Pin,
			title="Stanford Entry on Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=alice.id,
		)
		app.store.create(Placement, pin_id=pin.id, board_id=board.id, adder_id=alice.id)
		app.sign_in(bob)

		res = app.client.get(f"/pins/{pin.id}")

		assert_eq(res.status_code, 200)
		assert_that("Stanford Entry on Sartre" in res.text)


def test_unrelated_user_cannot_open_pin_details():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		board = app.store.create(Board, title="Reading", creator_id=alice.id)
		pin = app.store.create(
			Pin,
			title="Stanford Entry on Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=alice.id,
		)
		app.store.create(Placement, pin_id=pin.id, board_id=board.id, adder_id=alice.id)
		app.sign_in(bob)

		res = app.client.get(f"/pins/{pin.id}")

		assert_eq(res.status_code, 404)


def test_deletes_pin_and_placement():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		board = app.store.create(Board, title="Reading", creator_id=user.id)
		pin = app.store.create(
			Pin,
			title="Stanford Entry on Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=user.id,
		)
		app.store.create(Placement, pin_id=pin.id, board_id=board.id, adder_id=user.id)
		app.sign_in(user)

		res = app.client.post(f"/pins/{pin.id}", form={"_method": "DELETE"})

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{board.id}")
		assert_eq(app.store.find_all(Pin), [])
		assert_eq(app.store.find_all(Placement), [])
