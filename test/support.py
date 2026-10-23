from collections.abc import Iterable
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from helios.auth.password import Digest
from helios.config import Environment
from helios.database import Model, Store
import helios.database.config
from helios.database.migration import Migrations, Migrator
from helios.database.sqlite import Connection
from helios.wsgi.test import TestClient
from luna.test.assertion import assert_eq

from app import User, config, models
from app.wsgi import Application

Digest.method = "pbkdf2:sha256:1"


def ids(records: Iterable[Model]) -> list[UUID]:
	return [record.id for record in records]


class TestStore:
	def __init__(self):
		self.directory = TemporaryDirectory()
		try:
			database = config.database(
				Environment(
					{
						"APP_DATABASE_FILE": str(
							Path(self.directory.name, "store.sqlite")
						)
					}
				)
			)
			Migrator(
				database.path,
				Migrations.load(database.migrations),
				busy_timeout=database.busy_timeout,
			).apply()
			self.connection = Connection.open(database.path, database.busy_timeout)
		except Exception:
			self.directory.cleanup()
			raise

	def __enter__(self) -> Store:
		return Store(self.connection, models)

	def __exit__(self, exc_type, exc, traceback):
		try:
			self.connection.close()
		finally:
			self.directory.cleanup()


class TestApplication(Application):
	def __init__(self):
		self.temp_dir = TemporaryDirectory()
		try:
			self.dir = Path(self.temp_dir.name)
			self.sessions_file = self.dir.joinpath("sessions.json")
			self.sessions_file.write_text("{}")

			super().__init__(
				Environment(
					{
						"APP_DATABASE_FILE": str(self.dir.joinpath("store.sqlite")),
						"APP_SESSION_STORE_FILE": str(self.sessions_file),
						"APP_SESSION_LOCK_FILE": str(
							self.dir.joinpath("sessions.lock")
						),
					}
				)
			)
			self.container.get(Migrator).apply()
			database = self.container.get(helios.database.config.Config)
			self.boot()
			self.connection = Connection.open(database.path, database.busy_timeout)
			self.refresh()
			self.client = TestClient(self)
		except Exception:
			self.temp_dir.cleanup()
			raise

	def __exit__(self, exception_type, exception, traceback):
		try:
			self.connection.close()
			super().__exit__(exception_type, exception, traceback)
		finally:
			self.temp_dir.cleanup()

	def refresh(self):
		"""Replace the store, so later reads see what a request committed."""

		self.store = Store(self.connection, models)

	def sign_in(self, user: User):
		session_id = uuid4()
		self.sessions_file.write_text(
			json.dumps(
				{
					str(session_id): {
						"items": {"_user_id": str(user.id)},
						"last_active_at": None,
					}
				}
			)
		)
		self.client.set_cookie("session_id", str(session_id))
		res = self.client.get("/boards/")
		assert_eq(res.status_code, 200)


class TestClient(TestClient):
	def __init__(self, app: TestApplication):
		super().__init__(app)
		self.app = app

	def request(self, *args, **kwargs):
		try:
			return super().request(*args, **kwargs)
		finally:
			self.app.refresh()


def checked_values(html: str, name: str) -> set[str]:
	"""Return the values of the checked inputs named `name` in `html`."""

	values = set()
	for tag in re.findall(r"<input\b[^>]*>", html):
		value = re.search(r'\svalue="([^"]*)"', tag)
		if (
			f'name="{name}"' in tag
			and re.search(r"\schecked\b", tag)
			and value is not None
		):
			values.add(value.group(1))
	return values
