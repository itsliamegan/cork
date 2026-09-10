from pathlib import Path
from unittest.mock import patch

from luna.test.assertion import assert_eq

from app.config import Config, DEFAULT_CONFIG, ROOT_DIR


def test_declares_application_defaults():
	assert_eq(
		DEFAULT_CONFIG.persist.lock_file,
		ROOT_DIR.joinpath("data", "persistence.lock"),
	)
	assert_eq(DEFAULT_CONFIG.data.store_file, ROOT_DIR.joinpath("data", "store.json"))
	assert_eq(DEFAULT_CONFIG.views.dir, ROOT_DIR.joinpath("app", "views"))
	assert_eq(
		DEFAULT_CONFIG.session.store_file,
		ROOT_DIR.joinpath("data", "sessions.json"),
	)


def test_loads_component_config_from_environment():
	config = Config.from_env(
		{
			"CORK_PERSIST_LOCK_FILE": "/srv/cork/persistence.lock",
			"CORK_DATA_STORE_FILE": "/srv/cork/store.json",
			"CORK_VIEWS_DIR": "/srv/cork/views",
			"CORK_SESSION_STORE_FILE": "/srv/cork/sessions.json",
		}
	)

	assert_eq(config.persist.lock_file, Path("/srv/cork/persistence.lock"))
	assert_eq(config.data.store_file, Path("/srv/cork/store.json"))
	assert_eq(config.views.dir, Path("/srv/cork/views"))
	assert_eq(config.session.store_file, Path("/srv/cork/sessions.json"))


def test_loads_dotenv_with_process_environment_precedence():
	with patch(
		"app.config.dotenv_values",
		return_value={
			"CORK_DATA_STORE_FILE": "/dotenv/store.json",
			"CORK_SESSION_STORE_FILE": "/dotenv/sessions.json",
		},
	):
		config = Config.load({"CORK_DATA_STORE_FILE": "/environment/store.json"})

	assert_eq(config.data.store_file, Path("/environment/store.json"))
	assert_eq(config.session.store_file, Path("/dotenv/sessions.json"))
