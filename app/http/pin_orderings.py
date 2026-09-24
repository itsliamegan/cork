from uuid import UUID

from helios.app import Context
from helios.database import Store
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status

from app import Board, Placement


def update(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	Board.find_accessible(ctx, id)

	form = Form([Field("placement_id", parser.List(parser.UUID()))])
	input, errors = form.validate(req.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	placement_ids = input["placement_id"]
	if len(placement_ids) != len(set(placement_ids)):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	placements = store.find_by(Placement, board_id=id)
	placements_by_id = {placement.id: placement for placement in placements}
	if set(placement_ids) != set(placements_by_id):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	for position, placement_id in enumerate(placement_ids):
		placement = placements_by_id[placement_id]
		placement.position = position
		store.save(placement)

	return Response.empty()
