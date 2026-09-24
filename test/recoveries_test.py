from luna.test.assertion import assert_eq, assert_that

from app import Recovery, User
from test.support import TestApplication


def test_code_is_16_characters():
	code = Recovery.Code.generate()

	assert_eq(len(code.plaintext or ""), 16)


def test_create_generates_recovery():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.sign_in(user)

		res = app.client.post("/recoveries/")

		assert_eq(res.status_code, 302)
		assert_eq(len(app.store.find_by(Recovery, user_id=user.id)), 1)


def test_create_replaces_existing_recovery():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.sign_in(user)

		app.client.post("/recoveries/")
		first_id = app.store.find_by(Recovery, user_id=user.id)[0].id

		app.client.post("/recoveries/")
		recoveries = app.store.find_by(Recovery, user_id=user.id)

		assert_eq(len(recoveries), 1)
		assert_that(recoveries[0].id != first_id)


def test_show_redirects_without_flash():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.sign_in(user)

		created = app.client.post("/recoveries/")
		app.client.get(created.headers["Location"])

		revisited = app.client.get(created.headers["Location"])
		assert_eq(revisited.status_code, 302)
		assert_eq(revisited.headers["Location"], "/settings")
