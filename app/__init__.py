from pathlib import Path

import helios.flash
import helios.session
import helios.store
import helios.views
from helios.wsgi import Application

from app.data import schema, Pin
from app.http import routes

app = Application(routes, [
	helios.store.Component(Path("data", "store.json"), schema),
	helios.views.Component(Path("app", "views")),
	helios.session.Component(Path("data", "sessions.json")),
	helios.flash.Component()
])
app.boot()
