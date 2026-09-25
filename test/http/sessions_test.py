from datetime import UTC, datetime, timedelta
import json
from uuid import uuid4

from helios.auth.password import Digest
from helios.http import Input
from luna.test.assertion import assert_eq, assert_that

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
		form = app.client.get(res.headers["Location"])

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/sessions/new")
		assert_that("Recovery code is invalid." in form.text)


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


def test_sign_in_form_rejects_malformed_recovery_codes():
	for code in [
		"ABCDEFGHJKLMNPQ",
		"ABCDEFGHJKLMNPQRS",
		"ABCDEFGHJKLMNPQ0",
		"ABCDEFGHJKLMNPQ1",
		"ABCDEFGHJKLMNPQI",
		"ABCDEFGHJKLMNPQO",
		"ABCD-EFGH-JKLM-NP",
	]:
		_, errors = SignInForm.validate(Input({"recovery_code": code}))

		assert_eq(errors.first("recovery_code"), "Recovery code is invalid.")


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
		session_id = uuid4()
		app.sessions_file.write_text(
			json.dumps(
				{
					str(session_id): {
						"items": {"_user_id": str(user.id)},
						"last_active_at": None,
					}
				}
			)
		)
		app.client.set_cookie("session_id", str(session_id))

		res = app.client.get("/boards/")
		persisted = json.loads(app.sessions_file.read_text())

		assert_eq(res.status_code, 200)
		assert_eq(app.client.get_cookie("session_id").value, str(session_id))
		assert_that(str(session_id) in persisted)


def test_expired_session_is_rejected():
	with TestApplication() as app:
		user = app.store.create(User, name="User")
		session_id = uuid4()
		app.sessions_file.write_text(
			json.dumps(
				{
					str(session_id): {
						"items": {"_user_id": str(user.id)},
						"last_active_at": (
							datetime.now(UTC) - timedelta(days=31)
						).isoformat(),
					}
				}
			)
		)
		app.client.set_cookie("session_id", str(session_id))

		res = app.client.get("/boards/")
		persisted = json.loads(app.sessions_file.read_text())

		assert_eq(res.status_code, 302)
		assert_that(str(session_id) not in persisted)
