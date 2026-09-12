import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from helios.auth.password import Digest
from helios.data.store import Format
from helios.persist.files import Files
from helios.wsgi import TestClient
from luna.test.assertion import assert_eq

from app.config import Config
from app.data import User, schema
from app.wsgi import Application

Digest.method = "pbkdf2:sha256:1"


class TestApplication(Application):
	def __init__(self):
		self.temp_dir = TemporaryDirectory()
		try:
			self.dir = Path(self.temp_dir.name)
			self.store_file = self.dir.joinpath("store.json")
			self.sessions_file = self.dir.joinpath("sessions.json")
			self.lock_file = self.dir.joinpath("persistence.lock")
			self.store_file.write_text("[]")
			self.sessions_file.write_text("{}")

			config = Config.load(
				{
					"APP_PERSIST_LOCK_FILE": str(self.lock_file),
					"APP_DATA_STORE_FILE": str(self.store_file),
					"APP_SESSION_STORE_FILE": str(self.sessions_file),
				}
			)
			self.persistence = Files(config.persist)
			self.store_data = self.persistence.json(
				config.data.store_file, Format(schema)
			)
			super().__init__(config)
			self.boot()
			with self.persistence.lock() as scope:
				self.store = scope.open(self.store_data).load()
			self.client = TestClient(self)
		except Exception:
			self.temp_dir.cleanup()
			raise

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, traceback):
		self.temp_dir.cleanup()

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
		with self.app.persistence.lock() as scope:
			scope.open(self.app.store_data).save(self.app.store)
			self.app.store.pending.clear()
		try:
			return super().request(*args, **kwargs)
		finally:
			with self.app.persistence.lock() as scope:
				self.app.store = scope.open(self.app.store_data).load()
