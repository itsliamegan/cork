from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.form import Form
from helios.http import Request, Response, Status
from helios.routing import URLs

from app import Access, Archival, Pin, Placement, User


class ArchivalForm(Form):
	placement_id: UUID


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	flash = ctx.get(Flashes)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	form, errors = ArchivalForm.validate(req.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	access = Access(store, user)
	placement = access.find_placement(form.placement_id)
	board = access.find_board(placement.board_id)
	pin = store.find_one(Pin, placement.pin_id)

	archival = Archival.create(store, placement, user)
	flash["archived"] = {"archival_id": str(archival.id), "title": pin.title}
	return Response.redirect(urls.route("boards.show", {"id": board.id}))


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	access = Access(store, user)
	archival = access.find_archival(id)
	placement = store.find_one(Placement, archival.placement_id)
	board = access.find_board(placement.board_id)
	store.delete(archival)

	return Response.redirect(urls.route("boards.show", {"id": board.id}))
