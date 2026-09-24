from luna.test.assertion import assert_eq

from app import Recovery, User
from test.support import TestApplication


def test_create_generates_recovery():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.sign_in(user)

		res = app.client.post("/recoveries/")

		assert_eq(res.status_code, 302)
		assert_eq(len(app.store.find_by(Recovery, user_id=user.id)), 1)


def test_show_redirects_without_flash():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.sign_in(user)

		created = app.client.post("/recoveries/")
		app.client.get(created.headers["Location"])

		revisited = app.client.get(created.headers["Location"])
		assert_eq(revisited.status_code, 302)
		assert_eq(revisited.headers["Location"], "/settings")
