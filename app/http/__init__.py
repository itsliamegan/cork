from helios.http import Method, Response
from helios.routing import Pattern, Route

import app.http.auths as auths
import app.http.home as home
import app.http.settings as settings
import app.http.boards as boards
import app.http.boards.shares as shares
import app.http.pins as pins

def ensure_signed_in(req, ctx):
	is_secure_route = not req.url.path.startswith("/sign-in")
	is_signed_out = not ctx.auth.is_signed_in()
	if is_secure_route and is_signed_out:
		return Response.redirect("/sign-in")

guards = [
	ensure_signed_in,
]

routes = [
	Route(Method.GET, Pattern("/sign-in"), auths.new),
	Route(Method.POST, Pattern("/sign-in"), auths.create),
	Route(Method.POST, Pattern("/sign-out"), auths.delete),

	Route(Method.GET, Pattern("/"), home.show),
	Route(Method.GET, Pattern("/settings"), settings.show),

	Route(Method.GET, Pattern("/boards/"), boards.index),
	Route(Method.POST, Pattern("/boards/"), boards.create),
	Route(Method.GET, Pattern("/boards/new"), boards.new),
	Route(Method.GET, Pattern("/boards/{id:uuid}"), boards.show),
	Route(Method.GET, Pattern("/boards/{id:uuid}/edit"), boards.edit),
	Route(Method.PUT, Pattern("/boards/{id:uuid}"), boards.update),
	Route(Method.DELETE, Pattern("/boards/{id:uuid}"), boards.delete),
	Route(Method.GET, Pattern("/boards/{id:uuid}/pins/new"), pins.new),
	Route(Method.GET, Pattern("/boards/{id:uuid}/shares"), shares.index),
	Route(Method.POST, Pattern("/boards/{id:uuid}/shares"), shares.create),
	Route(Method.DELETE, Pattern("/boards/{id:uuid}/shares/{share_id:uuid}"), shares.delete),

	Route(Method.POST, Pattern("/pins/"), pins.create),
	Route(Method.GET, Pattern("/pins/{id:uuid}/edit"), pins.edit),
	Route(Method.PUT, Pattern("/pins/{id:uuid}"), pins.update),
	Route(Method.DELETE, Pattern("/pins/{id:uuid}"), pins.delete),
]
