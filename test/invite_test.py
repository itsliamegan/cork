from datetime import UTC, datetime, timedelta

from helios.database import NotFoundError
from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Invite, User
from test.support import TestStore


def test_account_invite_lasts_a_week_without_a_target():
	with TestStore() as store:
		creator = store.create(User, name="Alice")
		before = datetime.now(UTC)

		invite = Invite.create(store, creator)
		after = datetime.now(UTC)

		assert_eq(invite.creator_id, creator.id)
		assert_that(invite.target_id is None)
		assert_that(before + timedelta(days=7) <= invite.expires_at)
		assert_that(invite.expires_at <= after + timedelta(days=7))


def test_targeted_invite_lasts_a_day():
	with TestStore() as store:
		creator = store.create(User, name="Alice")
		before = datetime.now(UTC)

		invite = Invite.create(store, creator, target=creator)
		after = datetime.now(UTC)

		assert_eq(invite.target_id, creator.id)
		assert_that(before + timedelta(hours=24) <= invite.expires_at)
		assert_that(invite.expires_at <= after + timedelta(hours=24))


def test_invite_expires_at_boundary():
	with TestStore() as store:
		creator = store.create(User, name="Alice")
		invite = Invite.create(store, creator)

		assert_that(Invite.find_valid(store, invite.token.value) is invite)
		invite.expires_at = datetime.now(UTC)
		assert_that(Invite.find_valid(store, invite.token.value) is None)


def test_unknown_token_is_invalid():
	with TestStore() as store:
		creator = store.create(User, name="Alice")
		Invite.create(store, creator)

		invite = Invite.find_valid(store, "not-a-real-token")

		assert_that(invite is None)


def test_redeeming_account_invite_creates_user_and_spends_invite():
	with TestStore() as store:
		creator = store.create(User, name="Alice")
		invite = Invite.create(store, creator)

		user = invite.redeem(store, "Bob")

		assert_eq(user.name, "Bob")
		assert_eq({stored.name for stored in store.find_all(User)}, {"Alice", "Bob"})
		assert_that(Invite.find_valid(store, invite.token.value) is None)


def test_redeeming_targeted_invite_returns_target_and_spends_invite():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		invite = Invite.create(store, alice, target=alice)

		user = invite.redeem(store, "")

		assert_eq(user.id, alice.id)
		assert_eq(len(store.find_all(User)), 1)
		assert_that(Invite.find_valid(store, invite.token.value) is None)


def test_redeeming_one_invite_leaves_others_valid():
	with TestStore() as store:
		creator = store.create(User, name="Alice")
		first = Invite.create(store, creator)
		second = Invite.create(store, creator)

		first.redeem(store, "Bob")

		assert_that(Invite.find_valid(store, first.token.value) is None)
		assert_that(Invite.find_valid(store, second.token.value) is second)


def test_find_target_returns_target_user():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		account_invite = Invite.create(store, alice)
		targeted_invite = Invite.create(store, alice, target=alice)

		account_target = account_invite.find_target(store)
		targeted_target = targeted_invite.find_target(store)

		assert_that(account_target is None)
		assert_that(targeted_target is alice)


def test_find_created_by_hides_other_creators_invites():
	with TestStore() as store:
		alice = store.create(User, name="Alice")
		bob = store.create(User, name="Bob")
		invite = Invite.create(store, alice)

		found = Invite.find_created_by(store, invite.id, alice)

		assert_eq(found.id, invite.id)
		with assert_raises(NotFoundError):
			Invite.find_created_by(store, invite.id, bob)
