from datetime import timedelta
from pathlib import Path

import helios.app
from helios.config import Environment
import helios.database.config
from helios.http import URL
import helios.limit.config
import helios.session.config
import helios.session.file
import helios.view.config

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = Path(ROOT_DIR, ".env")
DATA_DIR = Path("/var/lib/cork")
BASE_URL = URL.parse("http://localhost:4000")


def application(environment: Environment) -> helios.app.Config:
	return helios.app.Config(
		base_url=environment.url("APP_BASE_URL", BASE_URL),
	)


def views(environment: Environment) -> helios.view.config.Config:
	return helios.view.config.Config(
		environment.path("APP_VIEWS_DIR", Path(ROOT_DIR, "app", "views")),
	)


def database(environment: Environment) -> helios.database.config.Config:
	return helios.database.config.Config(
		environment.path("APP_DATABASE_FILE", Path(DATA_DIR, "store.sqlite")),
	)


def session(environment: Environment) -> helios.session.config.Config:
	base_url = environment.url("APP_BASE_URL", BASE_URL)
	return helios.session.config.Config(
		secure=base_url.scheme == "https",
	)


def session_driver(environment: Environment) -> helios.session.file.Driver:
	return helios.session.file.Driver(
		environment.path("APP_SESSION_STORE_FILE", Path(DATA_DIR, "sessions.json")),
		environment.path("APP_SESSION_LOCK_FILE", Path(DATA_DIR, "sessions.lock")),
	)


def rate_limit(environment: Environment) -> helios.limit.config.Config:
	return helios.limit.config.Config(
		header=environment.text("APP_RATE_LIMIT_HEADER", "X-Forwarded-For"),
		limit=int(environment.text("APP_RATE_LIMIT_REQUESTS", "30")),
		window=timedelta(
			seconds=int(environment.text("APP_RATE_LIMIT_WINDOW_SECONDS", "300")),
		),
	)
