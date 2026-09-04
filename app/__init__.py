from pathlib import Path

import helios.flash
import helios.session
import helios.store
import helios.views
from helios.wsgi import Application

from app.data import schema, Pin
from app.http import guards, routes

from helios.app import Component
class Guards(Component):
	def __init__(self, guards):
		self.guards = guards

	def __call__(self, req, ctx, next):
		for guard in self.guards:
			res = guard(req, ctx)
			if res:
				return res
			else:
				return next(req, ctx)

app = Application(routes, [
	helios.store.Component(Path("data", "store.json"), schema),
	helios.views.Component(Path("app", "views")),
	helios.session.Component(Path("data", "sessions.json")),
	helios.flash.Component(),
	Guards(guards),
])
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
		use_reloader = True,
		extra_files = [*asset_files, *view_files],
		static_files = {"/static": str(Path("public", "static"))}
	)
