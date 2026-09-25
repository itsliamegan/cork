from helios.database import NotFoundError
from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Recovery, User
from test.support import TestStore


def test_code_is_16_characters_from_the_alphabet():
	code = Recovery.Code.generate()

	plaintext = code.plaintext or ""

	assert_eq(len(plaintext), 16)
	assert_that(all(character in Recovery.Code.ALPHABET for character in plaintext))


def test_create_replaces_existing_recovery():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		first = Recovery.create(store, owner)

		second = Recovery.create(store, owner)

		recoveries = store.find_by(Recovery, user_id=owner.id)
		assert_eq([recovery.id for recovery in recoveries], [second.id])
		assert_that(second.id != first.id)


def test_created_code_matches_only_its_plaintext():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		recovery = Recovery.create(store, owner)
		plaintext = recovery.code.plaintext or ""

		found = Recovery.find_by_code(store, plaintext)

		assert_that(found is recovery)
		assert_that(Recovery.find_by_code(store, "X" * 16) is None)


def test_redeem_signs_in_user_and_rotates_code():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		recovery = Recovery.create(store, owner)
		plaintext = recovery.code.plaintext or ""

		result = Recovery.redeem(store, plaintext)

		recoveries = store.find_by(Recovery, user_id=owner.id)
		assert_eq(len(recoveries), 1)
		assert_eq(result, (owner, recoveries[0]))
		assert_that(Recovery.find_by_code(store, plaintext) is None)


def test_redeem_rejects_unknown_code():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		Recovery.create(store, owner)

		result = Recovery.redeem(store, "X" * 16)

		assert_that(result is None)


def test_find_owned_hides_other_users_recoveries():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		stranger = store.create(User, name="Stranger")
		recovery = Recovery.create(store, owner)

		found = Recovery.find_owned(store, recovery.id, owner)

		assert_eq(found.id, recovery.id)
		with assert_raises(NotFoundError):
			Recovery.find_owned(store, recovery.id, stranger)
