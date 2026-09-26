from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import NotFoundError, Store
from helios.http import Request, Response
from helios.routing import URLs

from app import Access, Board, Ownership, Pin, Placement, Removal, User


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	placement = store.find_one(Placement, id)
	pin = store.find_one(Pin, placement.pin_id)
	board = store.find_one(Board, placement.board_id)
	access = Access(Ownership(store, user))
	if not Removal(placement, pin, board).is_authorized(access):
		raise NotFoundError(Placement, id)

	store.delete(placement)
	return Response.redirect(urls.route("boards.show", {"id": board.id}))
