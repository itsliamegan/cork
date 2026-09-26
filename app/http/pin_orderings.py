from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.form import Form
from helios.http import Request, Response, Status

from app import Access, Ownership, Placement, User
from app.http.rules import Distinct


class PinOrderForm(Form):
	rules = {"placement_ids": [Distinct()]}

	placement_ids: list[UUID] = []


def update(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	access = Access(store, user, Ownership(store, user))
	board = access.find_board(id)

	form, errors = PinOrderForm.validate(req.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	placements = store.find_by(Placement, board_id=board.id)
	placements_by_id = {placement.id: placement for placement in placements}
	if set(form.placement_ids) != set(placements_by_id):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	for position, placement_id in enumerate(form.placement_ids):
		placement = placements_by_id[placement_id]
		placement.position = position
		store.save(placement)

	return Response.empty()
