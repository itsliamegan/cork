from datetime import timedelta
from pathlib import Path

from helios.config import Config
import helios.data.config
from helios.http import URL
import helios.limit.config
import helios.persist.config
import helios.session.config
import helios.views.config

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = Path(ROOT_DIR, ".env")


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
		self.persist = helios.persist.config.Config(
			self.path(
				"APP_PERSIST_LOCK_FILE",
				Path(ROOT_DIR, "data", "persistence.lock"),
			)
		)
		self.data = helios.data.config.Config(
			self.path(
				"APP_DATA_STORE_FILE",
				Path(ROOT_DIR, "data", "store.json"),
			)
		)
		self.views = helios.views.config.Config(
			self.path(
				"APP_VIEWS_DIR",
				Path(ROOT_DIR, "app", "views"),
			)
		)
		self.session = helios.session.config.Config(
			self.path(
				"APP_SESSION_STORE_FILE",
				Path(ROOT_DIR, "data", "sessions.json"),
			)
		)
