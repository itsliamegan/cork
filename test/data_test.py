from uuid import uuid4

from helios.database import DatabaseError
from luna.test.assertion import assert_eq, assert_that

from app.data import Pin, User
from test.support import TestApplication


def test_user_names_are_unique_ignoring_ascii_case():
	with TestApplication() as app:
		app.store.create(User, name="Alice")

		try:
			app.store.create(User, name="ALICE")
		except DatabaseError:
			rejected = True
		else:
			rejected = False

		assert_that(rejected)
		assert_eq([user.name for user in app.store.find_all(User)], ["Alice"])


def test_user_names_may_differ_only_in_non_ascii_case():
	with TestApplication() as app:
		app.store.create(User, name="Émile")

		app.store.create(User, name="émile")

		assert_eq(len(app.store.find_all(User)), 2)


def test_display_url_shortens_to_hostname():
	pin = Pin(
		title="Sartre",
		url="https://www.example.com/articles/sartre",
		creator_id=uuid4(),
	)

	display_url = pin.display_url()

	assert_eq(display_url, "example.com")
