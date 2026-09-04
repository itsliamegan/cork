from uuid import UUID

from helios.app import Context
from helios.forms import rules, Field, Form
from helios.http import Request, Response, Status, URL

from app.data import find_all_owned, find_owned, Board, Pin

def create(req: Request, ctx: Context) -> Response:
	form = Form([
		Field("url", [rules.required]),
		Field("title", [rules.required]),
		Field("board_id", []),
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)

	if input["board_id"]:
		board = find_owned(ctx, Board, UUID(input["board_id"]))
		if board is None:
			return Response.text("404 Not Found", status = Status.NOT_FOUND)
		board_id = board.id
	else:
		board_id = None

	ctx.store.create(
		Pin,
		title = input["title"],
		url = input["url"],
		board_id = board_id,
		user_id = ctx.auth.user.id
	)

	if board_id is None:
		board_url = URL("/")
	else:
		board_url = URL(f"/boards/{board_id}")

	return Response.redirect(board_url)

def new(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	board_id = UUID(params["id"])
	board = find_owned(ctx, Board, board_id)
	if board is None:
		return Response.text("404 Not Found", status = Status.NOT_FOUND)
	boards = find_all_owned(ctx, Board)
	html = ctx.views.render("pins.new", {"board": board, "board_id": board_id, "boards": boards})
	return Response.html(html)

def edit(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	pin = find_owned(ctx, Pin, id)
	if pin is None:
		return Response.text("404 Not Found", status = Status.NOT_FOUND)
	board = find_owned(ctx, Board, pin.board_id) if pin.board_id else None
	boards = find_all_owned(ctx, Board)
	html = ctx.views.render("pins.edit", {"pin": pin, "board": board, "boards": boards})
	return Response.html(html)

def update(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	pin = find_owned(ctx, Pin, id)
	if pin is None:
		return Response.text("404 Not Found", status = Status.NOT_FOUND)

	form = Form([
		Field("url", [rules.required]),
		Field("title", [rules.required]),
		Field("board_id", []),
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)

	if input["board_id"]:
		board = find_owned(ctx, Board, UUID(input["board_id"]))
		if board is None:
			return Response.text("404 Not Found", status = Status.NOT_FOUND)
		board_id = board.id
	else:
		board_id = None

	pin.url = input["url"]
	pin.title = input["title"]
	pin.board_id = board_id

	if board_id is None:
		board_url = URL("/")
	else:
		board_url = URL(f"/boards/{board_id}")

	return Response.redirect(board_url)

def delete(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	pin = find_owned(ctx, Pin, id)
	if pin is None:
		return Response.text("404 Not Found", status = Status.NOT_FOUND)

	if pin.board_id is None:
		board_url = URL("/")
	else:
		board_url = URL(f"/boards/{pin.board_id}")

	ctx.store.delete(Pin, pin.id)

	return Response.redirect(board_url)
