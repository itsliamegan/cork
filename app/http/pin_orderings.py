from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.form import Form, Rules
from helios.form.rule import Distinct
from helios.http import Request, Response, Status

from app import Access, Placement, User


class PinOrderForm(Form):
	rules = Rules({"placement_ids": [Distinct()]})

	placement_ids: list[UUID] = []


def update(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	access = Access(store, user)
	board = access.find_board(id)

	form, errors = PinOrderForm.validate(req.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	placements = store.find_by(Placement, board_id=board.id)
	placements_by_id = {placement.id: placement for placement in placements}
	if set(form.placement_ids) != set(placements_by_id):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	placements = [placements_by_id[placement_id] for placement_id in form.placement_ids]
	Placement.reorder(store, board, placements)

	return Response.empty()
