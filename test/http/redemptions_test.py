from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from luna.test.assertion import assert_eq, assert_that

from app import Invite, Recovery, User
from test.support import TestApplication, TestClient


def test_signed_in_user_redirects():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		invite = Invite.create(app.store, creator)
		app.sign_in(creator)

		res = app.client.get(f"/redemptions/new?token={invite.token.value}")

		assert_eq(res.status_code, 302)


def test_new_renders_untargeted_invite():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		invite = Invite.create(app.store, creator)

		res = app.client.get(f"/redemptions/new?token={invite.token.value}")

		assert_eq(res.status_code, 200)
		assert_that("Invited by Creator" in res.text)


def test_new_renders_targeted_invite():
	with TestApplication() as app:
		target = app.store.create(User, name="Target")
		invite = Invite.create(app.store, target, target=target)

		res = app.client.get(f"/redemptions/new?token={invite.token.value}")

		assert_eq(res.status_code, 200)
		assert_that("<strong>Target</strong>" in res.text)


def test_new_renders_name_error():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		invite = Invite.create(app.store, creator)

		res = app.client.post(
			"/redemptions/", form={"token": invite.token.value, "name": " creator "}
		)
		res = app.client.get(res.headers["Location"])

		assert_eq(res.status_code, 200)
		assert_that("That name is already in use." in res.text)
		assert_that('value="creator"' in res.text)


def test_untargeted_invite_creates_user_and_recovery():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		invite = Invite.create(app.store, creator)

		res = app.client.post(
			"/redemptions/", form={"token": invite.token.value, "name": "  Newcomer  "}
		)

		assert_eq(res.status_code, 302)
		users = app.store.find_all(User)
		created = next(user for user in users if user.name == "Newcomer")
		assert_eq(len(app.store.find_by(Recovery, user_id=created.id)), 1)
		assert_that(
			invite.id not in {stored.id for stored in app.store.find_all(Invite)}
		)


def test_duplicate_name_does_not_redeem():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		invite = Invite.create(app.store, creator)

		res = app.client.post(
			"/redemptions/", form={"token": invite.token.value, "name": " creator "}
		)

		assert_eq(res.status_code, 302)
		assert_eq(app.store.find_one(Invite, invite.id).id, invite.id)
		assert_eq(len(app.store.find_all(User)), 1)


def test_empty_name_does_not_redeem():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		invite = Invite.create(app.store, creator)

		res = app.client.post(
			"/redemptions/", form={"token": invite.token.value, "name": "   "}
		)

		assert_eq(res.status_code, 302)
		assert_eq(app.store.find_one(Invite, invite.id).id, invite.id)
		assert_eq(len(app.store.find_all(User)), 1)


def test_targeted_invite_signs_in_without_recovery():
	with TestApplication() as app:
		target = app.store.create(User, name="Target")
		invite = Invite.create(app.store, target, target=target)

		res = app.client.post("/redemptions/", form={"token": invite.token.value})

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/boards/")
		assert_eq(app.store.find_by(Recovery, user_id=target.id), [])
		assert_that(
			invite.id not in {stored.id for stored in app.store.find_all(Invite)}
		)


def test_invalid_tokens_render_error():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		expired = Invite.create(app.store, creator)
		expired.expires_at = datetime.now(UTC)
		app.store.save(expired)
		redeemed = Invite.create(app.store, creator)
		redeemed_token = redeemed.token.value
		app.store.delete(redeemed)

		unknown = app.client.get("/redemptions/new?token=not-a-real-token")
		expired_res = app.client.get(f"/redemptions/new?token={expired.token.value}")
		redeemed_res = app.client.get(f"/redemptions/new?token={redeemed_token}")

		assert_eq(unknown.status_code, 200)
		assert_eq(expired_res.status_code, 200)
		assert_eq(redeemed_res.status_code, 200)


def test_concurrent_redemptions_create_one_user():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		invite = Invite.create(app.store, creator)
		app.client.get(f"/redemptions/new?token={invite.token.value}")
		clients = [TestClient(app), TestClient(app)]

		with ThreadPoolExecutor(max_workers=2) as executor:
			responses = list(
				executor.map(
					lambda pair: pair[0].post(
						"/redemptions/",
						form={"token": invite.token.value, "name": pair[1]},
					),
					zip(clients, ["Newcomer", "Second newcomer"], strict=True),
				)
			)

		assert_eq([r.status_code for r in responses], [302, 302])
		assert_eq(len(app.store.find_all(User)), 2)
		assert_that(
			invite.id not in {stored.id for stored in app.store.find_all(Invite)}
		)
