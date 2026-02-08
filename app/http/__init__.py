from lib.http import Method
from lib.routing import Pattern, Route

import app.http.pins as pins
import app.http.hides as hides

routes = [
	Route(Method.GET, Pattern("/"), pins.index),
	Route(Method.POST, Pattern("/pins/"), pins.store),
	Route(Method.GET, Pattern("/pins/new"), pins.new),
	Route(Method.GET, Pattern("/pins/{id}/edit"), pins.edit),
	Route(Method.PUT, Pattern("/pins/{id}"), pins.update),
	Route(Method.POST, Pattern("/pins/{id}/hide"), hides.store),
	Route(Method.DELETE, Pattern("/pins/{id}/hide"), hides.destroy)
]
