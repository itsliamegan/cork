from helios.auth import Authenticator
from helios.http import Method, Response
from helios.routing import Group, Pattern, Route

from app.http import (
	boards,
	home,
	invites,
	orderings,
	pins,
	placements,
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
			Route(Method.POST, Pattern("/"), sessions.create, name="sessions.create"),
			Route(Method.GET, Pattern("/new"), sessions.new, name="sessions.new"),
			Route(
				Method.DELETE,
				Pattern("/"),
				sessions.delete,
				name="sessions.delete",
				guards=[ensure_signed_in],
			),
		],
	),
	Group(
		prefix="/redemptions",
		routes=[
			Route(
				Method.POST, Pattern("/"), redemptions.create, name="redemptions.create"
			),
			Route(Method.GET, Pattern("/new"), redemptions.new, name="redemptions.new"),
		],
	),
	Group(
		guards=[ensure_signed_in],
		routes=[
			Route(Method.GET, Pattern("/"), home.show, name="home.show"),
			Route(
				Method.GET, Pattern("/settings"), settings.show, name="settings.show"
			),
			Route(
				Method.PUT,
				Pattern("/settings"),
				settings.update,
				name="settings.update",
			),
			Group(
				prefix="/invites",
				routes=[
					Route(
						Method.POST, Pattern("/"), invites.create, name="invites.create"
					),
					Route(
						Method.GET,
						Pattern("/{id:uuid}"),
						invites.show,
						name="invites.show",
					),
				],
			),
			Group(
				prefix="/recoveries",
				routes=[
					Route(
						Method.POST,
						Pattern("/"),
						recoveries.create,
						name="recoveries.create",
					),
					Route(
						Method.GET,
						Pattern("/{id:uuid}"),
						recoveries.show,
						name="recoveries.show",
					),
				],
			),
			Route(
				Method.PUT,
				Pattern("/orderings"),
				orderings.update,
				name="orderings.update",
			),
			Route(
				Method.DELETE,
				Pattern("/placements/{id:uuid}"),
				placements.delete,
				name="placements.delete",
			),
			Group(
				prefix="/boards",
				routes=[
					Route(Method.GET, Pattern("/"), boards.index, name="boards.index"),
					Route(
						Method.POST, Pattern("/"), boards.create, name="boards.create"
					),
					Route(Method.GET, Pattern("/new"), boards.new, name="boards.new"),
					Route(
						Method.GET,
						Pattern("/{id:uuid}"),
						boards.show,
						name="boards.show",
					),
					Route(
						Method.GET,
						Pattern("/{id:uuid}/edit"),
						boards.edit,
						name="boards.edit",
					),
					Route(
						Method.PUT,
						Pattern("/{id:uuid}"),
						boards.update,
						name="boards.update",
					),
					Route(
						Method.DELETE,
						Pattern("/{id:uuid}"),
						boards.delete,
						name="boards.delete",
					),
					Route(
						Method.PUT,
						Pattern("/{board_id:uuid}/placements"),
						placements.update_order,
						name="placements.update_order",
					),
					Route(
						Method.GET,
						Pattern("/{id:uuid}/pins/new"),
						pins.new,
						name="pins.new",
					),
				],
			),
			Group(
				prefix="/pins",
				routes=[
					Route(Method.GET, Pattern("/"), pins.index, name="pins.index"),
					Route(Method.POST, Pattern("/"), pins.create, name="pins.create"),
					Route(
						Method.GET,
						Pattern("/new"),
						pins.canonical_new,
						name="pins.canonical_new",
					),
					Route(
						Method.GET, Pattern("/{id:uuid}"), pins.show, name="pins.show"
					),
					Route(
						Method.GET,
						Pattern("/{id:uuid}/edit"),
						pins.edit,
						name="pins.edit",
					),
					Route(
						Method.PUT,
						Pattern("/{id:uuid}"),
						pins.update,
						name="pins.update",
					),
					Route(
						Method.DELETE,
						Pattern("/{id:uuid}"),
						pins.delete,
						name="pins.delete",
					),
				],
			),
		],
	),
]
