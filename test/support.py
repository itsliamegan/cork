from pathlib import Path
from tempfile import TemporaryDirectory

from helios.store import load, save
from helios.wsgi import TestClient
from luna.test.assertion import assert_eq

from app import Application
from app.data import User, schema


class TestApplication(Application):
	def __init__(self):
		self.temp_dir = TemporaryDirectory()
		try:
			self.dir = Path(self.temp_dir.name)
			self.store_file = self.dir.joinpath("store.json")
			self.sessions_file = self.dir.joinpath("sessions.json")
			self.store_file.write_text("[]")
			self.sessions_file.write_text("{}")

			super().__init__(
				store_file=self.store_file,
				sessions_file=self.sessions_file,
			)
			self.boot()
			self.store = load(self.store_file, schema)
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
		save(self.app.store_file, self.app.store)
		try:
			return super().request(*args, **kwargs)
		finally:
			self.app.store = load(self.app.store_file, schema)
