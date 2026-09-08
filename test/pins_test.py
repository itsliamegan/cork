from luna.test.assertion import assert_eq, assert_that

from app.data import Board, Pin, User
from test.support import TestApplication


def test_creates_pin():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		board = app.store.create(Board, title="Reading", user_id=user.id)
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

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{board.id}")
		assert_eq(len(pins), 1)
		assert_eq(pins[0].title, "Stanford Entry on Sartre")
		assert_eq(pins[0].note, "Pay particular attention to the Negation section.")
		assert_eq(pins[0].board_id, board.id)
		assert_eq(pins[0].user_id, user.id)

		res = app.client.get(f"/pins/{pins[0].id}")

		assert_eq(res.status_code, 200)
		assert_that("Pay particular attention to the Negation section." in res.text)


def test_updates_pin_note():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		board = app.store.create(Board, title="Reading", user_id=user.id)
		pin = app.store.create(
			Pin,
			title="Stanford Entry on Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			note="Pay particular attention to the Negation section.",
			board_id=board.id,
			user_id=user.id,
		)
		app.sign_in(user)

		res = app.client.post(
			f"/pins/{pin.id}",
			form={
				"_method": "PUT",
				"title": pin.title,
				"url": pin.url,
				"note": "Read Marxism section next?",
				"board_id": str(board.id),
			},
		)
		updated_pin = app.store.find_one(Pin, pin.id)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/pins/{pin.id}")
		assert_eq(updated_pin.note, "Read Marxism section next?")

		res = app.client.get(f"/pins/{pin.id}")

		assert_eq(res.status_code, 200)
		assert_that("Read Marxism section next?" in res.text)
