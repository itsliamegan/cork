from lux.http import Method
from lux.routing import Pattern, Route

import app.http.auths as auths
import app.http.home as home
import app.http.settings as settings
import app.http.boards as boards
import app.http.pins as pins

routes = [
	Route(Method.GET, Pattern("/sign-in"), auths.new),
	Route(Method.POST, Pattern("/sign-in"), auths.create),
	Route(Method.POST, Pattern("/sign-out"), auths.delete),

	Route(Method.GET, Pattern("/"), home.show),
	Route(Method.GET, Pattern("/settings"), settings.show),

	Route(Method.GET, Pattern("/boards/"), boards.index),
	Route(Method.POST, Pattern("/boards/"), boards.create),
	Route(Method.GET, Pattern("/boards/new"), boards.new),
	Route(Method.GET, Pattern("/boards/{id}"), boards.show),
	Route(Method.GET, Pattern("/boards/{id}/edit"), boards.edit),
	Route(Method.PUT, Pattern("/boards/{id}"), boards.update),
	Route(Method.DELETE, Pattern("/boards/{id}"), boards.delete),
	Route(Method.GET, Pattern("/boards/{id}/pins/new"), pins.new),

	Route(Method.POST, Pattern("/pins/"), pins.create),
	Route(Method.GET, Pattern("/pins/{id}/edit"), pins.edit),
	Route(Method.PUT, Pattern("/pins/{id}"), pins.update),
	Route(Method.DELETE, Pattern("/pins/{id}"), pins.delete),
]
