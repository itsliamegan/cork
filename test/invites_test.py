from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from helios.wsgi import TestClient
from luna.test.assertion import assert_eq, assert_that

from app.data import Invite, Recovery, User
from test.support import TestApplication


def test_create_stores_account_invite():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		app.sign_in(creator)
		before = datetime.now(UTC)

		res = app.client.post("/invites/")
		after = datetime.now(UTC)

		assert_eq(res.status_code, 302)
		invite = app.store.find_all(Invite)[0]
		assert_eq(invite.creator_id, creator.id)
		assert_that(invite.target_id is None)
		assert_that(before + timedelta(days=7) <= invite.expires_at)
		assert_that(invite.expires_at <= after + timedelta(days=7))


def test_create_stores_targeted_invite():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		app.sign_in(creator)
		before = datetime.now(UTC)

		res = app.client.post("/invites/", form={"targeted": "on"})
		after = datetime.now(UTC)

		assert_eq(res.status_code, 302)
		invite = app.store.find_all(Invite)[0]
		assert_eq(invite.target_id, creator.id)
		assert_that(before + timedelta(hours=24) <= invite.expires_at)
		assert_that(invite.expires_at <= after + timedelta(hours=24))


def test_show_redirects_after_create():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		app.sign_in(creator)

		created = app.client.post("/invites/")
		app.client.get(created.headers["Location"])

		revisited = app.client.get(created.headers["Location"])
		assert_eq(revisited.status_code, 302)
		assert_eq(revisited.headers["Location"], "/settings")


def test_invite_expires_at_boundary():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		invite = Invite.create(app.store, creator)

		assert_that(Invite.find_valid(app.store, invite.token.value) is invite)
		invite.expires_at = datetime.now(UTC)
		assert_that(Invite.find_valid(app.store, invite.token.value) is None)


def test_signed_in_user_redirects():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		invite = Invite.create(app.store, creator)
		app.sign_in(creator)

		res = app.client.get(f"/redemptions/new?token={invite.token.value}")

		assert_eq(res.status_code, 302)


def test_account_invite_creates_user_and_recovery():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		invite = Invite.create(app.store, creator)

		res = app.client.post(
			"/redemptions/", form={"token": invite.token.value, "name": "  Bob  "}
		)

		assert_eq(res.status_code, 302)
		users = app.store.find_all(User)
		created = next(user for user in users if user.name == "Bob")
		assert_eq(len(app.store.find_by(Recovery, user_id=created.id)), 1)
		assert_that(
			invite.id not in {stored.id for stored in app.store.find_all(Invite)}
		)


def test_duplicate_name_does_not_redeem():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		invite = Invite.create(app.store, creator)

		res = app.client.post(
			"/redemptions/", form={"token": invite.token.value, "name": " alice "}
		)

		assert_eq(res.status_code, 302)
		assert_eq(app.store.find_one(Invite, invite.id).id, invite.id)
		assert_eq(len(app.store.find_all(User)), 1)


def test_empty_name_does_not_redeem():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		invite = Invite.create(app.store, creator)

		res = app.client.post(
			"/redemptions/", form={"token": invite.token.value, "name": "   "}
		)

		assert_eq(res.status_code, 302)
		assert_eq(app.store.find_one(Invite, invite.id).id, invite.id)
		assert_eq(len(app.store.find_all(User)), 1)


def test_spent_invite_cannot_be_reused():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		invite = Invite.create(app.store, creator)

		app.client.post(
			"/redemptions/", form={"token": invite.token.value, "name": "Bob"}
		)
		app.client.delete("/sessions/")
		res = app.client.post(
			"/redemptions/", form={"token": invite.token.value, "name": "Charlie"}
		)

		assert_eq(res.status_code, 302)
		assert_eq(len(app.store.find_all(User)), 2)


def test_targeted_invite_signs_in_without_recovery():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		invite = Invite.create(app.store, alice, target=alice)

		res = app.client.post("/redemptions/", form={"token": invite.token.value})

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/boards/")
		assert_eq(app.store.find_by(Recovery, user_id=alice.id), [])
		assert_that(
			invite.id not in {stored.id for stored in app.store.find_all(Invite)}
		)


def test_invalid_tokens_render_error():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		expired = Invite.create(app.store, creator)
		expired.expires_at = datetime.now(UTC)
		app.store.save(expired)
		redeemed = Invite.create(app.store, creator)
		redeemed_token = redeemed.token.value
		app.store.delete(redeemed.id)

		unknown = app.client.get("/redemptions/new?token=not-a-real-token")
		expired_res = app.client.get(f"/redemptions/new?token={expired.token.value}")
		redeemed_res = app.client.get(f"/redemptions/new?token={redeemed_token}")

		assert_eq(unknown.status_code, 200)
		assert_eq(expired_res.status_code, 200)
		assert_eq(redeemed_res.status_code, 200)


def test_concurrent_redemptions_create_one_user():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
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
					zip(clients, ["Bob", "Charlie"], strict=True),
				)
			)

		with app.persistence.lock() as scope:
			app.store = scope.open(app.store_data).load()

		assert_eq([r.status_code for r in responses], [302, 302])
		assert_eq(len(app.store.find_all(User)), 2)
		assert_that(
			invite.id not in {stored.id for stored in app.store.find_all(Invite)}
		)


def test_invites_are_independent():
	with TestApplication() as app:
		creator = app.store.create(User, name="Alice")
		first = Invite.create(app.store, creator)
		second = Invite.create(app.store, creator)

		first_res = app.client.post(
			"/redemptions/", form={"token": first.token.value, "name": "Bob"}
		)
		app.client.delete("/sessions/")
		second_res = app.client.post(
			"/redemptions/", form={"token": second.token.value, "name": "Charlie"}
		)

		assert_eq(first_res.status_code, 302)
		assert_eq(second_res.status_code, 302)
		assert_eq(len(app.store.find_all(User)), 3)
		remaining = {inv.id for inv in app.store.find_all(Invite)}
		assert_that(first.id not in remaining)
		assert_that(second.id not in remaining)
