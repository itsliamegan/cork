from pathlib import Path

import helios.auth
import helios.data
import helios.flash
import helios.persist
from helios.routing import Router
import helios.session
import helios.views
from helios.wsgi import Application

from app.config import Config
from app.data import User, schema
from app.http import routes


class Application(Application):
	def __init__(self, config: Config):
		files = helios.persist.Files(config.persist)
		store_data = files.json(config.data.store_file, helios.data.Format(schema))
		sessions_data = files.json(config.session.store_file, helios.session.Format())
		super().__init__(
			Router(routes),
			[
				helios.persist.Component(files),
				helios.data.Component(store_data),
				helios.views.Component(config.views),
				helios.session.Component(sessions_data),
				helios.flash.Component(),
				helios.auth.Component(User),
			],
		)


app = Application(Config.load())
app.boot()


def main():

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
