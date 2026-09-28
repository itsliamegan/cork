from helios.auth import Authenticator
from helios.http import Method, Response
from helios.routing import Group, Pattern, Route, URLs

from app import User
from app.http import (
	archivals,
	board_ordering_moves,
	boards,
	home,
	invites,
	pins,
	placement_moves,
	placements,
	recoveries,
	redemptions,
	sessions,
	settings,
)


def ensure_signed_in(req, ctx, **params):
	auth = ctx.get(Authenticator[User])
	urls = ctx.get(URLs)

	if not auth.is_signed_in():
		return Response.redirect(urls.route("sessions.new"))


routes: list[Route | Group] = [
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
				Method.DELETE,
				Pattern("/placements/{id:uuid}"),
				placements.delete,
				name="placements.delete",
			),
			Route(
				Method.POST,
				Pattern("/placements/{id:uuid}/moves"),
				placement_moves.create,
				name="placement_moves.create",
			),
			Group(
				prefix="/archivals",
				routes=[
					Route(
						Method.POST,
						Pattern("/"),
						archivals.create,
						name="archivals.create",
					),
					Route(
						Method.DELETE,
						Pattern("/{id:uuid}"),
						archivals.delete,
						name="archivals.delete",
					),
				],
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
						Method.POST,
						Pattern("/{id:uuid}/ordering/moves"),
						board_ordering_moves.create,
						name="board_ordering_moves.create",
					),
				],
			),
			Group(
				prefix="/pins",
				routes=[
					Route(Method.GET, Pattern("/"), pins.index, name="pins.index"),
					Route(Method.POST, Pattern("/"), pins.create, name="pins.create"),
					Route(Method.GET, Pattern("/new"), pins.new, name="pins.new"),
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
