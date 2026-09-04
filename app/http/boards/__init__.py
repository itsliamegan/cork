from app.data import find_all_owned, find_owned, Board, Pin

from helios.app import Context
from helios.forms import rules, Field, Form
from helios.http import Request, Response, Status, URL

from uuid import UUID

def index(req: Request, ctx: Context) -> Response:
	boards = find_all_owned(ctx, Board)

	html = ctx.views.render("boards.index", {"boards": boards})

	return Response.html(html)

def create(req: Request, ctx: Context) -> Response:
	form = Form([
		Field("title", [rules.required])
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)

	board = ctx.store.create(Board, title = input["title"], user_id = ctx.auth.user.id)

	return Response.redirect(URL(f"/boards/{board.id}"))

def new(req: Request, ctx: Context) -> Response:
	html = ctx.views.render("boards.new")
	return Response.html(html)

def show(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	board = find_owned(ctx, Board, id)
	pins = find_all_owned(ctx, Pin, board_id = board.id)

	html = ctx.views.render("boards.show", {"board": board, "pins": pins})

	return Response.html(html)

def edit(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	board = find_owned(ctx, Board, id)

	html = ctx.views.render("boards.edit", {"board": board})

	return Response.html(html)

def update(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	board = find_owned(ctx, Board, id)
	form = Form([
		Field("title", [rules.required])
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)
	board.title = input["title"]
	return Response.redirect(URL("/boards/"))

def delete(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	board = find_owned(ctx, Board, id)
	pins = find_all_owned(ctx, Pin, board_id = board.id)
	for pin in pins:
		ctx.store.delete(Pin, pin.id)
	ctx.store.delete(Board, board.id)

	return Response.redirect(URL("/boards/"))
