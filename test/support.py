import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from uuid import uuid4

from helios.auth.password import Digest
from helios.database import Store
import helios.database.config
from helios.database.sqlite import connect
from helios.wsgi.test import TestClient
from luna.test.assertion import assert_eq

from app import User, models
from app.config import Config, ROOT_DIR
from app.wsgi import Application
from lib.migrate import Migrations, Migrator

Digest.method = "pbkdf2:sha256:1"

MIGRATIONS_DIR = Path(ROOT_DIR, "database", "migrations")


class TestStore:
	def __init__(self):
		self.directory = TemporaryDirectory()
		try:
			config = helios.database.config.Config(
				Path(self.directory.name, "store.sqlite")
			)
			Migrator(config, Migrations.load(MIGRATIONS_DIR)).apply()
			self.connection = connect(config)
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

			config = Config.load(
				{
					"APP_DATABASE_FILE": str(self.dir.joinpath("store.sqlite")),
					"APP_SESSION_STORE_FILE": str(self.sessions_file),
					"APP_SESSION_LOCK_FILE": str(self.dir.joinpath("sessions.lock")),
				}
			)
			Migrator(config.database, Migrations.load(MIGRATIONS_DIR)).apply()
			super().__init__(config)
			self.connection = connect(config.database)
			self.refresh()
			self.client = TestClient(self)
		except Exception:
			self.temp_dir.cleanup()
			raise

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, traceback):
		try:
			self.connection.close()
			self.close()
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
