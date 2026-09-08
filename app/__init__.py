from pathlib import Path

import helios.auth
import helios.flash
from helios.routing import Router
import helios.session
import helios.store
import helios.views
from helios.wsgi import Application

from app.data import User, schema
from app.http import routes

ROOT_DIR = Path(__file__).resolve().parent.parent
STORE_FILE = ROOT_DIR.joinpath("data", "store.json")
SESSIONS_FILE = ROOT_DIR.joinpath("data", "sessions.json")
VIEWS_DIR = ROOT_DIR.joinpath("app", "views")


class Application(Application):
	def __init__(
		self,
		store_file: Path = STORE_FILE,
		sessions_file: Path = SESSIONS_FILE,
		views_dir: Path = VIEWS_DIR,
	):
		super().__init__(
			Router(routes),
			[
				helios.store.Component(store_file, schema),
				helios.views.Component(views_dir),
				helios.session.Component(sessions_file),
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
