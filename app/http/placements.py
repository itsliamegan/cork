from uuid import UUID

from helios.app import Context
from helios.database import NotFoundError, Store
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL

from app.data import (
	Board,
	Pin,
	Placement,
	can_remove_placement,
	find_accessible_board,
)


def update_order(req: Request, ctx: Context, board_id: UUID) -> Response:
	store = ctx.get(Store)
	find_accessible_board(ctx, board_id)

	form = Form([Field("placement_id", parser.List(parser.UUID()))])
	input, errors = form.validate(req.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	placement_ids = input["placement_id"]
	if len(placement_ids) != len(set(placement_ids)):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	placements = store.find_by(Placement, board_id=board_id)
	placements_by_id = {placement.id: placement for placement in placements}
	if set(placement_ids) != set(placements_by_id):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	for position, placement_id in enumerate(placement_ids):
		placement = placements_by_id[placement_id]
		placement.position = position
		store.save(placement)

	return Response.empty()


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	placement = store.find_one(Placement, id)
	pin = store.find_one(Pin, placement.pin_id)
	board = store.find_one(Board, placement.board_id)
	if not can_remove_placement(ctx, placement, pin, board):
		raise NotFoundError(Placement, id)

	store.delete(placement)
	return Response.redirect(URL(f"/boards/{board.id}"))
