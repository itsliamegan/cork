from pathlib import Path

import lib.store
import lib.views
from lib.wsgi import Application

from app.data import Pin, models
from app.http import routes

app = Application(routes, [
	lib.store.Component(Path("data", "store.json"), models),
	lib.views.Component(Path("app", "views"))
])
app.boot()
