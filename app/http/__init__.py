from helios.auth import Authenticator
from helios.http import Method, Response
from helios.routing import Group, Pattern, Route

from app.http import (
	boards,
	home,
	invites,
	orderings,
	pins,
	recoveries,
	redemptions,
	sessions,
	settings,
)


def ensure_signed_in(req, ctx, **params):
	auth = ctx.get(Authenticator)

	if not auth.is_signed_in():
		return Response.redirect("/sessions/new")


routes = [
	Group(
		prefix="/sessions",
		routes=[
			Route(Method.POST, Pattern("/"), sessions.create),
			Route(Method.GET, Pattern("/new"), sessions.new),
			Route(
				Method.DELETE,
				Pattern("/"),
				sessions.delete,
				guards=[ensure_signed_in],
			),
		],
	),
	Group(
		prefix="/redemptions",
		routes=[
			Route(Method.POST, Pattern("/"), redemptions.create),
			Route(Method.GET, Pattern("/new"), redemptions.new),
		],
	),
	Group(
		guards=[ensure_signed_in],
		routes=[
			Route(Method.GET, Pattern("/"), home.show),
			Route(Method.GET, Pattern("/settings"), settings.show),
			Route(Method.PUT, Pattern("/settings"), settings.update),
			Group(
				prefix="/invites",
				routes=[
					Route(Method.POST, Pattern("/"), invites.create),
					Route(Method.GET, Pattern("/{id:uuid}"), invites.show),
				],
			),
			Group(
				prefix="/recoveries",
				routes=[
					Route(Method.POST, Pattern("/"), recoveries.create),
					Route(Method.GET, Pattern("/{id:uuid}"), recoveries.show),
				],
			),
			Route(Method.PUT, Pattern("/orderings"), orderings.update),
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
					Route(Method.GET, Pattern("/{id:uuid}"), pins.show),
					Route(Method.GET, Pattern("/{id:uuid}/edit"), pins.edit),
					Route(Method.PUT, Pattern("/{id:uuid}"), pins.update),
					Route(Method.DELETE, Pattern("/{id:uuid}"), pins.delete),
				],
			),
		],
	),
]
