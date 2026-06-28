from app.data import Board, Pin

from lux.app import Context
from lux.forms import rules, Field, Form
from lux.http import Request, Response, Status, URL

from uuid import UUID

def store(req: Request, ctx: Context) -> Response:
	form = Form([
		Field("title", [rules.required])
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)

	board = ctx.store.create(Board, title = input["title"])

	return Response.redirect(URL(f"/boards/{board.id}"))

def new(req: Request, ctx: Context) -> Response:
	html = ctx.views.render("boards.new")
	return Response.html(html)

def show(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	board = ctx.store.find_one(Board, id)
	if board is None:
		return Response.text("404 Not Found", status = Status.NOT_FOUND)
	pins = ctx.store.find_by(Pin, board_id = board.id)

	html = ctx.views.render("boards.show", {"board": board, "pins": pins})

	return Response.html(html)

def edit(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	board = ctx.store.find_one(Board, id)
	if board is None:
		return Response.text("404 Not Found", status = Status.NOT_FOUND)

	html = ctx.views.render("boards.edit", {"board": board})

	return Response.html(html)

def update(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	board = ctx.store.find_one(Board, id)
	if board is None:
		return Response.text("404 Not Found", status = Status.NOT_FOUND)
	form = Form([
		Field("title", [rules.required])
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)
	board.title = input["title"]
	return Response.redirect(URL(f"/boards/{board.id}"))
