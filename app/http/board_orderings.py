from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.form import Form, Rules
from helios.form.rule import Distinct
from helios.http import Request, Response, Status

from app import Access, Ordering, User


class BoardOrderForm(Form):
	rules = Rules({"board_ids": [Distinct()]})

	board_ids: list[UUID] = []


def update(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	form, errors = BoardOrderForm.validate(req.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	access = Access(store, user)
	boards_by_id = {board.id: board for board in access.find_boards()}
	if set(form.board_ids) != set(boards_by_id):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	boards = [boards_by_id[board_id] for board_id in form.board_ids]
	Ordering.replace(store, access, boards)

	return Response.empty()
