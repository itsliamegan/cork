from pathlib import Path

import lib.flash
import lib.session
import lib.store
import lib.views
from lib.wsgi import Application

from app.data import Pin, model_types
from app.http import routes

app = Application(routes, [
	lib.store.Component(Path("data", "store.json"), model_types),
	lib.views.Component(Path("app", "views")),
	lib.session.Component(Path("data", "sessions.json")),
	lib.flash.Component()
])
app.boot()
