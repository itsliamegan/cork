from helios.app import Context
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status

from app.data import Ordering, find_all_accessible_boards


def update(req: Request, ctx: Context) -> Response:
	form = Form([Field("board_id", parser.List(parser.UUID()))])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board_ids = input["board_id"]
	if len(board_ids) != len(set(board_ids)):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	accessible_board_ids = {board.id for board in find_all_accessible_boards(ctx)}
	if set(board_ids) != accessible_board_ids:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	for ordering in ctx.store.find_by(Ordering, user_id=ctx.auth.user.id):
		ctx.store.delete(Ordering, ordering.id)
	for position, board_id in enumerate(board_ids):
		ctx.store.create(
			Ordering,
			user_id=ctx.auth.user.id,
			board_id=board_id,
			position=position,
		)

	return Response.empty()
