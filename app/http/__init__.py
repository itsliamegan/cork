from helios.http import Method, Response
from helios.routing import Group, Pattern, Route

from app.http import auths, boards, home, pins, settings


def ensure_signed_in(req, ctx, **params):
	if not ctx.auth.is_signed_in():
		return Response.redirect("/sign-in")


routes = [
	Route(Method.GET, Pattern("/sign-in"), auths.new),
	Route(Method.POST, Pattern("/sign-in"), auths.create),
	Group(
		guards=[ensure_signed_in],
		routes=[
			Route(Method.POST, Pattern("/sign-out"), auths.delete),
			Route(Method.GET, Pattern("/"), home.show),
			Route(Method.GET, Pattern("/settings"), settings.show),
			Route(Method.PUT, Pattern("/settings"), settings.update),
			Group(
				prefix="/boards",
				routes=[
					Route(Method.GET, Pattern("/"), boards.index),
					Route(Method.POST, Pattern("/"), boards.create),
					Route(Method.GET, Pattern("/new"), boards.new),
					Route(Method.GET, Pattern("/{id:uuid}"), boards.show),
					Route(Method.GET, Pattern("/{id:uuid}/edit"), boards.edit),
					Route(Method.PUT, Pattern("/{id:uuid}"), boards.update),
					Route(Method.DELETE, Pattern("/{id:uuid}"), boards.delete),
					Route(Method.GET, Pattern("/{id:uuid}/pins/new"), pins.new),
				],
			),
			Group(
				prefix="/pins",
				routes=[
					Route(Method.POST, Pattern("/"), pins.create),
					Route(Method.GET, Pattern("/{id:uuid}/edit"), pins.edit),
					Route(Method.PUT, Pattern("/{id:uuid}"), pins.update),
					Route(Method.DELETE, Pattern("/{id:uuid}"), pins.delete),
				],
			),
		],
	),
]
