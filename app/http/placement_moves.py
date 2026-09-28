from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.form import Form
from helios.http import Request, Response, Status

from app import Access, Move, Placement, User
from app.move import OutOfDate


class PlacementMoveForm(Form):
	above_id: UUID | None = None
	below_id: UUID | None = None


def create(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	access = Access(store, user)
	placement = access.find_placement(id)
	board = access.find_board(placement.board_id)

	form, errors = PlacementMoveForm.validate(req.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	is_own_neighbour = placement.id in (form.above_id, form.below_id)
	has_no_neighbours = form.above_id is None and form.below_id is None
	if is_own_neighbour or has_no_neighbours or form.above_id == form.below_id:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	try:
		Placement.move(
			store,
			board,
			user,
			Move(placement.id, form.above_id, form.below_id),
		)
	except OutOfDate:
		return Response.text("409 Conflict", status=Status.CONFLICT)

	return Response.empty()
