from uuid import UUID

from helios.app import Context
from helios.database import NotFoundError, Store
from helios.http import Request, Response
from helios.routing import URLs

from app import Board, Pin, Placement


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	urls = ctx.get(URLs)
	placement = store.find_one(Placement, id)
	pin = store.find_one(Pin, placement.pin_id)
	board = store.find_one(Board, placement.board_id)
	if not placement.can_remove(ctx, pin, board):
		raise NotFoundError(Placement, id)

	store.delete(placement)
	return Response.redirect(urls.route("boards.show", {"id": board.id}))
