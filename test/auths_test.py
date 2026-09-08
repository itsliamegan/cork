from luna.test.assertion import assert_eq, assert_that

from app.data import User
from test.support import TestApplication


def test_signs_in():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")

		res = app.client.post(
			"/sign-in",
			form={"user_id": str(user.id)},
			redirect=True,
		)

		assert_eq(res.status_code, 200)
		assert_that("Boards" in res.text)
		assert_that(user.name in res.text)
		assert_that(app.client.get_cookie("session_id") is not None)
		assert_eq(res.history[0].status_code, 302)
		assert_eq(res.history[0].headers["Location"], "/boards/")


def test_signs_out():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.sign_in(user)

		res = app.client.post("/sign-out")
		boards = app.client.get("/boards/")

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/sign-in")
		assert_eq(boards.status_code, 302)
		assert_eq(boards.headers["Location"], "/sign-in")


def test_redirects_to_sign_in():
	with TestApplication() as app:
		res = app.client.get("/boards/")

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/sign-in")
