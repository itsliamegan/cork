from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.http import Request, Response
from helios.routing import URLs

from app import Access, Archival, Pin, Placement, User


def create(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	flash = ctx.get(Flashes)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	placement = store.find_one(Placement, id)
	board = Access(store, user).find_board(placement.board_id)
	pin = store.find_one(Pin, placement.pin_id)

	Archival.create(store, placement, user)
	flash["archived"] = {"placement_id": str(placement.id), "title": pin.title}
	return Response.redirect(urls.route("boards.show", {"id": board.id}))


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	placement = store.find_one(Placement, id)
	board = Access(store, user).find_board(placement.board_id)

	for archival in store.find_by(
		Archival,
		placement_id=placement.id,
		user_id=user.id,
	):
		store.delete(archival)
	return Response.redirect(urls.route("boards.show", {"id": board.id}))
