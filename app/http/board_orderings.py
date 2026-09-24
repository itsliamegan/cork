from typing import cast

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status

from app import Board, Ordering, User


def update(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	form = Form([Field("board_id", parser.List(parser.UUID()))])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board_ids = input["board_id"]
	if len(board_ids) != len(set(board_ids)):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	accessible_board_ids = {board.id for board in Board.find_all_accessible(ctx)}
	if set(board_ids) != accessible_board_ids:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	for ordering in store.find_by(Ordering, user_id=user.id):
		store.delete(ordering)
	for position, board_id in enumerate(board_ids):
		store.create(
			Ordering,
			user_id=user.id,
			board_id=board_id,
			position=position,
		)

	return Response.empty()
