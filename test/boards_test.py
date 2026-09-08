from luna.test.assertion import assert_eq

from app.data import Board, User
from test.support import TestApplication


def test_creates_board():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.sign_in(user)

		res = app.client.post("/boards/", form={"title": "Reading"})
		boards = app.store.find_all(Board)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{boards[0].id}")
		assert_eq(len(boards), 1)
		assert_eq(boards[0].title, "Reading")
		assert_eq(boards[0].user_id, user.id)


def test_deletes_board():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		board = app.store.create(Board, title="Reading", user_id=user.id)
		app.sign_in(user)

		res = app.client.post(
			f"/boards/{board.id}",
			form={"_method": "DELETE"},
		)
		boards = app.store.find_all(Board)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/boards/")
		assert_eq(boards, [])
