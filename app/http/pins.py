from uuid import UUID

from lib.app import Context
from lib.forms import rules, Field, Form
from lib.http import Request, Response, Status, URL

from app.data import Board, Pin

def index(req: Request, ctx: Context) -> Response:
	pins = sorted(ctx.store.find_all(Pin), key = lambda pin: pin.created_at, reverse = True)
	inbox = [pin for pin in pins if not pin.hidden and pin.board_id is None]
	hidden = [pin for pin in pins if pin.hidden and pin.board_id is None]

	html = ctx.views.render("pins.index", {"inbox": inbox, "hidden": hidden})

	return Response.html(html)

def store(req: Request, ctx: Context) -> Response:
	form = Form([
		Field("url", [rules.required]),
		Field("title", [rules.required]),
		Field("board_id", []),
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)

	if input["board_id"]:
		board_id = UUID(input["board_id"])
	else:
		board_id = None

	ctx.store.create(
		Pin,
		title = input["title"],
		url = input["url"],
		board_id = board_id
	)

	return Response.redirect(URL("/"))

def new(req: Request, ctx: Context) -> Response:
	boards = ctx.store.find_all(Board)
	html = ctx.views.render("pins.new", {"boards": boards})
	return Response.html(html)

def edit(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	pin = ctx.store.find_one(Pin, id)
	if pin is None:
		return Response.text("404 Not Found", status = Status.NOT_FOUND)
	boards = ctx.store.find_all(Board)
	html = ctx.views.render("pins.edit", {"pin": pin, "boards": boards})
	return Response.html(html)

def update(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	pin = ctx.store.find_one(Pin, id)
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
		board_id = UUID(input["board_id"])
	else:
		board_id = None
	pin.url = input["url"]
	pin.title = input["title"]
	pin.board_id = board_id
	return Response.redirect(URL("/"))
