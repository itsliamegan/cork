from uuid import UUID

from helios.app import Context
from helios.database import NotFoundError, Store
from helios.http import Request, Response, URL

from app.data import (
	Board,
	Pin,
	Placement,
	can_remove_placement,
)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	placement = store.find_one(Placement, id)
	pin = store.find_one(Pin, placement.pin_id)
	board = store.find_one(Board, placement.board_id)
	if not can_remove_placement(ctx, placement, pin, board):
		raise NotFoundError(Placement, id)

	store.delete(placement)
	return Response.redirect(URL(f"/boards/{board.id}"))
