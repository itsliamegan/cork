from collections.abc import Mapping
import os
from pathlib import Path
from typing import Self

from dotenv import dotenv_values
from helios import data, persist, session, views

ROOT_DIR = Path(__file__).resolve().parent.parent


class Config:
	def __init__(
		self,
		persist: persist.Config,
		data: data.Config,
		views: views.Config,
		session: session.Config,
	):
		self.persist = persist
		self.data = data
		self.views = views
		self.session = session

	@classmethod
	def from_env(cls, environ: Mapping[str, str]) -> Self:
		return cls(
			persist=persist.Config(
				Path(
					environ.get(
						"APP_PERSIST_LOCK_FILE",
						DEFAULT_CONFIG.persist.lock_file,
					)
				)
			),
			data=data.Config(
				Path(
					environ.get(
						"APP_DATA_STORE_FILE",
						DEFAULT_CONFIG.data.store_file,
					)
				)
			),
			views=views.Config(
				Path(environ.get("APP_VIEWS_DIR", DEFAULT_CONFIG.views.dir))
			),
			session=session.Config(
				Path(
					environ.get(
						"APP_SESSION_STORE_FILE",
						DEFAULT_CONFIG.session.store_file,
					)
				)
			),
		)

	@classmethod
	def load(cls, environ: Mapping[str, str] | None = None) -> Self:
		if environ is None:
			environ = os.environ
		values = {
			name: value
			for name, value in dotenv_values(ROOT_DIR.joinpath(".env")).items()
			if value is not None
		}
		values.update(environ)
		return cls.from_env(values)


DEFAULT_CONFIG = Config(
	persist=persist.Config(ROOT_DIR.joinpath("data", "persistence.lock")),
	data=data.Config(ROOT_DIR.joinpath("data", "store.json")),
	views=views.Config(ROOT_DIR.joinpath("app", "views")),
	session=session.Config(ROOT_DIR.joinpath("data", "sessions.json")),
)
