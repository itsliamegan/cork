from helios.database import DatabaseError
from luna.test.assertion import assert_eq, assert_raises

from app import User
from test.support import TestStore


def test_names_are_unique_ignoring_ascii_case():
	with TestStore() as store:
		store.create(User, name="Alice")

		with assert_raises(DatabaseError):
			store.create(User, name="ALICE")

		assert_eq([user.name for user in store.find_all(User)], ["Alice"])


def test_names_may_differ_only_in_non_ascii_case():
	with TestStore() as store:
		store.create(User, name="Émile")

		store.create(User, name="émile")

		assert_eq(len(store.find_all(User)), 2)
