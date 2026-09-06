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

app = Application(
	Router(routes),
	[
		helios.store.Component(Path("data", "store.json"), schema),
		helios.views.Component(Path("app", "views")),
		helios.session.Component(Path("data", "sessions.json")),
		helios.flash.Component(),
		helios.auth.Component(User),
	],
)
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
