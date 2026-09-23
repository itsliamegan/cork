from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from luna.test.assertion import assert_eq

from app.config import Config, ROOT_DIR


def test_declares_application_defaults():
	config = Config.load({})

	assert_eq(
		config.database.database_file,
		ROOT_DIR.joinpath("data", "store.sqlite"),
	)
	assert_eq(config.views.dir, ROOT_DIR.joinpath("app", "views"))
	assert_eq(config.session_file, ROOT_DIR.joinpath("data", "sessions.json"))
	assert_eq(config.session_lock_file, ROOT_DIR.joinpath("data", "sessions.lock"))


def test_loads_component_config_from_environment():
	config = Config.load(
		{
			"APP_DATABASE_FILE": "/srv/cork/store.sqlite",
			"APP_VIEWS_DIR": "/srv/cork/views",
			"APP_SESSION_STORE_FILE": "/srv/cork/sessions.json",
			"APP_SESSION_LOCK_FILE": "/srv/cork/sessions.lock",
		}
	)

	assert_eq(config.database.database_file, Path("/srv/cork/store.sqlite"))
	assert_eq(config.views.dir, Path("/srv/cork/views"))
	assert_eq(config.session_file, Path("/srv/cork/sessions.json"))
	assert_eq(config.session_lock_file, Path("/srv/cork/sessions.lock"))


def test_loads_selected_dotenv_with_process_environment_precedence():
	with TemporaryDirectory() as dir:
		env_file = Path(dir, ".env")
		env_file.write_text(
			"APP_DATABASE_FILE=/dotenv/store.sqlite\n"
			"APP_SESSION_STORE_FILE=/dotenv/sessions.json\n"
			"APP_SESSION_LOCK_FILE=/dotenv/sessions.lock\n"
		)
		config = Config.load(
			{
				"APP_DATABASE_FILE": "/environment/store.sqlite",
				"APP_SESSION_LOCK_FILE": "/environment/sessions.lock",
			},
			env_file,
		)

	assert_eq(config.database.database_file, Path("/environment/store.sqlite"))
	assert_eq(config.session_file, Path("/dotenv/sessions.json"))
	assert_eq(config.session_lock_file, Path("/environment/sessions.lock"))


def test_importing_config_does_not_import_jinja():
	result = subprocess.run(
		[
			sys.executable,
			"-c",
			"import sys; import app.config; assert not "
			+ "any(name.startswith('jinja2') for name in sys.modules)",
		],
		check=False,
	)

	assert_eq(result.returncode, 0)
