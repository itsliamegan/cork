from datetime import UTC, datetime, timedelta

from helios.database import NotFoundError
from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Invite, User
from test.support import TestStore


def test_untargeted_invite_lasts_a_week():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		before = datetime.now(UTC)

		invite = Invite.create(store, creator)
		after = datetime.now(UTC)

		assert_eq(invite.creator_id, creator.id)
		assert_that(invite.target_id is None)
		assert_that(before + timedelta(days=7) <= invite.expires_at)
		assert_that(invite.expires_at <= after + timedelta(days=7))


def test_targeted_invite_lasts_a_day():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		before = datetime.now(UTC)

		invite = Invite.create(store, creator, target=creator)
		after = datetime.now(UTC)

		assert_eq(invite.target_id, creator.id)
		assert_that(before + timedelta(hours=24) <= invite.expires_at)
		assert_that(invite.expires_at <= after + timedelta(hours=24))


def test_invite_expires_at_boundary():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		invite = Invite.create(store, creator)

		assert_that(Invite.find_valid(store, invite.token.value) is invite)
		invite.expires_at = datetime.now(UTC)
		assert_that(Invite.find_valid(store, invite.token.value) is None)


def test_unknown_token_is_invalid():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		Invite.create(store, creator)

		invite = Invite.find_valid(store, "not-a-real-token")

		assert_that(invite is None)


def test_redeeming_untargeted_invite_creates_user_and_spends_invite():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		invite = Invite.create(store, creator)

		newcomer = invite.redeem(store, "Newcomer")

		assert_eq(newcomer.name, "Newcomer")
		assert_eq(
			{stored.name for stored in store.find_all(User)}, {"Creator", "Newcomer"}
		)
		assert_that(Invite.find_valid(store, invite.token.value) is None)


def test_redeeming_targeted_invite_returns_target_and_spends_invite():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		invite = Invite.create(store, creator, target=creator)

		redeemed = invite.redeem_for_target(store)

		assert_that(redeemed is creator)
		assert_eq(len(store.find_all(User)), 1)
		assert_that(Invite.find_valid(store, invite.token.value) is None)


def test_redeem_refuses_a_targeted_invite():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		invite = Invite.create(store, creator, target=creator)

		with assert_raises(ValueError):
			invite.redeem(store, "Newcomer")

		assert_eq(len(store.find_all(User)), 1)
		assert_that(Invite.find_valid(store, invite.token.value) is invite)


def test_redeem_for_target_refuses_an_untargeted_invite():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		invite = Invite.create(store, creator)

		with assert_raises(ValueError):
			invite.redeem_for_target(store)

		assert_that(Invite.find_valid(store, invite.token.value) is invite)


def test_redeeming_one_invite_leaves_others_valid():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		first = Invite.create(store, creator)
		second = Invite.create(store, creator)

		first.redeem(store, "Newcomer")

		assert_that(Invite.find_valid(store, first.token.value) is None)
		assert_that(Invite.find_valid(store, second.token.value) is second)


def test_find_target_returns_target_user():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		untargeted_invite = Invite.create(store, creator)
		targeted_invite = Invite.create(store, creator, target=creator)

		untargeted_target = untargeted_invite.find_target(store)
		targeted_target = targeted_invite.find_target(store)

		assert_that(untargeted_target is None)
		assert_that(targeted_target is creator)


def test_find_created_by_hides_other_creators_invites():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		stranger = store.create(User, name="Stranger")
		invite = Invite.create(store, creator)

		found = Invite.find_created_by(store, invite.id, creator)

		assert_eq(found.id, invite.id)
		with assert_raises(NotFoundError):
			Invite.find_created_by(store, invite.id, stranger)
