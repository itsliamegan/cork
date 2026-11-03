from datetime import UTC, datetime, timedelta

from helios.auth.authenticator import SESSION_KEY
from helios.auth.password import Digest
import helios.auth.test
from helios.http import Input
from luna.test.assertion import (
	assert_eq,
	assert_is,
	assert_not_none,
	assert_that,
)

from app import Recovery, User
from app.http.sessions import SignInForm
from test.support import TestApplication


def test_new_renders():
	with TestApplication() as app:
		res = app.client.get("/sessions/new")

		assert_eq(res.status_code, 200)


def test_new_redirects_when_signed_in():
	with TestApplication() as app:
		user = app.store.create(User, name="User")
		app.sign_in(user)

		res = app.client.get("/sessions/new")

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/boards/")


def test_create_signs_in_with_recovery_code():
	with TestApplication() as app:
		user = app.store.create(User, name="User")
		app.store.create(
			Recovery,
			user_id=user.id,
			code=Recovery.Code(Digest.generate("ABCDEFGHJKLMNPQR")),
		)

		res = app.client.post("/sessions/", form={"recovery_code": "ABCDEFGHJKLMNPQR"})
		boards = app.client.get("/boards/")

		assert_eq(res.status_code, 302)
		assert_eq(boards.status_code, 200)


def test_create_rejects_invalid_recovery_code():
	with TestApplication() as app:
		app.store.create(User, name="User")

		res = app.client.post("/sessions/", form={"recovery_code": "XXXXXXXXXX"})
		boards = app.client.get("/boards/")

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/sessions/new")
		assert_eq(boards.status_code, 302)


def test_sign_in_form_normalizes_recovery_code():
	for code in [
		"ABCDEFGHJKLMNPQR",
		"abcdefghjklmnpqr",
		" abcd efgh\tjklm\nnpqr ",
		"AbCd EfGh jKlM nPqR",
	]:
		form, errors = SignInForm.validate(Input({"recovery_code": code}))

		assert_that(not errors)
		assert_eq(form.recovery_code, "ABCDEFGHJKLMNPQR")


def test_sign_in_form_rejects_recovery_codes_with_disallowed_characters():
	for code in [
		"ABCDEFGHJKLMNPQ0",
		"ABCDEFGHJKLMNPQ1",
		"ABCDEFGHJKLMNPQI",
		"ABCDEFGHJKLMNPQO",
		"ABCD-EFGH-JKLM-NP",
	]:
		_, errors = SignInForm.validate(Input({"recovery_code": code}))

		assert_eq(
			errors.first("recovery_code"),
			"Recovery code must only contain allowed characters.",
		)


def test_sign_in_form_rejects_recovery_codes_of_the_wrong_length():
	for code in ["ABCDEFGHJKLMNPQ", "ABCDEFGHJKLMNPQRS"]:
		_, errors = SignInForm.validate(Input({"recovery_code": code}))

		assert_eq(errors.first("recovery_code"), "Recovery code must be 16 characters.")


def test_sign_in_form_accepts_a_lowercase_recovery_code_with_spaces():
	form, errors = SignInForm.validate(Input({"recovery_code": "abcd efgh jkmn pqrs"}))

	assert_that(not errors)
	assert_eq(form.recovery_code, "ABCDEFGHJKMNPQRS")


def test_delete_signs_out():
	with TestApplication() as app:
		user = app.store.create(User, name="User")
		app.sign_in(user)

		res = app.client.delete("/sessions/")
		boards = app.client.get("/boards/")

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/sessions/new")
		assert_eq(boards.status_code, 302)


def test_guard_redirects_to_new_session():
	with TestApplication() as app:
		res = app.client.get("/boards/")

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/sessions/new")


def test_stored_session_remains_authenticated():
	with TestApplication() as app:
		user = app.store.create(User, name="User")
		helios.auth.test.sign_in(app.client, user)
		token = assert_not_none(app.client.get_cookie("session_id")).value

		res = app.client.get("/boards/")

		assert_eq(res.status_code, 200)
		assert_eq(assert_not_none(app.client.get_cookie("session_id")).value, token)


def test_expired_session_is_rejected():
	with TestApplication() as app:
		user = app.store.create(User, name="User")
		with app.client.session() as session:
			session[SESSION_KEY] = str(user.id)
			session.last_active_at = datetime.now(UTC) - timedelta(days=31)

		res = app.client.get("/boards/")

		assert_eq(res.status_code, 302)
		assert_is(app.client.get_cookie("session_id"), None)
