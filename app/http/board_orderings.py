from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.form import Form
from helios.http import Request, Response, Status

from app import Access, Ordering, Ownership, User
from app.http.rules import Distinct


class BoardOrderForm(Form):
	rules = {"board_ids": [Distinct()]}

	board_ids: list[UUID] = []


def update(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	form, errors = BoardOrderForm.validate(req.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	access = Access(store, user, Ownership(store, user))
	accessible_board_ids = {board.id for board in access.find_boards()}
	if set(form.board_ids) != accessible_board_ids:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	for ordering in store.find_by(Ordering, user_id=user.id):
		store.delete(ordering)
	for position, board_id in enumerate(form.board_ids):
		store.create(
			Ordering,
			user_id=user.id,
			board_id=board_id,
			position=position,
		)

	return Response.empty()
