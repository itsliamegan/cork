from pathlib import Path

from helios.config import Config
import helios.data.config
import helios.persist.config
import helios.session.config
import helios.views.config

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = Path(ROOT_DIR, ".env")


class Config(Config):
	def __init__(self, values: dict[str, str]):
		super().__init__(values)

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
