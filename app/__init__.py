from pathlib import Path

import lux.flash
import lux.session
import lux.store
import lux.views
from lux.wsgi import Application

from app.data import schema, Pin
from app.http import routes

app = Application(routes, [
	lux.store.Component(Path("data", "store.json"), schema),
	lux.views.Component(Path("app", "views")),
	lux.session.Component(Path("data", "sessions.json")),
	lux.flash.Component()
])
app.boot()
