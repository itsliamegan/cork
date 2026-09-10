from pathlib import Path
from tempfile import TemporaryDirectory

from helios import data, persist, session
from helios.wsgi import TestClient
from luna.test.assertion import assert_eq

from app import Application
from app.config import Config, DEFAULT_CONFIG
from app.data import User, schema


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

			config = Config(
				persist=persist.Config(self.lock_file),
				data=data.Config(self.store_file),
				views=DEFAULT_CONFIG.views,
				session=session.Config(self.sessions_file),
			)
			self.persistence = persist.Files(config.persist)
			self.store_data = self.persistence.json(
				config.data.store_file, data.Format(schema)
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
		res = self.client.post(
			"/sign-in",
			form={"user_id": str(user.id)},
		)
		assert_eq(res.status_code, 302)


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
