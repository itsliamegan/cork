from pathlib import Path

import helios.auth
import helios.data
import helios.flash
import helios.persist
from helios.routing import Router
import helios.session
import helios.views
from helios.wsgi import Application

from app.data import User, schema
from app.http import routes

ROOT_DIR = Path(__file__).resolve().parent.parent
STORE_FILE = ROOT_DIR.joinpath("data", "store.json")
SESSIONS_FILE = ROOT_DIR.joinpath("data", "sessions.json")
LOCK_FILE = ROOT_DIR.joinpath("data", "persistence.lock")
VIEWS_DIR = ROOT_DIR.joinpath("app", "views")


class Application(Application):
	def __init__(
		self,
		store_file: Path = STORE_FILE,
		sessions_file: Path = SESSIONS_FILE,
		lock_file: Path = LOCK_FILE,
		views_dir: Path = VIEWS_DIR,
	):
		self.persistence = helios.persist.Files(lock_file)
		self.store_data = self.persistence.json(store_file, helios.data.Format(schema))
		self.sessions_data = self.persistence.json(
			sessions_file, helios.session.Format()
		)
		super().__init__(
			Router(routes),
			[
				helios.persist.Component(self.persistence),
				helios.data.Component(self.store_data),
				helios.views.Component(views_dir),
				helios.session.Component(self.sessions_data),
				helios.flash.Component(),
				helios.auth.Component(User),
			],
		)


app = Application()
app.boot()


def main():
	from pathlib import Path

	from werkzeug.serving import run_simple

	asset_files = [str(file) for file in Path("app", "assets").glob("**/*")]
	view_files = [str(file) for file in Path("app", "views").glob("**/*.html")]

	run_simple(
		"0.0.0.0",
		4000,
		app,
		use_reloader=True,
		extra_files=[*asset_files, *view_files],
		static_files={"/static": str(Path("public", "static"))},
	)
