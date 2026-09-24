from datetime import UTC, datetime, timedelta
import json
from uuid import uuid4

from helios.auth.password import Digest
from luna.test.assertion import assert_eq, assert_that

from app import Recovery, User
from test.support import TestApplication


def test_new_renders():
	with TestApplication() as app:
		res = app.client.get("/sessions/new")

		assert_eq(res.status_code, 200)


def test_new_redirects_when_signed_in():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.sign_in(user)

		res = app.client.get("/sessions/new")

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/boards/")


def test_create_normalizes_recovery_code():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.store.create(
			Recovery,
			user_id=user.id,
			code=Recovery.Code(Digest.generate("ABCDEFGHJKLMNPQR")),
		)

		res = app.client.post(
			"/sessions/",
			form={"recovery_code": "  abcd efgh\t jklm\nnpqr  "},
		)

		assert_eq(res.status_code, 302)
		assert_that(app.client.get_cookie("session_id") is not None)


def test_create_rejects_invalid_recovery_code():
	with TestApplication() as app:
		app.store.create(User, name="Alice")

		res = app.client.post("/sessions/", form={"recovery_code": "XXXXXXXXXX"})
		form = app.client.get(res.headers["Location"])

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/sessions/new")
		assert_that("That recovery code is invalid." in form.text)


def test_delete_signs_out():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
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
		user = app.store.create(User, name="Alice")
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
		user = app.store.create(User, name="Alice")
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
