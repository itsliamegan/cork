from helios.auth import Authenticator
from helios.http import Response
from helios.routing import Group, Route, URLs

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
			Route.post("/", sessions.create, name="sessions.create"),
			Route.get("/new", sessions.new, name="sessions.new"),
			Route.delete(
				"/",
				sessions.delete,
				name="sessions.delete",
				guards=[ensure_signed_in],
			),
		],
	),
	Group(
		prefix="/redemptions",
		routes=[
			Route.post("/", redemptions.create, name="redemptions.create"),
			Route.get("/new", redemptions.new, name="redemptions.new"),
		],
	),
	Group(
		guards=[ensure_signed_in],
		routes=[
			Route.get("/", home.show, name="home.show"),
			Route.get("/settings", settings.show, name="settings.show"),
			Route.put("/settings", settings.update, name="settings.update"),
			Group(
				prefix="/invites",
				routes=[
					Route.post("/", invites.create, name="invites.create"),
					Route.get("/{id:uuid}", invites.show, name="invites.show"),
				],
			),
			Group(
				prefix="/recoveries",
				routes=[
					Route.post("/", recoveries.create, name="recoveries.create"),
					Route.get("/{id:uuid}", recoveries.show, name="recoveries.show"),
				],
			),
			Route.delete(
				"/placements/{id:uuid}",
				placements.delete,
				name="placements.delete",
			),
			Route.post(
				"/placements/{id:uuid}/moves",
				placement_moves.create,
				name="placement_moves.create",
			),
			Group(
				prefix="/archivals",
				routes=[
					Route.post("/", archivals.create, name="archivals.create"),
					Route.delete(
						"/{id:uuid}",
						archivals.delete,
						name="archivals.delete",
					),
				],
			),
			Group(
				prefix="/boards",
				routes=[
					Route.get("/", boards.index, name="boards.index"),
					Route.post("/", boards.create, name="boards.create"),
					Route.get("/new", boards.new, name="boards.new"),
					Route.get("/{id:uuid}", boards.show, name="boards.show"),
					Route.get("/{id:uuid}/edit", boards.edit, name="boards.edit"),
					Route.put("/{id:uuid}", boards.update, name="boards.update"),
					Route.delete("/{id:uuid}", boards.delete, name="boards.delete"),
					Route.post(
						"/{id:uuid}/ordering/moves",
						board_ordering_moves.create,
						name="board_ordering_moves.create",
					),
				],
			),
			Group(
				prefix="/pins",
				routes=[
					Route.get("/", pins.index, name="pins.index"),
					Route.post("/", pins.create, name="pins.create"),
					Route.get("/new", pins.new, name="pins.new"),
					Route.get("/{id:uuid}", pins.show, name="pins.show"),
					Route.get("/{id:uuid}/edit", pins.edit, name="pins.edit"),
					Route.put("/{id:uuid}", pins.update, name="pins.update"),
					Route.delete("/{id:uuid}", pins.delete, name="pins.delete"),
				],
			),
		],
	),
]
