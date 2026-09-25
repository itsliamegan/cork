from luna.test.assertion import assert_eq, assert_that

from app import Invite, User
from test.support import TestApplication


def test_create_stores_untargeted_invite():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		app.sign_in(creator)

		res = app.client.post("/invites/")

		assert_eq(res.status_code, 302)
		invite = app.store.find_all(Invite)[0]
		assert_eq(invite.creator_id, creator.id)
		assert_that(invite.target_id is None)


def test_create_stores_targeted_invite():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		app.sign_in(creator)

		res = app.client.post("/invites/", form={"targeted": "on"})

		assert_eq(res.status_code, 302)
		invite = app.store.find_all(Invite)[0]
		assert_eq(invite.target_id, creator.id)


def test_show_redirects_after_create():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		app.sign_in(creator)

		created = app.client.post("/invites/")
		app.client.get(created.headers["Location"])

		revisited = app.client.get(created.headers["Location"])
		assert_eq(revisited.status_code, 302)
		assert_eq(revisited.headers["Location"], "/settings")
