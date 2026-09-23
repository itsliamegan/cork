from datetime import timedelta
from pathlib import Path

from helios.config import Config
import helios.database.config
from helios.http import URL
import helios.limit.config
import helios.session.config
import helios.views.config

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = Path(ROOT_DIR, ".env")
DATA_DIR = Path("/var/lib/cork")


class Config(Config):
	def __init__(self, values: dict[str, str]):
		super().__init__(values)

		self.base_url = self.url("APP_BASE_URL", URL("http://localhost:4000"))
		self.rate_limit = helios.limit.config.Config(
			header=self.text("APP_RATE_LIMIT_HEADER", "X-Forwarded-For"),
			limit=int(self.text("APP_RATE_LIMIT_REQUESTS", "30")),
			window=timedelta(
				seconds=int(self.text("APP_RATE_LIMIT_WINDOW_SECONDS", "300"))
			),
		)
		self.database = helios.database.config.Config(
			self.path(
				"APP_DATABASE_FILE",
				Path(DATA_DIR, "store.sqlite"),
			)
		)
		self.views = helios.views.config.Config(
			self.path(
				"APP_VIEWS_DIR",
				Path(ROOT_DIR, "app", "views"),
			)
		)
		self.session = helios.session.config.Config()
		self.session_file = self.path(
			"APP_SESSION_STORE_FILE",
			Path(DATA_DIR, "sessions.json"),
		)
		self.session_lock_file = self.path(
			"APP_SESSION_LOCK_FILE",
			Path(DATA_DIR, "sessions.lock"),
		)
